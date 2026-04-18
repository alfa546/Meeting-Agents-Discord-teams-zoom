# LIMO Agent - AI Chatbot

LIMO Agent is a web-based AI chatbot similar to GPT.

This project is now focused only on chatbot functionality.


## What LIMO Agent Does

- Provides a clean web chat interface
- Supports multi-session chat by session ID
- Uses OpenRouter API when `OPENROUTER_API_KEY` is configured
- Automatically falls back to local replies if API key is missing
- Exposes simple API endpoints for chat, chat history, and clear history

## Tech Stack

- FastAPI
- Jinja2 templates (web UI)
- OpenRouter Python SDK (LLM provider)

## Project Structure

```text
.
├── main.py
├── requirements.txt
├── web/
│   └── templates/
│       └── index.html
└── README.md
```

## Setup

1. Create virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` file:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=openrouter/elephant-alpha
```

## Run

```bash
uvicorn main:app --reload --port 8000
```

Open: `http://localhost:8000`

## API Endpoints

- `GET /api/health`
- `POST /api/chat`
- `POST /api/session/history`
- `POST /api/session/clear`

## Example Request

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-user","message":"Hello LIMO","model":"openrouter/elephant-alpha"}'
```

## Notes

- Current session store is in-memory. Restarting server clears chat history.
- For production, replace in-memory storage with a database and add authentication.
