# Discord and Gmail Status (Current)

This file explains which Discord and Gmail features are currently working in the project, and how to connect them from the website.

## 1) What Discord is currently doing

### A. Website integration level
- A Discord integration card is available in the website dashboard.
- When a user fills Discord credentials and clicks Connect, the backend saves platform status as `connected=true`.
- Clicking Disconnect updates status to `connected=false`.
- The dashboard Connected Apps count updates accordingly.

### B. Discord bot level
The Discord bot module currently supports:
- `!ping`: replies with bot online status.
- `!summary <text>`: generates an AI summary for long text.
- `!remind <minutes> <message>`: schedules an in-memory reminder and sends the message at the scheduled time.
- `!help`: shows the list of available commands.
- Optional welcome DM for new members (controlled via environment variable).

### C. Required environment variables for Discord bot
- `DISCORD_TOKEN`
- `DISCORD_WELCOME_DM_ENABLED` (optional)
- `DISCORD_WELCOME_DM_TEMPLATE` (optional)

## 2) What Gmail is currently doing

### A. Website integration level
- A Gmail integration card is available in the website dashboard.
- Gmail Address and App Password fields are present in the UI.
- Clicking Connect saves Gmail status as connected in the backend database.
- Clicking Disconnect marks the Gmail status as disconnected.

Important:
- The current website Connect action does not execute the full Gmail OAuth flow.
- From the website side, this is currently integration state tracking (save/retrieve status), not full mailbox automation.

### B. Gmail helper module level
The backend Gmail helper currently supports:
- OAuth token generation/refresh using `credentials.json` and `token.json`.
- Fetching recent important/primary emails.
- Extracting subject, sender, snippet, and links.

Important:
- The Gmail helper logic exists, but there is no dedicated FastAPI endpoint yet to expose full Gmail mailbox actions directly through the website.

## 3) How to connect Discord and Gmail from the website

1. Start the backend:
   - `uvicorn main:app --reload --port 8000`

2. Open in browser:
   - `http://localhost:8000`

3. Create an account or log in first:
   - Integrations require an authenticated user session.

4. Open the `Integrations` tab in the dashboard.

5. Connect Discord:
   - Enter Bot Token and Server ID in the Discord card.
   - Click `Connect`.
   - On success, the badge changes to `Connected`.

6. Connect Gmail:
   - Enter Gmail Address and App Password in the Gmail card.
   - Click `Connect`.
   - On success, the badge changes to `Connected`.

7. To disconnect any platform:
   - Click `Disconnect` on the same integration card.

## 4) How data is stored in backend
- Platform connect/disconnect APIs save status in the `platforms` table.
- Currently supported platforms:
  - `discord`
  - `gmail`
  - `whatsapp`

## 5) Current progress summary
- Discord: Website status tracking and bot commands are both working.
- Gmail: Website status tracking is working, Gmail helper code is ready, but direct mailbox actions from website are not fully wired yet.
