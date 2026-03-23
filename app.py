import streamlit as st
from rag_chain import build_chain
from chat_history import load_history, save_history, clear_history

st.set_page_config(page_title="ГПС Ассистент", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500&family=Syne:wght@400;600;700&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}

/* Hide Streamlit branding */
#MainMenu, footer, header {visibility: hidden;}
.stDeployButton {display: none;}

/* Main container */
.main .block-container {
    padding: 2rem 3rem;
    max-width: 900px;
}

/* Title */
h1 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.8rem !important;
    letter-spacing: -0.5px;
    color: #f0f0f0 !important;
    margin-bottom: 0 !important;
}

/* Caption */
.stCaption {
    color: #444 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.05em;
}

/* Metric */
[data-testid="stMetric"] {
    background: #111;
    border: 1px solid #1e1e1e;
    border-radius: 8px;
    padding: 0.75rem 1rem;
}
[data-testid="stMetricLabel"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem !important;
    color: #444 !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: #00ff88 !important;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: #0f0f0f !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 0.5rem !important;
}

/* User message accent */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    border-left: 2px solid #00ff88 !important;
}

/* Assistant message accent */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    border-left: 2px solid #333 !important;
}

/* Chat input */
[data-testid="stChatInput"] {
    background: #111 !important;
    border: 1px solid #222 !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #00ff88 !important;
    box-shadow: 0 0 0 1px #00ff8822 !important;
}

/* Expander (Источники) */
[data-testid="stExpander"] {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
    color: #444 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* Source cards */
.stCaption {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    color: #555 !important;
    line-height: 1.6 !important;
}

/* Bold in sources */
strong {
    color: #00ff88 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
}

/* Button */
.stButton button {
    background: transparent !important;
    border: 1px solid #222 !important;
    color: #444 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
.stButton button:hover {
    border-color: #ff4444 !important;
    color: #ff4444 !important;
}

/* Divider */
hr {
    border-color: #1a1a1a !important;
}

/* Spinner */
.stSpinner > div {
    border-color: #00ff88 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #222; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #333; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_chain():
    try:
        return build_chain()
    except Exception as e:
        return None

chain = get_chain()

if chain is None:
    st.warning("⚠️ База знаний пуста. Добавьте PDF в папку docs/ и запустите indexer.py")
    st.stop()

st.title("ГПС / Ассистент")
st.caption("RAG · ГОСТ · нормативные документы")

col1, col2, col3 = st.columns([3, 1, 1])
with col2:
    try:
        count = chain.retriever.vectorstore._collection.count()
        st.metric("Чанков в базе", count)
    except:
        pass
with col3:
    if st.button("очистить чат"):
        clear_history()
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = load_history()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("задать вопрос по документам..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner(""):
            result = chain.invoke({"query": question})
            answer = result["result"]
            sources = result["source_documents"]

        st.markdown(answer)

        with st.expander("источники"):
            for i, doc in enumerate(sources):
                source = doc.metadata.get('source', 'документ')
                page = doc.metadata.get('page', '?')
                clean_text = ' '.join(doc.page_content.split())
                st.markdown(f"**{source} · стр. {page}**")
                st.caption(clean_text[:300] + "...")
                if i < len(sources) - 1:
                    st.divider()

    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_history(st.session_state.messages)
