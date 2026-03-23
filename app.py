import streamlit as st
import os
from rag_chain import build_chain
from chat_history import (load_all_chats, create_chat, get_chat_messages,
                           save_chat_messages, delete_chat)
from indexer import build_index

st.set_page_config(page_title="ГПС Ассистент", page_icon="⚙️", layout="wide")

# ─── Theme ────────────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

is_dark = st.session_state.theme == "dark"
bg       = "#0a0a0a" if is_dark else "#fafafa"
bg2      = "#111111" if is_dark else "#f0f0f0"
bg3      = "#1a1a1a" if is_dark else "#e4e4e4"
text     = "#e8e8e8" if is_dark else "#111111"
text2    = "#555555" if is_dark else "#888888"
border   = "#1e1e1e" if is_dark else "#dddddd"
accent   = "#00ff88"
danger   = "#ff4444"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

* {{ box-sizing: border-box; }}
html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif !important;
    background-color: {bg} !important;
    color: {text} !important;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}
[data-testid="collapsedControl"] {{ display: none !important; }}

/* Sidebar — фиксированная ширина 260px */
section[data-testid="stSidebar"] {{
    background: {bg2} !important;
    border-right: 1px solid {border} !important;
    min-width: 260px !important;
    max-width: 260px !important;
    width: 260px !important;
    padding: 0 !important;
    transform: none !important;
    display: flex !important;
    visibility: visible !important;
}}
section[data-testid="stSidebar"] > div {{
    width: 260px !important;
    min-width: 260px !important;
    padding: 1.25rem 1rem !important;
}}
section[data-testid="stSidebar"] * {{
    color: {text} !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

/* Main content отступ от сайдбара */
.main .block-container {{
    padding: 2rem 2.5rem !important;
    max-width: 860px !important;
    margin: 0 auto !important;
}}

/* Кнопки в сайдбаре — как у Grok */
.stButton button {{
    background: transparent !important;
    border: 1px solid {border} !important;
    color: {text2} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 400 !important;
    border-radius: 8px !important;
    width: 100% !important;
    text-align: left !important;
    padding: 0.5rem 0.75rem !important;
    transition: all 0.15s ease !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}
.stButton button:hover {{
    background: {bg3} !important;
    border-color: {border} !important;
    color: {text} !important;
}}
.chat-active .stButton button {{
    background: {bg3} !important;
    color: {text} !important;
}}
.delete-btn .stButton button {{
    border-color: transparent !important;
    color: {text2} !important;
    padding: 0.5rem 0.5rem !important;
    font-size: 0.7rem !important;
}}
.delete-btn .stButton button:hover {{
    border-color: {danger} !important;
    color: {danger} !important;
    background: transparent !important;
}}

/* Заголовок h2 */
h2 {{
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1.3rem !important;
    color: {text} !important;
    margin-bottom: 1.5rem !important;
}}

/* Сообщения чата */
[data-testid="stChatMessage"] {{
    background: transparent !important;
    border: none !important;
    border-bottom: 1px solid {border} !important;
    border-radius: 0 !important;
    padding: 1.25rem 0 !important;
    margin-bottom: 0 !important;
}}
[data-testid="stChatMessage"] p {{
    font-size: 0.9rem !important;
    line-height: 1.7 !important;
    color: {text} !important;
}}

/* Chat input — как у Grok, внизу по центру */
[data-testid="stChatInput"] {{
    border-radius: 12px !important;
    border: 1px solid {border} !important;
    background: {bg2} !important;
}}
[data-testid="stChatInput"] textarea {{
    background: {bg2} !important;
    color: {text} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
}}
[data-testid="stChatInput"]:focus-within {{
    border-color: {accent} !important;
}}

/* Expander источники */
[data-testid="stExpander"] {{
    background: {bg2} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    margin-top: 0.5rem !important;
}}
[data-testid="stExpander"] summary {{
    font-size: 0.75rem !important;
    color: {text2} !important;
    font-weight: 500 !important;
}}
[data-testid="stExpander"] summary:hover {{
    color: {text} !important;
}}
.stCaption {{
    font-size: 0.75rem !important;
    color: {text2} !important;
    line-height: 1.6 !important;
}}
strong {{
    color: {text} !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
}}
hr {{ border-color: {border} !important; }}

/* File uploader */
[data-testid="stFileUploader"] {{
    background: {bg2} !important;
    border: 1px dashed {border} !important;
    border-radius: 10px !important;
    padding: 1rem !important;
}}
[data-testid="stFileUploader"] * {{ color: {text2} !important; }}

/* Метрики */
[data-testid="stMetric"] {{
    background: {bg2} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    padding: 0.75rem 1rem !important;
}}

/* Spinner */
.stSpinner > div {{ border-top-color: {accent} !important; }}

/* Warning */
[data-testid="stAlert"] {{
    background: {bg2} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    color: {text2} !important;
    font-size: 0.85rem !important;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {border}; border-radius: 2px; }}

/* Светлая тема — sidebar текст */
section[data-testid="stSidebar"] button {{
    color: {"#333" if not is_dark else text2} !important;
}}
</style>
""", unsafe_allow_html=True)

# ─── Session state ─────────────────────────────────────────────────────────────
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "page" not in st.session_state:
    st.session_state.page = "chat"

# ─── Chain ─────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_chain():
    try:
        return build_chain()
    except:
        return None

chain = get_chain()

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div style='padding: 1rem 0 0.5rem; font-family: Syne; font-weight: 700; font-size: 1.1rem; color: {text};'>ГПС / Ассистент</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 0.65rem; color: {text2}; margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.1em;'>RAG · ГОСТ · документы</div>", unsafe_allow_html=True)

    # Новый чат
    if st.button("＋  новый чат"):
        new_id = create_chat()
        st.session_state.current_chat_id = new_id
        st.session_state.messages = []
        st.session_state.page = "chat"
        st.rerun()

    st.markdown(f"<div style='height:1px; background:{border}; margin: 0.75rem 0;'></div>", unsafe_allow_html=True)

    # Список чатов
    chats = load_all_chats()
    for chat_id, chat_data in reversed(list(chats.items())):
        is_active = chat_id == st.session_state.current_chat_id
        cols = st.columns([5, 1])
        with cols[0]:
            div_class = "chat-active" if is_active else ""
            st.markdown(f"<div class='{div_class}'>", unsafe_allow_html=True)
            if st.button(chat_data["title"][:28], key=f"chat_{chat_id}"):
                st.session_state.current_chat_id = chat_id
                st.session_state.messages = get_chat_messages(chat_id)
                st.session_state.page = "chat"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with cols[1]:
            st.markdown("<div class='delete-btn'>", unsafe_allow_html=True)
            if st.button("✕", key=f"del_{chat_id}"):
                delete_chat(chat_id)
                if chat_id == st.session_state.current_chat_id:
                    st.session_state.current_chat_id = None
                    st.session_state.messages = []
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"<div style='height:1px; background:{border}; margin: 0.75rem 0;'></div>", unsafe_allow_html=True)

    # Настройки
    if st.button("⚙  настройки"):
        st.session_state.page = "settings"
        st.rerun()

# ─── Main area ─────────────────────────────────────────────────────────────────
st.markdown("<div class='chat-area'>", unsafe_allow_html=True)

# ── Страница настроек ──────────────────────────────────────────────────────────
if st.session_state.page == "settings":
    st.markdown(f"<h2 style='font-family: Syne; font-weight: 700; color: {text};'>Настройки</h2>", unsafe_allow_html=True)

    # Тема
    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 0.72rem; color: {text2}; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;'>Тема интерфейса</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("☀  светлая" if is_dark else "☀  светлая (активна)"):
            st.session_state.theme = "light"
            st.rerun()
    with col2:
        if st.button("◑  тёмная (активна)" if is_dark else "◑  тёмная"):
            st.session_state.theme = "dark"
            st.rerun()

    st.markdown(f"<div style='height:1px; background:{border}; margin: 1.5rem 0;'></div>", unsafe_allow_html=True)

    # Загрузка документов
    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 0.72rem; color: {text2}; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;'>База знаний</div>", unsafe_allow_html=True)

    uploaded = st.file_uploader("Загрузить PDF документы", type="pdf", accept_multiple_files=True)
    if uploaded:
        if st.button("Добавить в базу знаний"):
            os.makedirs("docs", exist_ok=True)
            for f in uploaded:
                path = os.path.join("docs", f.name)
                with open(path, "wb") as out:
                    out.write(f.getbuffer())
            with st.spinner("Индексирую документы..."):
                get_chain.clear()
                build_index()
            st.success(f"✓ Добавлено документов: {len(uploaded)}")
            st.rerun()

    # Список документов в базе
    docs_list = [f for f in os.listdir("docs") if f.endswith(".pdf")] if os.path.exists("docs") else []
    if docs_list:
        st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 0.7rem; color: {text2}; margin-top: 1rem;'>Документов в базе: {len(docs_list)}</div>", unsafe_allow_html=True)
        for doc in docs_list:
            st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 0.68rem; color: {text2}; padding: 0.2rem 0;'>· {doc}</div>", unsafe_allow_html=True)

# ── Страница чата ──────────────────────────────────────────────────────────────
else:
    if st.session_state.current_chat_id is None:
        # Пустой экран — нет активного чата
        st.markdown(f"""
        <div style='text-align: center; padding: 5rem 0;'>
            <div style='font-family: Syne; font-size: 2rem; font-weight: 700; color: {text}; margin-bottom: 0.5rem;'>ГПС / Ассистент</div>
            <div style='font-family: JetBrains Mono; font-size: 0.75rem; color: {text2}; text-transform: uppercase; letter-spacing: 0.1em;'>Создайте новый чат чтобы начать</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        if chain is None:
            st.warning("⚠️ База знаний пуста. Перейдите в Настройки и загрузите документы.")
        else:
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
                save_chat_messages(st.session_state.current_chat_id, st.session_state.messages)

st.markdown("</div>", unsafe_allow_html=True)