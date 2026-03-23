import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from database import supabase

load_dotenv()

PROMPT_TEMPLATE = """Ты — эксперт-ассистент для диспетчеров газоперерабатывающей станции (ГПС).
Отвечай на основе предоставленного контекста из нормативных документов.
Синтезируй информацию из контекста чтобы дать полезный ответ.
Если в контексте есть частичная информация — используй её.
Если информации совсем нет — скажи об этом честно.
Всегда указывай из какого документа взята информация.

Контекст:
{context}

Вопрос: {question}

Ответ (со ссылкой на источник):"""

embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def search_documents(query: str, threshold: float = 0.3, k: int = 6):
    query_embedding = embeddings_model.embed_query(query)
    result = supabase.rpc("match_documents", {
        "query_embedding": query_embedding,
        "match_threshold": threshold,
        "match_count": k
    }).execute()
    return result.data or []

def search_user_documents(query: str, user_id: str, threshold: float = 0.3, k: int = 4):
    query_embedding = embeddings_model.embed_query(query)
    result = supabase.rpc("match_user_documents", {
        "query_embedding": query_embedding,
        "match_threshold": threshold,
        "match_count": k,
        "p_user_id": user_id
    }).execute()
    return result.data or []

def ask(question: str, user_id: str = None):
    shared_docs = search_documents(question)
    personal_docs = search_user_documents(question, user_id) if user_id else []
    all_docs = shared_docs + personal_docs

    if not all_docs:
        return {
            "answer": "В базе знаний не найдено релевантной информации по вашему вопросу.",
            "sources": []
        }

    context = "\n\n".join([d["content"] for d in all_docs])
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)
    response = llm.invoke(prompt)

    sources = []
    for d in all_docs:
        meta = d.get("metadata", {})
        sources.append({
            "source": meta.get("source", "документ"),
            "page": meta.get("page", "?"),
            "text": " ".join(d["content"].split())[:300]
        })

    return {"answer": response.content, "sources": sources}