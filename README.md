# Channel Agent Hub (Discord + Gmail + WhatsApp)

This project has been cleaned from meeting platform features and now focuses on three channels only:

- Discord
- Gmail
- WhatsApp

It includes:
- FastAPI backend
- Dashboard frontend
- Discord bot utilities
- Gmail helper utilities
- WhatsApp helper utilities
- AI text summarization endpoint

## Scope Update

Removed from this project scope:
- Google Meet, Zoom, Teams join automation
- Calendar meeting sync flows
- Meeting room UI
- Meeting analytics/history endpoints
- OAuth routes dedicated to meeting workflows

Current scope:
- User auth (local)
- Channel integration state tracking (Discord, Gmail, WhatsApp)
- Summarize long text via Groq
- Optional audio transcription endpoint

## Project Structure

```text
Meeting-Agents-Discord-teams-zoom/
├── main.py                    # FastAPI backend (channel-focused)
├── scheduler.py               # In-memory reminder scheduler
├── requirements.txt           # Clean dependency set
├── credentials.json           # Gmail OAuth desktop credentials (optional)
├── meetingagent.db            # SQLite database
│
├── agent/
│   ├── discord_bot.py         # Discord channel assistant bot
│   ├── email_handler.py       # Gmail important-email helper
│   ├── whatsapp_handler.py    # WhatsApp API helper
│   └── summarizer.py          # Groq LLM summarizer
│
├── bot/
│   ├── transcriber.py         # Groq Whisper transcription
│
│
├── db/
│   └── models.py              # SQLAlchemy models
│
└── web/
    └── templates/
        └── index.html         # Frontend dashboard
```

## Setup

### 1. Clone and enter directory

```bash
git clone https://github.com/alfa546/Meeting-Agents-Discord-teams-zoom.git
cd Meeting-Agents-Discord-teams-zoom
```

### 2. Create and activate virtualenv

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create `.env` in the project root.

```env
# Core AI
GROQ_API_KEY=your_groq_key

# Discord
DISCORD_TOKEN=your_discord_bot_token
DISCORD_WELCOME_DM_ENABLED=true
DISCORD_WELCOME_DM_TEMPLATE=Namaste {member_name}. {server_name} me welcome.

# WhatsApp gateway
WHATSAPP_API_URL=https://your-whatsapp-provider.example/send
WHATSAPP_API_TOKEN=your_whatsapp_token
```

For Gmail helper:
- Keep `credentials.json` in root (Google desktop OAuth credentials).
- On first run, `token.json` is generated after consent.

## Run

### Start backend

```bash
uvicorn main:app --reload --port 8000
```

Open:
- http://localhost:8000

### Start Discord bot (optional)

```bash
python -m agent.discord_bot
```

## API Endpoints

### Auth
- `POST /api/register`
- `POST /api/login`

### Channel integrations
- `POST /api/platform/connect`
- `POST /api/platform/disconnect`
- `GET /api/platform/status/{email}`

Supported platform values:
- `discord`
- `gmail`
- `whatsapp`

### AI utilities
- `POST /api/summarize`
- `POST /api/transcribe`

### Health
- `GET /api/health`

## Discord Bot Commands

- `!ping`
- `!summary <text>`
- `!remind <minutes> <message>`
- `!help`

## License

MIT

