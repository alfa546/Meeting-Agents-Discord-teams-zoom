import os
import json
import re
from collections import Counter
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _basic_sentiment(text: str) -> str:
    low = (text or "").lower()
    pos_words = ["good", "great", "excellent", "done", "success", "happy", "improve", "resolved", "achieve"]
    neg_words = ["issue", "problem", "delay", "risk", "blocked", "failed", "error", "concern", "urgent"]
    pos = sum(1 for w in pos_words if w in low)
    neg = sum(1 for w in neg_words if w in low)
    if pos > neg:
        return "Positive"
    if neg > pos:
        return "Negative"
    return "Neutral"


def _fallback_analytics(transcript: str) -> dict:
    lines = [ln.strip() for ln in (transcript or "").splitlines() if ln.strip()]
    speaker_counter = Counter()
    for line in lines:
        m = re.match(r"^([A-Za-z][A-Za-z0-9_\- ]{1,25})\s*:\s+", line)
        if m:
            speaker_counter[m.group(1).strip()] += 1

    if not speaker_counter:
        speaker_counter["Speaker 1"] = max(1, len(lines) // 4 or 1)

    word_counter = Counter(re.findall(r"[A-Za-z]{4,}", (transcript or "").lower()))
    stop = {
        "this", "that", "with", "from", "have", "were", "will", "your", "about", "there", "their",
        "they", "them", "what", "when", "where", "which", "would", "could", "should", "into", "than"
    }
    topics = []
    for token, count in word_counter.most_common(8):
        if token in stop:
            continue
        topics.append({"topic": token.capitalize(), "share": min(80, 10 + count * 3)})
        if len(topics) >= 4:
            break
    if not topics:
        topics = [{"topic": "General Discussion", "share": 100}]

    return {
        "speaker_counts": [{"speaker": k, "turns": v} for k, v in speaker_counter.most_common(6)],
        "topic_breakdown": topics,
        "sentiment": {
            "overall": _basic_sentiment(transcript),
            "positive": 34,
            "neutral": 40,
            "negative": 26
        }
    }

def summarize_transcript(transcript: str, target_language: str = "auto") -> dict:
    """Transcript se meeting summary nikalo"""
    print("Summarizing transcript...")

    normalized = (target_language or "auto").strip().lower()
    if normalized not in {"auto", "english", "urdu", "hindi"}:
        normalized = "auto"

    language_rule = """
LANGUAGE RULES - Follow strictly:
- If transcript is in English only -> respond in English
- If transcript is in Urdu only -> respond in Roman Urdu (Urdu written in English letters, NOT Urdu script)
- If transcript is mixed Urdu/English -> respond in Roman Urdu
- NEVER use Urdu script characters
- NEVER use Arabic script
- Roman Urdu example: "Is meeting mein discuss hua ke project deadline extend hogi"
"""

    if normalized == "english":
        language_rule = "Respond only in clear English."
    elif normalized == "urdu":
        language_rule = "Respond only in Roman Urdu. Do not use Urdu/Arabic script."
    elif normalized == "hindi":
        language_rule = "Respond only in Hindi written in Devanagari script."

    prompt = f"""
You are a meeting assistant. Analyze this meeting transcript and provide a summary.

{language_rule}

Provide:
1. **Meeting Summary** (3-4 lines)
2. **Key Points** (bullet points)
3. **Action Items** (who needs to do what)
4. **Decisions Made**

Transcript:
{transcript}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500
    )

    summary = response.choices[0].message.content
    return {
        "summary": summary,
        "transcript": transcript,
        "language": normalized
    }


def analyze_transcript(transcript: str) -> dict:
    """Meeting analytics: speaker turns, topic breakdown, sentiment."""
    text = (transcript or "").strip()
    if not text:
        return _fallback_analytics(text)

    prompt = f"""
You are a meeting analytics assistant.
Return ONLY strict JSON with this shape:
{{
  "speaker_counts": [{{"speaker": "Name", "turns": 4}}],
  "topic_breakdown": [{{"topic": "Topic Name", "share": 35}}],
  "sentiment": {{"overall": "Positive|Neutral|Negative", "positive": 30, "neutral": 50, "negative": 20}}
}}

Rules:
- speaker_counts: max 8 speakers, turns = how many times they spoke.
- topic_breakdown: max 6 topics, share as integer percentages and total close to 100.
- sentiment percentages should total 100.
- If speaker names are missing, use Speaker 1, Speaker 2 style.

Transcript:
{text}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.replace("json", "", 1).strip()

        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Invalid analytics payload")

        parsed.setdefault("speaker_counts", [])
        parsed.setdefault("topic_breakdown", [])
        parsed.setdefault("sentiment", {})
        sentiment = parsed["sentiment"] if isinstance(parsed["sentiment"], dict) else {}
        sentiment.setdefault("overall", _basic_sentiment(text))
        sentiment.setdefault("positive", 33)
        sentiment.setdefault("neutral", 34)
        sentiment.setdefault("negative", 33)
        parsed["sentiment"] = sentiment
        return parsed
    except Exception:
        return _fallback_analytics(text)