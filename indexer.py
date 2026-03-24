import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_openai import OpenAIEmbeddings
from database import supabase
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

def build_index(docs_path: str = "docs/"):
    loader = DirectoryLoader(docs_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    print(f"✅ Загружено документов: {len(documents)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " "]
    )
    chunks = splitter.split_documents(documents)
    print(f"✅ Чанков создано: {len(chunks)}")

    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

    for i, chunk in enumerate(chunks):
        embedding = embeddings_model.embed_query(chunk.page_content)
        supabase.table("documents").insert({
            "content": chunk.page_content,
            "metadata": chunk.metadata,
            "embedding": embedding
        }).execute()
        if (i + 1) % 50 == 0:
            print(f"  Загружено {i + 1}/{len(chunks)} чанков...")

    print(f"✅ База знаний обновлена в Supabase")

if __name__ == "__main__":
    build_index()
