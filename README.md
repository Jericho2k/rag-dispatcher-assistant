# ГПС / Ассистент

RAG-ассистент для диспетчеров газоперерабатывающей станции. Отвечает на вопросы по нормативным документам и регламентам.

## Стек
- **Backend:** FastAPI + Python
- **AI:** OpenAI GPT-4o-mini + text-embedding-3-small
- **Database:** Supabase (PostgreSQL + pgvector)
- **Auth:** JWT + Supabase Auth
- **Frontend:** HTML/CSS/JS

## Архитектура
- RAG pipeline: документы → embeddings → векторный поиск → LLM
- Роли: admin (загружает документы, управляет пользователями) и user
- Личные документы каждого пользователя видны только ему

## Запуск локально
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Переменные окружения (.env)
```
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
DATABASE_URL=
SECRET_KEY=
```
