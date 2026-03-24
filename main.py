import hashlib
import json
import os
import tempfile

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests

from db.models import Platform, SessionLocal, User, init_db

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

load_dotenv()

app = FastAPI(title="Channel Agent API")
templates = Jinja2Templates(directory="web/templates")

# ===== Startup =====
@app.on_event("startup")
async def startup():
    init_db()

# ===== Models =====
class UserRegister(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class SummarizeRequest(BaseModel):
    transcript: str
    language: str = "auto"

class PlatformConnect(BaseModel):
    platform: str
    credentials: dict


SUPPORTED_PLATFORMS = {"discord", "gmail", "whatsapp"}


def _extract_discord_credentials(credentials: dict) -> tuple[str, str]:
    token = (
        (credentials or {}).get("discord-token")
        or (credentials or {}).get("token")
        or (credentials or {}).get("bot_token")
        or ""
    ).strip()
    guild_id = (
        (credentials or {}).get("discord-server")
        or (credentials or {}).get("server_id")
        or (credentials or {}).get("guild_id")
        or ""
    ).strip()
    return token, guild_id


def _validate_discord_credentials(token: str, guild_id: str) -> str | None:
    if not token:
        raise HTTPException(status_code=400, detail="Discord Bot Token is required.")
    if not guild_id:
        raise HTTPException(status_code=400, detail="Discord Server ID is required.")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Discord Server ID must be numeric.")

    auth_token = token[4:] if token.lower().startswith("bot ") else token
    headers = {"Authorization": f"Bot {auth_token}"}

    try:
        me_response = requests.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=12)
    except requests.RequestException:
        return "Discord API could not be reached right now. Saved as connected locally; retry later for full verification."

    if me_response.status_code == 401:
        raise HTTPException(status_code=400, detail="Invalid Discord Bot Token.")
    if me_response.status_code >= 400:
        raise HTTPException(status_code=400, detail="Discord bot validation failed.")

    try:
        guild_response = requests.get(
            f"https://discord.com/api/v10/guilds/{guild_id}",
            headers=headers,
            timeout=12,
        )
    except requests.RequestException:
        return "Discord server verification is temporarily unavailable. Saved as connected locally."

    if guild_response.status_code == 401:
        raise HTTPException(status_code=400, detail="Invalid Discord Bot Token.")
    if guild_response.status_code == 403:
        raise HTTPException(status_code=400, detail="Bot is not a member of this Discord server.")
    if guild_response.status_code == 404:
        raise HTTPException(status_code=400, detail="Discord server not found for this bot.")
    if guild_response.status_code >= 400:
        raise HTTPException(status_code=400, detail="Discord server validation failed.")
    return None

# ===== Routes =====
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/register")
async def register(user: UserRegister):
    db = SessionLocal()
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(user.password)
    new_user = User(name=user.name, email=user.email, password=hashed)
    db.add(new_user)
    db.commit()
    db.close()
    return {"success": True, "message": f"Welcome {user.name}!", "user": {"name": user.name, "email": user.email}}

@app.post("/api/login")
async def login(user: UserLogin):
    db = SessionLocal()
    existing = db.query(User).filter(User.email == user.email).first()
    db.close()
    if not existing or not verify_password(user.password, existing.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"success": True, "message": "Login successful", "user": {"name": existing.name, "email": existing.email}}

@app.post("/api/platform/connect")
async def connect_platform(data: PlatformConnect):
    platform_name = (data.platform or "").strip().lower()
    if platform_name not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail="Unsupported platform. Use discord, gmail, or whatsapp.")

    user_email = (data.credentials or {}).get("email", "").strip().lower()
    if not user_email:
        raise HTTPException(status_code=400, detail="Email is required in credentials.")

    db = SessionLocal()
    existing = db.query(Platform).filter(
        Platform.user_email == user_email,
        Platform.platform == platform_name
    ).first()

    safe_credentials = dict(data.credentials or {})
    safe_credentials["email"] = user_email

    warning_message = None
    if platform_name == "discord":
        token, guild_id = _extract_discord_credentials(safe_credentials)
        warning_message = _validate_discord_credentials(token, guild_id)
        if token:
            masked = (token[:6] + "..." + token[-4:]) if len(token) > 12 else "***"
            safe_credentials["discord-token"] = masked

    if existing:
        existing.connected = True
        existing.credentials = json.dumps(safe_credentials)
    else:
        new_platform = Platform(
            user_email=user_email,
            platform=platform_name,
            connected=True,
            credentials=json.dumps(safe_credentials)
        )
        db.add(new_platform)
    db.commit()
    db.close()
    response = {"success": True, "message": f"{platform_name} connected successfully!"}
    if warning_message:
        response["warning"] = warning_message
    return response

@app.get("/api/platform/status/{email}")
async def platform_status(email: str):
    db = SessionLocal()
    platforms = db.query(Platform).filter(Platform.user_email == email).all()
    db.close()
    result = {}
    for p in platforms:
        result[p.platform] = p.connected
    return result

@app.post("/api/platform/disconnect")
async def disconnect_platform(data: dict):
    platform_name = (data.get("platform") or "").strip().lower()
    if platform_name not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail="Unsupported platform. Use discord, gmail, or whatsapp.")

    db = SessionLocal()
    platform = db.query(Platform).filter(
        Platform.user_email == (data.get("email") or "").strip().lower(),
        Platform.platform == platform_name
    ).first()
    if platform:
        platform.connected = False
        db.commit()
    db.close()
    return {"success": True, "message": f"{platform_name} disconnected"}

@app.post("/api/transcribe")
async def transcribe_audio_api(audio: UploadFile = File(...)):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        from bot.transcriber import transcribe_audio
        transcript = transcribe_audio(tmp_path)

        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

        return {"transcript": transcript}
    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/api/summarize")
async def summarize_api(data: SummarizeRequest):
    try:
        from agent.summarizer import summarize_transcript
        if not (data.transcript or "").strip():
            raise HTTPException(status_code=400, detail="Transcript is required for summary")
        result = summarize_transcript(data.transcript, data.language)
        if not (result.get("summary") or "").strip():
            raise HTTPException(status_code=500, detail="Summary generation returned empty output")
        return {"summary": result['summary'], "language": result.get("language", data.language)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "message": "Channel Agent is running",
        "supported_platforms": sorted(SUPPORTED_PLATFORMS),
    }