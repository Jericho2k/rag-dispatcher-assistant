from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import shutil
from rag_chain import build_chain
from chat_history import (load_all_chats, create_chat, get_chat_messages,
                           save_chat_messages, delete_chat)
from indexer import build_index

app = FastAPI()

# ─── RAG chain singleton ───────────────────────────────────────────────────────
_chain = None

def get_chain():
    global _chain
    if _chain is None:
        try:
            _chain = build_chain()
        except Exception as e:
            print(f"Chain error: {e}")
    return _chain

# ─── Models ────────────────────────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    chat_id: str
    question: str

class RenameRequest(BaseModel):
    title: str

# ─── Chat endpoints ────────────────────────────────────────────────────────────
@app.get("/api/chats")
def list_chats():
    return load_all_chats()

@app.post("/api/chats")
def new_chat():
    chat_id = create_chat()
    return {"chat_id": chat_id}

@app.delete("/api/chats/{chat_id}")
def remove_chat(chat_id: str):
    delete_chat(chat_id)
    return {"ok": True}

@app.get("/api/chats/{chat_id}/messages")
def chat_messages(chat_id: str):
    return get_chat_messages(chat_id)

# ─── Ask endpoint ──────────────────────────────────────────────────────────────
@app.post("/api/ask")
def ask(req: QuestionRequest):
    chain = get_chain()
    if chain is None:
        return {"error": "База знаний пуста. Загрузите документы в настройках."}

    result = chain.invoke({"query": req.question})
    answer = result["result"]
    sources = []
    for doc in result["source_documents"]:
        sources.append({
            "source": doc.metadata.get("source", "документ"),
            "page": doc.metadata.get("page", "?"),
            "text": " ".join(doc.page_content.split())[:300]
        })

    messages = get_chat_messages(req.chat_id)
    messages.append({"role": "user", "content": req.question})
    messages.append({"role": "assistant", "content": answer, "sources": sources})
    save_chat_messages(req.chat_id, messages)

    return {"answer": answer, "sources": sources}

# ─── Docs upload endpoint ──────────────────────────────────────────────────────
@app.post("/api/docs/upload")
async def upload_docs(files: list[UploadFile] = File(...)):
    os.makedirs("docs", exist_ok=True)
    saved = []
    for file in files:
        path = os.path.join("docs", file.filename)
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved.append(file.filename)

    global _chain
    _chain = None
    build_index()

    return {"uploaded": saved}

@app.get("/api/docs")
def list_docs():
    if not os.path.exists("docs"):
        return []
    return [f for f in os.listdir("docs") if f.endswith(".pdf")]

# ─── Static files ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")
