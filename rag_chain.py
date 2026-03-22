from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

load_dotenv()

PROMPT_TEMPLATE = """Ты — эксперт-ассистент для диспетчеров газоперерабатывающей станции (ГПС).
Отвечай ТОЛЬКО на основе предоставленного контекста из нормативных документов.
Если ответа нет в контексте — честно скажи об этом.
Всегда указывай из какого документа взята информация.

Контекст:
{context}

Вопрос: {question}

Ответ (со ссылкой на источник):"""

def build_chain(persist_dir: str = "chroma_db"):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings
    )
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )
    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"]
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )
    return chain