import json
import os
from datetime import datetime

HISTORY_FILE = "chat_history.json"

def load_all_chats():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_all_chats(chats):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=2)

def create_chat():
    chats = load_all_chats()
    chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = f"Чат {len(chats) + 1}"
    chats[chat_id] = {"title": title, "messages": []}
    save_all_chats(chats)
    return chat_id

def get_chat_messages(chat_id):
    chats = load_all_chats()
    return chats.get(chat_id, {}).get("messages", [])

def save_chat_messages(chat_id, messages):
    chats = load_all_chats()
    if chat_id in chats:
        # Обновляем заголовок по первому вопросу
        if messages and chats[chat_id]["title"].startswith("Чат "):
            first_msg = messages[0]["content"]
            chats[chat_id]["title"] = first_msg[:40] + ("..." if len(first_msg) > 40 else "")
        chats[chat_id]["messages"] = messages
        save_all_chats(chats)

def delete_chat(chat_id):
    chats = load_all_chats()
    if chat_id in chats:
        del chats[chat_id]
        save_all_chats(chats)

def rename_chat(chat_id, new_title):
    chats = load_all_chats()
    if chat_id in chats:
        chats[chat_id]["title"] = new_title
        save_all_chats(chats)