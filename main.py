import os
import json
from datetime import datetime
from typing import Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

try:
    from openrouter import OpenRouter
except Exception:  # pragma: no cover
    OpenRouter = None

load_dotenv()

app = FastAPI(title="LIMO Agent")
templates = Jinja2Templates(directory="web/templates")

SYSTEM_PROMPT = (
    "You are LIMO Agent, a helpful AI chatbot like GPT. "
    "Answer clearly, accurately, and with practical steps when useful."
)
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/elephant-alpha")

# Data directory for persistent storage
DATA_DIR = "data"
CHATS_FILE = os.path.join(DATA_DIR, "chats.json")
RECENT_FILE = os.path.join(DATA_DIR, "recent.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# In-memory chat store: {session_id: [{role, content, at}]}
CHAT_SESSIONS: Dict[str, List[dict]] = {}


def _load_chat_data():
    """Load all chat data from disk into memory"""
    global CHAT_SESSIONS
    if os.path.exists(CHATS_FILE):
        try:
            with open(CHATS_FILE, 'r') as f:
                CHAT_SESSIONS = json.load(f)
        except Exception:
            CHAT_SESSIONS = {}


def _save_chat_data():
    """Save current chat sessions to disk"""
    try:
        with open(CHATS_FILE, 'w') as f:
            json.dump(CHAT_SESSIONS, f, indent=2)
    except Exception:
        pass


def _load_recent_chats():
    """Load recent chats metadata from disk"""
    if os.path.exists(RECENT_FILE):
        try:
            with open(RECENT_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_recent_chats(recent: dict):
    """Save recent chats metadata to disk"""
    try:
        with open(RECENT_FILE, 'w') as f:
            json.dump(recent, f, indent=2)
    except Exception:
        pass


def _get_chat_title(session_id: str) -> str:
    """Get or generate title for a chat session"""
    recent = _load_recent_chats()
    if session_id in recent and 'title' in recent[session_id]:
        return recent[session_id]['title']
    
    # Generate title from first user message
    history = CHAT_SESSIONS.get(session_id, [])
    for msg in history:
        if msg.get('role') == 'user':
            title = msg.get('content', 'Chat')[:50]
            recent[session_id] = {
                'title': title,
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }
            _save_recent_chats(recent)
            return title
    return 'New Chat'


def _update_chat_activity(session_id: str):
    """Update the last activity timestamp for a chat"""
    recent = _load_recent_chats()
    if session_id not in recent:
        recent[session_id] = {
            'title': _get_chat_title(session_id),
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }
    recent[session_id]['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    _save_recent_chats(recent)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=8000)
    model: str = Field(default=DEFAULT_MODEL, min_length=3, max_length=200)


class SessionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)


def _get_client():
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key or OpenRouter is None:
        return None
    return OpenRouter(api_key=api_key)


def _local_fallback(user_message: str) -> str:
    msg = user_message.lower()
    if "resume" in msg or "cv" in msg:
        return "Share your background, skills, and target role. I can draft a strong one-page resume for you."
    if "email" in msg or "reply" in msg:
        return "Send the original message and I will draft a concise professional reply."
    if "code" in msg or "python" in msg or "javascript" in msg:
        return "Share your code snippet and goal. I will help debug or improve it step by step."
    return "LIMO Agent is ready. Ask anything and I will help with clear, practical answers."


def _chat_completion(session_id: str, user_message: str, model: str) -> str:
    history = CHAT_SESSIONS.setdefault(session_id, [])
    history.append({"role": "user", "content": user_message, "at": datetime.utcnow().isoformat() + "Z"})
    _save_chat_data()

    client = _get_client()
    if client is None:
        answer = _local_fallback(user_message)
        history.append({"role": "assistant", "content": answer, "at": datetime.utcnow().isoformat() + "Z"})
        _save_chat_data()
        _update_chat_activity(session_id)
        return answer

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history[-16:]:
        messages.append({"role": item["role"], "content": item["content"]})

    try:
        completion = client.chat.send(
            model=model,
            messages=messages,
            temperature=0.4,
            max_tokens=1000,
        )
        answer = (completion.choices[0].message.content or "").strip() or _local_fallback(user_message)
    except Exception:
        answer = _local_fallback(user_message)

    history.append({"role": "assistant", "content": answer, "at": datetime.utcnow().isoformat() + "Z"})
    _save_chat_data()
    _update_chat_activity(session_id)
    return answer


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.on_event("startup")
async def startup_event():
    """Load chat data from disk when app starts"""
    _load_chat_data()


@app.get("/api/health")
async def health():
    provider = "openrouter" if _get_client() else "local-fallback"
    return {
        "status": "online",
        "app": "LIMO Agent",
        "provider": provider,
        "model": DEFAULT_MODEL,
        "active_sessions": len(CHAT_SESSIONS),
    }


@app.post("/api/chat")
async def chat(payload: ChatRequest):
    requested_model = payload.model.strip() or DEFAULT_MODEL
    answer = _chat_completion(payload.session_id.strip(), payload.message.strip(), requested_model)
    return {"answer": answer, "session_id": payload.session_id, "model": requested_model}


@app.post("/api/session/history")
async def session_history(payload: SessionRequest):
    history = CHAT_SESSIONS.get(payload.session_id.strip(), [])
    return {"session_id": payload.session_id, "history": history}


@app.post("/api/session/clear")
async def session_clear(payload: SessionRequest):
    session_id = payload.session_id.strip()
    CHAT_SESSIONS.pop(session_id, None)
    _save_chat_data()
    
    # Also remove from recent chats
    recent = _load_recent_chats()
    recent.pop(session_id, None)
    _save_recent_chats(recent)
    
    return {"success": True, "session_id": session_id}


@app.post("/api/recent-chats")
async def get_recent_chats():
    """Get list of recent chats sorted by most recent first"""
    recent = _load_recent_chats()
    
    # Sort by updated_at descending
    sorted_chats = sorted(
        recent.items(),
        key=lambda x: x[1].get('updated_at', ''),
        reverse=True
    )
    
    # Return as list of dicts with session_id included
    result = [
        {
            'session_id': session_id,
            'title': data.get('title', 'Chat'),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at')
        }
        for session_id, data in sorted_chats
    ]
    
    return {"chats": result}
