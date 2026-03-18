from fastapi import FastAPI, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.requests import Request
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="MeetingAgent API")
templates = Jinja2Templates(directory="web/templates")

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
    if not user.name or not user.email or not user.password:
        raise HTTPException(status_code=400, detail="All fields required")
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")
    # Database mein save hoga baad mein
    return {"success": True, "message": f"Welcome {user.name}!", "user": {"name": user.name, "email": user.email}}

@app.post("/api/login")
async def login(user: UserLogin):
    if not user.email or not user.password:
        raise HTTPException(status_code=400, detail="All fields required")
    return {"success": True, "message": "Login successful", "user": {"name": user.email.split("@")[0], "email": user.email}}

@app.post("/api/meeting/join")
async def join_meeting(meeting: MeetingJoin):
    if not meeting.link:
        raise HTTPException(status_code=400, detail="Meeting link required")
    return {"success": True, "message": "Bot joining meeting...", "link": meeting.link}

@app.post("/api/platform/connect")
async def connect_platform(data: PlatformConnect):
    return {"success": True, "message": f"{data.platform} connected successfully!"}

@app.get("/api/health")
async def health():
    return {"status": "online", "message": "MeetingAgent is running!"}