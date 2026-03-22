import streamlit as st
from rag_chain import build_chain

st.set_page_config(page_title="ГПС Ассистент", page_icon="⚙️", layout="wide")
st.title("⚙️ Ассистент диспетчера ГПС")
st.caption("Задайте вопрос по нормативным документам и регламентам")

@st.cache_resource
def get_chain():
    try:
        return build_chain()
    except Exception as e:
        return None

chain = get_chain()

if chain is None:
    st.warning("⚠️ База знаний пуста. Добавьте PDF-документы в папку `docs/` и запустите `indexer.py`")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("Введите вопрос..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Ищу в документах..."):
            result = chain.invoke({"query": question})
            answer = result["result"]
            sources = result["source_documents"]

        st.markdown(answer)

        with st.expander("📄 Источники"):
            for i, doc in enumerate(sources):
                source = doc.metadata.get('source', 'документ')
                page = doc.metadata.get('page', '?')
                # Чистим текст от лишних переносов
                clean_text = ' '.join(doc.page_content.split())
                st.markdown(f"**{source}** (стр. {page})")
                st.caption(clean_text[:300] + "...")
                if i < len(sources) - 1:
                    st.divider()

    st.session_state.messages.append({"role": "assistant", "content": answer})