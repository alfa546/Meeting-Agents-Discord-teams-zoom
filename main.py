from fastapi import FastAPI, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from dotenv import load_dotenv
from db.models import init_db, SessionLocal, User, Platform, Meeting
import hashlib
import json
import os

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

load_dotenv()

app = FastAPI(title="MeetingAgent API")
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

class MeetingJoin(BaseModel):
    link: str

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
    return {"success": True, "message": "Bot joining meeting...", "link": meeting.link}

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

@app.get("/api/health")
async def health():
    return {"status": "online", "message": "MeetingAgent is running!"}