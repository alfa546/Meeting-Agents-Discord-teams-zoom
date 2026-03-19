import os
import time
import requests
from dotenv import load_dotenv
from agent.summarizer import summarize_transcript

try:
    import jwt
except ImportError:
    raise ImportError("PyJWT install karo: pip install PyJWT")

load_dotenv()

# ── Zoom Credentials ──────────────────────────────────────
ZOOM_API_KEY       = os.getenv("ZOOM_API_KEY")       # Zoom App → Credentials → API Key
ZOOM_API_SECRET    = os.getenv("ZOOM_API_SECRET")    # Zoom App → Credentials → API Secret
ZOOM_API_BASE      = "https://api.zoom.us/v2"


# ═════════════════════════════════════════════════════════
#  JWT Token Generator
# ═════════════════════════════════════════════════════════
def generate_zoom_jwt() -> str:
    """Zoom JWT token generate karo (60 seconds valid)."""
    payload = {
        "iss": ZOOM_API_KEY,
        "exp": int(time.time()) + 60,
    }
    token = jwt.encode(payload, ZOOM_API_SECRET, algorithm="HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def zoom_headers() -> dict:
    return {
        "Authorization": f"Bearer {generate_zoom_jwt()}",
        "Content-Type":  "application/json",
    }


# ═════════════════════════════════════════════════════════
#  Zoom API Functions
# ═════════════════════════════════════════════════════════
def create_zoom_meeting(topic: str = "Bot Meeting", duration: int = 60) -> dict | None:
    """Naya instant Zoom meeting create karo."""
    url = f"{ZOOM_API_BASE}/users/me/meetings"
    payload = {
        "topic":    topic,
        "type":     1,          # 1 = instant meeting
        "duration": duration,
        "settings": {
            "host_video":        True,
            "participant_video": True,
            "join_before_host":  True,
            "auto_recording":    "none",
        },
    }
    resp = requests.post(url, headers=zoom_headers(), json=payload, timeout=10)
    return resp.json() if resp.status_code == 201 else None


def get_zoom_meeting(meeting_id: str) -> dict | None:
    """Meeting details fetch karo."""
    url = f"{ZOOM_API_BASE}/meetings/{meeting_id}"
    resp = requests.get(url, headers=zoom_headers(), timeout=10)
    return resp.json() if resp.status_code == 200 else None


def list_zoom_meetings() -> list:
    """Upcoming meetings ki list lo."""
    url = f"{ZOOM_API_BASE}/users/me/meetings"
    resp = requests.get(url, headers=zoom_headers(), timeout=10)
    return resp.json().get("meetings", []) if resp.status_code == 200 else []


def end_zoom_meeting(meeting_id: str) -> bool:
    """Meeting end karo."""
    url = f"{ZOOM_API_BASE}/meetings/{meeting_id}/status"
    resp = requests.put(url, headers=zoom_headers(),
                        json={"action": "end"}, timeout=10)
    return resp.status_code == 204


def get_meeting_summary(meeting_id: str) -> str | None:
    """Meeting transcript/summary fetch karo (agar recording ho)."""
    url = f"{ZOOM_API_BASE}/meetings/{meeting_id}/recordings"
    resp = requests.get(url, headers=zoom_headers(), timeout=10)
    if resp.status_code != 200:
        return None
    data     = resp.json()
    files    = data.get("recording_files", [])
    transcripts = [f for f in files if f.get("file_type") == "TRANSCRIPT"]
    return transcripts[0].get("download_url") if transcripts else None


# ═════════════════════════════════════════════════════════
#  CLI / Webhook Command Handler
# ═════════════════════════════════════════════════════════
def handle_command(command: str, args: str = "") -> str:
    """
    Commands handle karo aur result string return karo.
    Yahan se tum apna webhook, Slack bot, ya koi bhi
    interface connect kar sakte ho.
    """

    if command == "meeting":
        topic = args.strip() or "Bot Meeting"
        data  = create_zoom_meeting(topic=topic)
        if not data:
            return "❌ Meeting create nahi hui. API credentials check karo."
        return (
            f"✅ Zoom Meeting Ready!\n"
            f"📌 Topic     : {data.get('topic')}\n"
            f"🆔 Meeting ID: {data.get('id')}\n"
            f"🔑 Password  : {data.get('password', 'N/A')}\n"
            f"🔗 Join Link : {data.get('join_url')}\n"
            f"🎙️ Host Link : {data.get('start_url')}"
        )

    elif command == "joinmeeting":
        meeting_id = args.strip()
        if not meeting_id:
            return "❌ Meeting ID bhejo: joinmeeting 123456789"
        data = get_zoom_meeting(meeting_id)
        if not data or "code" in data:
            return f"❌ Meeting '{meeting_id}' nahi mili."
        return (
            f"🔗 {data.get('topic', 'Zoom Meeting')}\n"
            f"🆔 ID       : {meeting_id}\n"
            f"🔑 Password : {data.get('password', 'N/A')}\n"
            f"🔗 Join Link: {data.get('join_url')}"
        )

    elif command == "meetings":
        meeting_list = list_zoom_meetings()
        if not meeting_list:
            return "📭 Koi upcoming meeting nahi hai."
        lines = ["📅 Upcoming Zoom Meetings:"]
        for m in meeting_list[:10]:
            lines.append(f"  • {m.get('topic')} (ID: {m.get('id')}) — {m.get('join_url')}")
        return "\n".join(lines)

    elif command == "endmeeting":
        meeting_id = args.strip()
        if not meeting_id:
            return "❌ Meeting ID bhejo: endmeeting 123456789"
        return (
            f"✅ Meeting '{meeting_id}' end kar di."
            if end_zoom_meeting(meeting_id)
            else f"❌ Meeting end nahi hui. ID ya permissions check karo."
        )

    elif command == "summary":
        transcript = args.strip()
        if not transcript:
            return "❌ Text bhejo: summary Ali ne kaha..."
        result       = summarize_transcript(transcript)
        summary_text = result["summary"]
        if len(summary_text) > 1900:
            summary_text = summary_text[:1900] + "..."
        return f"📋 Meeting Summary:\n\n{summary_text}"

    elif command == "ping":
        zoom_ok = "✅ Configured" if (ZOOM_API_KEY and ZOOM_API_SECRET) else "❌ Missing"
        return f"🟢 Zoom Bot online hai!\n🔑 Zoom API: {zoom_ok}"

    else:
        return (
            "❓ Available commands:\n"
            "  meeting [topic]      — Naya Zoom meeting banao\n"
            "  joinmeeting <id>     — Meeting details dekho\n"
            "  meetings             — Saari meetings list karo\n"
            "  endmeeting <id>      — Meeting end karo\n"
            "  summary <text>       — Text ki summary banao\n"
            "  ping                 — Status check karo"
        )


# ═════════════════════════════════════════════════════════
#  Run as CLI (test ke liye)
# ═════════════════════════════════════════════════════════
if __name__ == "__main__":
    if not ZOOM_API_KEY or not ZOOM_API_SECRET:
        print("⚠️  .env mein ZOOM_API_KEY aur ZOOM_API_SECRET set karo!")
    else:
        print("🟢 Zoom Bot CLI ready. 'quit' type karo bahar aane ke liye.\n")

    while True:
        try:
            user_input = input("Command> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Bye!")
            break

        parts   = user_input.split(maxsplit=1)
        cmd     = parts[0].lower()
        arg_str = parts[1] if len(parts) > 1 else ""
        print(handle_command(cmd, arg_str), "\n")