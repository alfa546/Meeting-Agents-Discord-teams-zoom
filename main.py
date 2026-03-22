import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from dotenv import load_dotenv
from db.models import init_db, SessionLocal, User, Platform, Meeting
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse
import httpx
import hashlib
import json
import os
import asyncio
import re
from datetime import datetime, timezone, timedelta
from bot.meeting_joiner import join_google_meet

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

load_dotenv()

app = FastAPI(title="MeetingAgent API")
templates = Jinja2Templates(directory="web/templates")

# Session middleware
app.add_middleware(SessionMiddleware, secret_key="meetingagent-secret-key-2024")

# Google OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/calendar.readonly'}
)

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

class MeetingJoin(BaseModel):
    link: str
    user_email: str = "guest@meetingagent.com"
    bot_name: str = "Meeting Bot"
    bot_email: str = ""
    bot_password: str = ""

class TranscribeRequest(BaseModel):
    audio: bytes = None

class SummarizeRequest(BaseModel):
    transcript: str
    language: str = "auto"

class PlatformConnect(BaseModel):
    platform: str
    credentials: dict

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

@app.post("/api/meeting/join")
async def join_meeting(meeting: MeetingJoin):
    if not meeting.link:
        raise HTTPException(status_code=400, detail="Meeting link required")
    
    db = SessionLocal()
    new_meeting = Meeting(
        user_email=meeting.user_email,
        platform="google_meet",
        link=meeting.link,
        summary="Processing...",
        transcript=""
    )
    db.add(new_meeting)
    db.commit()
    meeting_id = new_meeting.id
    db.close()
    
    asyncio.create_task(process_meeting(
        meeting.link, 
        meeting_id, 
        meeting.bot_name,
        meeting.bot_email,
        meeting.bot_password
    ))
    
    return {"success": True, "message": f"Bot joining as {meeting.bot_name}...", "meeting_id": meeting_id}


async def process_meeting(link: str, meeting_id: str, 
                          bot_name: str = "Meeting Bot",
                          bot_email: str = "",
                          bot_password: str = ""):
    try:
        await join_google_meet(link, bot_name, bot_email, bot_password)
        
        import os
        if not os.path.exists('recordings'):
            return
        recordings = sorted(os.listdir('recordings'))
        if not recordings:
            return
        
        latest = f"recordings/{recordings[-1]}"
        from bot.transcriber import transcribe_audio
        transcript = transcribe_audio(latest)
        
        if not transcript:
            return
        
        from agent.summarizer import summarize_transcript
        result = summarize_transcript(transcript)
        
        db = SessionLocal()
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting:
            meeting.summary = result['summary']
            meeting.transcript = transcript
            db.commit()
        db.close()
        print(f"Meeting {meeting_id} summary saved!")
        
    except Exception as e:
        print(f"Meeting processing error: {e}")

@app.post("/api/platform/connect")
async def connect_platform(data: PlatformConnect):
    db = SessionLocal()
    existing = db.query(Platform).filter(
        Platform.user_email == data.credentials.get("email", "test@test.com"),
        Platform.platform == data.platform
    ).first()
    if existing:
        existing.connected = True
        existing.credentials = json.dumps(data.credentials)
    else:
        new_platform = Platform(
            user_email=data.credentials.get("email", "test@test.com"),
            platform=data.platform,
            connected=True,
            credentials=json.dumps(data.credentials)
        )
        db.add(new_platform)
    db.commit()
    db.close()
    return {"success": True, "message": f"{data.platform} connected successfully!"}

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
    db = SessionLocal()
    platform = db.query(Platform).filter(
        Platform.user_email == data.get("email"),
        Platform.platform == data.get("platform")
    ).first()
    if platform:
        platform.connected = False
        db.commit()
    db.close()
    return {"success": True, "message": f"{data.get('platform')} disconnected"}

@app.get("/api/meetings/{email}")
async def get_meetings(email: str):
    db = SessionLocal()
    meetings = db.query(Meeting).filter(
        Meeting.user_email == email
    ).order_by(Meeting.created_at.desc()).all()
    db.close()
    
    return [{
        "id": m.id,
        "platform": m.platform,
        "link": m.link,
        "summary": m.summary,
        "transcript": m.transcript,
        "created_at": str(m.created_at)
    } for m in meetings]


@app.get("/api/meeting/analytics/{meeting_id}")
async def meeting_analytics(meeting_id: str):
    db = SessionLocal()
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    db.close()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript = (meeting.transcript or "").strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript not ready for analytics")

    try:
        from agent.summarizer import analyze_transcript
        analytics = analyze_transcript(transcript)
        return {
            "meeting_id": meeting_id,
            "platform": meeting.platform,
            "analytics": analytics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics generation failed: {str(e)}")


def _extract_meeting_link(event: dict) -> str:
    if event.get("hangoutLink"):
        return event.get("hangoutLink")

    conference = event.get("conferenceData", {})
    for entry in conference.get("entryPoints", []) or []:
        uri = entry.get("uri")
        if uri and uri.startswith("http"):
            return uri

    text_pool = " ".join([
        str(event.get("description") or ""),
        str(event.get("location") or "")
    ])
    pattern = r"https?://[^\s]+"
    urls = re.findall(pattern, text_pool)
    for url in urls:
        low = url.lower()
        if any(key in low for key in ["meet.google.com", "zoom.us", "teams.microsoft.com", "webex.com"]):
            return url
    return ""


@app.get("/api/calendar/meetings/{email}")
async def calendar_meetings(email: str):
    db = SessionLocal()
    platform = db.query(Platform).filter(
        Platform.user_email == email,
        Platform.platform == "google",
        Platform.connected == True
    ).first()
    db.close()

    if not platform:
        raise HTTPException(status_code=404, detail="Google Calendar is not connected")

    try:
        creds = json.loads(platform.credentials or "{}")
    except Exception:
        creds = {}

    access_token = creds.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Google access token missing. Reconnect Google account.")

    now = datetime.now(timezone.utc)
    time_min = now.isoformat().replace("+00:00", "Z")
    time_max = (now + timedelta(days=7)).isoformat().replace("+00:00", "Z")

    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    params = {
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 25
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, params=params, headers=headers)

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Google token expired. Please reconnect Google OAuth.")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch calendar meetings")

    payload = resp.json()
    items = payload.get("items", [])
    meetings = []
    for item in items:
        link = _extract_meeting_link(item)
        if not link:
            continue
        start = (item.get("start") or {}).get("dateTime") or (item.get("start") or {}).get("date")
        meetings.append({
            "id": item.get("id"),
            "title": item.get("summary") or "Untitled meeting",
            "start": start,
            "link": link
        })

    return {"meetings": meetings}

@app.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = str(request.base_url) + "auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        # Token save karo database mein
        db = SessionLocal()
        existing = db.query(Platform).filter(
            Platform.user_email == user_info['email'],
            Platform.platform == 'google'
        ).first()
        
        if existing:
            existing.connected = True
            existing.credentials = json.dumps({
                'access_token': token.get('access_token'),
                'email': user_info['email'],
                'name': user_info['name']
            })
        else:
            new_platform = Platform(
                user_email=user_info['email'],
                platform='google',
                connected=True,
                credentials=json.dumps({
                    'access_token': token.get('access_token'),
                    'email': user_info['email'],
                    'name': user_info['name']
                })
            )
            db.add(new_platform)
        db.commit()
        db.close()
        
        # Frontend pe redirect karo
        return RedirectResponse(url=f"/#google_connected=true&email={user_info['email']}&name={user_info['name']}")
        
    except Exception as e:
        print(f"OAuth error: {e}")
        return RedirectResponse(url="/#google_error=true")

# ===== TRANSCRIBE & SUMMARIZE ROUTES =====
from fastapi import UploadFile, File
import tempfile
import os

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
    return {"status": "online", "message": "MeetingAgent is running!"}