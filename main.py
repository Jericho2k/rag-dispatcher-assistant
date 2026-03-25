import os
import shutil
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
import asyncio
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from dotenv import load_dotenv
from database import supabase
from auth import create_access_token, get_current_user, require_admin, get_current_user_query
from rag_chain import ask
from indexer import build_index

load_dotenv()

app = FastAPI()

# ── Models ─────────────────────────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    chat_id: str
    question: str

class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: str

# ── Auth endpoints ─────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    try:
        res = supabase.auth.sign_in_with_password({
            "email": form.username,
            "password": form.password
        })
        user_id = res.user.id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    role_res = supabase.table("user_roles")\
        .select("role, name, email")\
        .eq("user_id", user_id).execute()
    
    role_data = role_res.data[0] if role_res.data else {}
    role = role_data.get("role", "user")
    name = role_data.get("name", "")

    token = create_access_token({
        "sub": user_id,
        "role": role,
        "name": name,
        "email": form.username
    })
    return {"access_token": token, "token_type": "bearer", "role": role, "name": name}

@app.get("/api/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user

# ── User management (admin only) ───────────────────────────────────────────────
@app.post("/api/users")
async def create_user(
    req: CreateUserRequest,
    current_user: dict = Depends(require_admin)
):
    try:
        res = supabase.auth.admin.create_user({
            "email": req.email,
            "password": req.password,
            "email_confirm": True
        })
        user_id = res.user.id
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: {str(e)}")

    supabase.table("user_roles").insert({
        "user_id": user_id,
        "role": "user",
        "name": req.name,
        "email": req.email
    }).execute()

    return {"ok": True, "email": req.email}

@app.get("/api/users")
async def list_users(current_user: dict = Depends(require_admin)):
    res = supabase.table("user_roles")\
        .select("user_id, role, name, email")\
        .execute()
    return res.data

@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    supabase.table("user_roles").delete().eq("user_id", user_id).execute()
    return {"ok": True}

# ── Chat endpoints ─────────────────────────────────────────────────────────────
@app.get("/api/chats")
async def list_chats(current_user: dict = Depends(get_current_user)):
    res = supabase.table("chats")\
        .select("*")\
        .eq("user_id", current_user["user_id"])\
        .order("created_at", desc=True)\
        .execute()
    return res.data

@app.post("/api/chats")
async def new_chat(current_user: dict = Depends(get_current_user)):
    res = supabase.table("chats").insert({
        "user_id": current_user["user_id"],
        "title": "Новый чат"
    }).execute()
    return res.data[0]

@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str, current_user: dict = Depends(get_current_user)):
    supabase.table("chats")\
        .delete()\
        .eq("id", chat_id)\
        .eq("user_id", current_user["user_id"])\
        .execute()
    return {"ok": True}

@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str, current_user: dict = Depends(get_current_user)):
    chat = supabase.table("chats")\
        .select("id")\
        .eq("id", chat_id)\
        .eq("user_id", current_user["user_id"])\
        .execute()
    if not chat.data:
        raise HTTPException(status_code=404, detail="Чат не найден")

    res = supabase.table("messages")\
        .select("*")\
        .eq("chat_id", chat_id)\
        .order("created_at")\
        .execute()
    return res.data

# ── Ask endpoint ───────────────────────────────────────────────────────────────
@app.post("/api/ask")
async def ask_question(
    req: QuestionRequest,
    current_user: dict = Depends(get_current_user)
):
    chat = supabase.table("chats")\
        .select("id")\
        .eq("id", req.chat_id)\
        .eq("user_id", current_user["user_id"])\
        .execute()
    if not chat.data:
        raise HTTPException(status_code=404, detail="Чат не найден")

    result = ask(req.question, user_id=current_user["user_id"])

    supabase.table("messages").insert([
        {"chat_id": req.chat_id, "role": "user", "content": req.question, "sources": []},
        {"chat_id": req.chat_id, "role": "assistant", "content": result["answer"], "sources": result["sources"]}
    ]).execute()

    messages_count = supabase.table("messages")\
        .select("id", count="exact")\
        .eq("chat_id", req.chat_id)\
        .execute()
    if messages_count.count <= 2:
        title = req.question[:40] + ("..." if len(req.question) > 40 else "")
        supabase.table("chats").update({"title": title}).eq("id", req.chat_id).execute()

    return result

# ── Docs endpoints ─────────────────────────────────────────────────────────────
@app.get("/api/docs")
async def list_docs(current_user: dict = Depends(get_current_user)):
    res = supabase.table("documents")\
        .select("metadata")\
        .execute()
    names = list({
        d["metadata"].get("source", "").replace("docs/", "") 
        for d in res.data 
        if d.get("metadata")
    })
    return sorted(names)

@app.post("/api/docs/upload/shared")
async def upload_shared_docs(
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(require_admin)
):
    os.makedirs("docs", exist_ok=True)
    saved = []
    for file in files:
        path = os.path.join("docs", file.filename)
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved.append(file.filename)
    return {"uploaded": saved, "status": "saved"}

@app.get("/api/docs/index/stream")
async def index_stream(current_user: dict = Depends(get_current_user_query)):
    async def generate():
        from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, Docx2txtLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_openai import OpenAIEmbeddings

        yield "data: {\"status\": \"loading\", \"message\": \"Загружаю документы...\"}\n\n"
        await asyncio.sleep(0.1)

        documents = []
        docs_path = "docs/"

        if os.path.exists(docs_path):
            pdf_loader = DirectoryLoader(docs_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
            documents += pdf_loader.load()
            docx_loader = DirectoryLoader(docs_path, glob="**/*.docx", loader_cls=Docx2txtLoader)
            documents += docx_loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200,
            separators=["\n\n", "\n", ".", " "]
        )
        chunks = splitter.split_documents(documents)
        total = len(chunks)

        yield f"data: {{\"status\": \"indexing\", \"total\": {total}, \"current\": 0, \"pct\": 0}}\n\n"
        await asyncio.sleep(0.1)

        embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

        for i, chunk in enumerate(chunks):
            embedding = embeddings_model.embed_query(chunk.page_content)
            supabase.table("documents").insert({
                "content": chunk.page_content,
                "metadata": chunk.metadata,
                "embedding": embedding
            }).execute()

            pct = round((i + 1) / total * 100)
            yield f"data: {{\"status\": \"indexing\", \"total\": {total}, \"current\": {i+1}, \"pct\": {pct}}}\n\n"
            await asyncio.sleep(0)

        yield f"data: {{\"status\": \"done\", \"total\": {total}}}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/docs/upload/personal")
async def upload_personal_docs(
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    from langchain_community.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    import tempfile

    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    saved = []

    for file in files:
        suffix = ".pdf" if file.filename.endswith(".pdf") else ".docx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            if file.filename.endswith('.pdf'):
                loader = PyPDFLoader(tmp_path)
                docs = loader.load()
            elif file.filename.endswith('.docx'):
                from langchain_community.document_loaders import Docx2txtLoader
                loader = Docx2txtLoader(tmp_path)
                docs = loader.load()
            else:
                saved.append(f"{file.filename} (неподдерживаемый формат)")
                continue

            chunks = splitter.split_documents(docs)
            for chunk in chunks:
                embedding = embeddings_model.embed_query(chunk.page_content)
                supabase.table("user_documents").insert({
                    "user_id": current_user["user_id"],
                    "content": chunk.page_content,
                    "metadata": {**chunk.metadata, "source": file.filename},
                    "embedding": embedding
                }).execute()
            saved.append(file.filename)
        finally:
            os.unlink(tmp_path)

    return {"uploaded": saved}

@app.delete("/api/docs/shared/{filename}")
async def delete_shared_doc(
    filename: str,
    current_user: dict = Depends(require_admin)
):
    # Удаляем из файловой системы
    path = os.path.join("docs", filename)
    if os.path.exists(path):
        os.remove(path)

    # Удаляем чанки из Supabase
    supabase.table("documents")\
        .delete()\
        .like("metadata->>source", f"%{filename}%")\
        .execute()

    return {"ok": True}

@app.delete("/api/docs/personal/{filename}")
async def delete_personal_doc(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    supabase.table("user_documents")\
        .delete()\
        .eq("user_id", current_user["user_id"])\
        .like("metadata->>source", f"%{filename}%")\
        .execute()

    return {"ok": True}

@app.get("/api/docs/personal")
async def list_personal_docs(current_user: dict = Depends(get_current_user)):
    res = supabase.table("user_documents")\
        .select("metadata")\
        .eq("user_id", current_user["user_id"])\
        .execute()
    names = list({d["metadata"].get("source", "") for d in res.data if d.get("metadata")})
    return names

# ── Static ─────────────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")