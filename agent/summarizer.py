import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def summarize_transcript(transcript: str, target_language: str = "auto") -> dict:
    """Generate summary from long text, chat logs, or transcripts."""
    text = (transcript or "").strip()
    if not text:
        return {"summary": "", "transcript": transcript, "language": target_language}

    normalized = (target_language or "auto").strip().lower()
    if normalized not in {"auto", "english", "urdu", "hindi"}:
        normalized = "auto"

    language_rule = """
LANGUAGE RULES - Follow strictly:
- If input is English only -> respond in English
- If input is Urdu only -> respond in Roman Urdu (English letters)
- If input is mixed Urdu/English -> respond in Roman Urdu
- Do not use Urdu/Arabic script when Roman Urdu is requested
"""

    if normalized == "english":
        language_rule = "Respond only in clear English."
    elif normalized == "urdu":
        language_rule = "Respond only in Roman Urdu. Do not use Urdu/Arabic script."
    elif normalized == "hindi":
        language_rule = "Respond only in Hindi written in Devanagari script."

    prompt = f"""
You are an assistant for communication summaries.

{language_rule}

Provide:
1. Summary (3-4 lines)
2. Key Points (bullets)
3. Action Items
4. Decisions / Final Outcomes

Input text:
{text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
    )

    summary = (response.choices[0].message.content or "").strip()
    return {
        "summary": summary,
        "transcript": transcript,
        "language": normalized,
    }
