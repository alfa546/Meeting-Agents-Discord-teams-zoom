import os
from datetime import datetime
from typing import Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None

load_dotenv()

app = FastAPI(title="LIMO Agent")
templates = Jinja2Templates(directory="web/templates")

SYSTEM_PROMPT = (
    "You are LIMO Agent, a helpful AI chatbot like GPT. "
    "Answer clearly, accurately, and with practical steps when useful."
)

# Simple in-memory chat store: {session_id: [{role, content, at}]}
CHAT_SESSIONS: Dict[str, List[dict]] = {}


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=8000)


class SessionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)


def _get_client():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return None
    return Groq(api_key=api_key)


def _local_fallback(user_message: str) -> str:
    msg = user_message.lower()
    if "resume" in msg or "cv" in msg:
        return "Share your background, skills, and target role. I can draft a strong one-page resume for you."
    if "email" in msg or "reply" in msg:
        return "Send the original message and I will draft a concise professional reply."
    if "code" in msg or "python" in msg or "javascript" in msg:
        return "Share your code snippet and goal. I will help debug or improve it step by step."
    return "LIMO Agent is ready. Ask anything and I will help with clear, practical answers."


def _chat_completion(session_id: str, user_message: str) -> str:
    history = CHAT_SESSIONS.setdefault(session_id, [])
    history.append({"role": "user", "content": user_message, "at": datetime.utcnow().isoformat() + "Z"})

    client = _get_client()
    if client is None:
        answer = _local_fallback(user_message)
        history.append({"role": "assistant", "content": answer, "at": datetime.utcnow().isoformat() + "Z"})
        return answer

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history[-16:]:
        messages.append({"role": item["role"], "content": item["content"]})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4,
            max_tokens=1000,
        )
        answer = (completion.choices[0].message.content or "").strip() or _local_fallback(user_message)
    except Exception:
        answer = _local_fallback(user_message)

    history.append({"role": "assistant", "content": answer, "at": datetime.utcnow().isoformat() + "Z"})
    return answer


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    provider = "groq" if _get_client() else "local-fallback"
    return {
        "status": "online",
        "app": "LIMO Agent",
        "provider": provider,
        "active_sessions": len(CHAT_SESSIONS),
    }


@app.post("/api/chat")
async def chat(payload: ChatRequest):
    answer = _chat_completion(payload.session_id.strip(), payload.message.strip())
    return {"answer": answer, "session_id": payload.session_id}


@app.post("/api/session/history")
async def session_history(payload: SessionRequest):
    history = CHAT_SESSIONS.get(payload.session_id.strip(), [])
    return {"session_id": payload.session_id, "history": history}


@app.post("/api/session/clear")
async def session_clear(payload: SessionRequest):
    CHAT_SESSIONS.pop(payload.session_id.strip(), None)
    return {"success": True, "session_id": payload.session_id}
