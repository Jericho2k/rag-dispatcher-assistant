# RAG Dispatcher Assistant

AI-ассистент для диспетчеров ГПС на основе RAG (Retrieval-Augmented Generation).

## Стек
- LangChain + ChromaDB
- OpenAI GPT-4o-mini + text-embedding-3-small
- Streamlit

## Запуск
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python indexer.py   # один раз, после добавления PDF в docs/
streamlit run app.py
```
