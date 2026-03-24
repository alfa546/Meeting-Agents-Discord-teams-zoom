# 🤖 MeetingAgent — AI Meeting Intelligence Platform

An open-source AI-powered meeting agent that automatically joins meetings, transcribes audio, and delivers intelligent summaries across multiple platforms.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Discord](https://img.shields.io/badge/Discord-Bot-7289DA)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

- 🎯 **Auto Join** — Paste a meeting link, bot joins automatically
- 🎙️ **Live Transcription** — Powered by Groq Whisper (free)
- 🧠 **AI Summary** — Key points, action items, decisions via LLaMA 3.3
- 💬 **Discord Bot** — Always online, sends summaries via DM
- 👋 **Auto Welcome DM** — New Discord members get automatic DM on join
- 📧 **Gmail Integration** — Auto-detects meeting links from emails
- 🌐 **Web Dashboard** — Beautiful dark-theme interface
- 📊 **Meeting History** — All past meetings and summaries saved

---

## 🏗️ Project Structure

```
Meeting-Agents-Discord-teams-zoom/
├── main.py                  # FastAPI backend — all API routes
├── scheduler.py             # Background task scheduler
├── requirements.txt         # All Python dependencies
├── .env                     # API keys (never commit this!)
├── .env.example             # Template for environment variables
│
├── bot/
│   ├── meeting_joiner.py    # Playwright — auto join Google Meet/Zoom
│   ├── audio_capture.py     # FFmpeg — record meeting audio
│   └── transcriber.py       # Groq Whisper — audio to text
│
├── agent/
│   ├── discord_bot.py       # Discord bot — commands and responses
│   ├── summarizer.py        # Groq LLaMA — AI meeting summary
│   └── email_handler.py     # Gmail API — detect meeting links
│
├── web/
│   └── templates/
│       └── index.html       # Full web interface (single file)
│
└── db/
    └── models.py            # SQLAlchemy — database models
```

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/alfa546/Meeting-Agents-Discord-teams-zoom.git
cd Meeting-Agents-Discord-teams-zoom
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browser

```bash
playwright install chromium
playwright install-deps chromium  # Linux only
```

### 5. Setup Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your API keys (see API Keys section below).

### 6. Run the Application

```bash
# Web interface + API
python -m uvicorn main:app --reload --port 8000

# Discord bot (separate terminal)
python -m agent.discord_bot
```

Open browser: `http://localhost:8000`

---

## 🔑 API Keys — Where to Get Them

### 1. Groq API Key (FREE) ⭐ Most Important
> Used for: Speech-to-Text (Whisper) + AI Summary (LLaMA 3.3)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up with Google (free)
3. Click **"API Keys"** → **"Create API Key"**
4. Copy key → paste in `.env` as `GROQ_API_KEY`

**Free tier:** 28,800 seconds/day transcription + 14,400 requests/day LLM

---

### 2. Discord Bot Token (FREE)
> Used for: Discord bot — always online, sends summaries

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **"New Application"** → name it `MeetingAgent`
3. Left sidebar → **"Bot"** → **"Reset Token"** → copy token
4. Enable **"Message Content Intent"** and **"Server Members Intent"**
5. Go to **"OAuth2"** → **"URL Generator"**
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Send Messages`, `Read Message History`, `View Channels`
6. Copy generated URL → open in browser → add bot to your server
7. Paste token in `.env` as `DISCORD_TOKEN`

---

### 3. Discord Server ID (Guild ID) (FREE)
> Used for: Connecting bot to your specific server

1. Open Discord app
2. **Settings** → **Advanced** → enable **"Developer Mode"**
3. Right-click your server name → **"Copy Server ID"**
4. Paste in `.env` as `DISCORD_GUILD_ID`

---

### 4. Google Cloud — Gmail API (FREE)
> Used for: Reading emails to detect meeting links automatically

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create new project → name it `MeetingAgent`
3. **APIs & Services** → **"Enable APIs"** → search **"Gmail API"** → Enable
4. **APIs & Services** → **"OAuth consent screen"**
   - User Type: External → Create
   - App name: `MeetingAgent`
   - Add your email as test user
5. **APIs & Services** → **"Credentials"** → **"+ Create Credentials"** → **"OAuth 2.0 Client ID"**
   - Application type: **Desktop app**
   - Download JSON → save as `credentials.json` in project root
6. First run will open browser for Google login → `token.json` will be created automatically

---

### 5. Google OAuth — Web Login (FREE)
> Used for: Users connecting their Google account on website

1. Same Google Cloud project
2. **APIs & Services** → **"Credentials"** → **"+ Create Credentials"** → **"OAuth 2.0 Client ID"**
   - Application type: **Web application**
   - Authorized redirect URIs: `http://localhost:8000/auth/google/callback`
   - (For production: add your domain URL too)
3. Copy **Client ID** and **Client Secret**
4. Paste in `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

---

## 📄 Environment Variables

Create `.env` file in project root:

```env
# Groq AI (FREE) — https://console.groq.com
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Discord Bot (FREE) — https://discord.com/developers
DISCORD_TOKEN=MTxxxxxxxxxxxxxxxxxx
DISCORD_GUILD_ID=123456789012345678

# Optional: Auto DM to new Discord members
DISCORD_WELCOME_DM_ENABLED=true
DISCORD_WELCOME_DM_TEMPLATE=Namaste {member_name}! {server_name} me welcome. !help bhej kar commands dekh lo.

# Google OAuth (FREE) — https://console.cloud.google.com
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxx
```

> ⚠️ **Never commit `.env` to GitHub!** It's already in `.gitignore`

---

## 🤖 Discord Bot Commands

| Command | Description |
|---------|-------------|
| `!ping` | Check if bot is online |
| `!summary [text]` | Get AI summary of any meeting text |
| `!meeting [link]` | Join a meeting via bot |

### Running Discord Bot

```bash
python -m agent.discord_bot
```

Bot will print: `Bot online: MeetingAgent#XXXX`

---

## 🌐 Web Interface

### Register & Login
- Go to `http://localhost:8000`
- Click **"Get Started"** → create account
- Login with your credentials

### Join a Meeting
1. Login to dashboard
2. Paste meeting link in **"Quick Join Meeting"** box
3. Enter your name (shown in meeting)
4. Enter Gmail + password for bot to join
5. Click **"Join & Record"**
6. Bot joins meeting, records audio, generates summary

### View Summaries
- Dashboard → scroll down → **"Recent Meetings"**
- Click any meeting → summary popup appears
- Copy summary to clipboard

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Uvicorn |
| Frontend | HTML + CSS + Vanilla JS |
| Database | SQLite (dev) / PostgreSQL (prod) |
| AI STT | Groq Whisper Large V3 |
| AI LLM | Groq LLaMA 3.3 70B |
| Browser Automation | Playwright (Chromium) |
| Audio Recording | FFmpeg + PyAudio |
| Discord | discord.py |
| Email | Gmail API (google-api-python-client) |
| Auth | bcrypt + Google OAuth |

---

## 🚀 Deployment (DigitalOcean)

> Get $200 free credit via [GitHub Student Pack](https://education.github.com/pack)

```bash
# Build Docker image
docker build -t meetingagent .

# Run container
docker run -d -p 8000:8000 --env-file .env meetingagent
```

---

## 📦 Installation Issues

### Playwright on Linux
```bash
sudo apt-get install -y libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2t64
playwright install-deps chromium
```

### PyAudio on Windows
```bash
pip install pipwin
pipwin install pyaudio
```

### Virtual Environment Issues
```bash
# Delete and recreate
rm -rf venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/AmazingFeature`
3. Commit changes: `git commit -m 'Add AmazingFeature'`
4. Push to branch: `git push origin feature/AmazingFeature`
5. Open Pull Request

---

## 📝 License

MIT License — feel free to use, modify, and distribute.

---

## 👨‍💻 Built With

- [Groq](https://groq.com) — Free AI API
- [FastAPI](https://fastapi.tiangolo.com) — Python web framework
- [Playwright](https://playwright.dev) — Browser automation
- [discord.py](https://discordpy.readthedocs.io) — Discord bot library
- [Google APIs](https://developers.google.com) — Gmail + Meet

---

*Made with ❤️ — Open Source Forever*


**Contributer**
@alfa546 
@Sami0468
