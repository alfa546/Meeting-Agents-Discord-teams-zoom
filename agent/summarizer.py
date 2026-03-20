import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def summarize_transcript(transcript: str) -> dict:
    """Transcript se meeting summary nikalo"""
    print("Summarizing transcript...")

    prompt = f"""
You are a meeting assistant. Analyze this meeting transcript and provide:

1. **Meeting Summary** (3-4 lines)
2. **Key Points** (bullet points)
3. **Action Items** (who needs to do what)
4. **Decisions Made**

Transcript:
{transcript}

Always respond in Roman Urdu (Urdu written in English letters). For example: "Is meeting 
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500
    )

    summary = response.choices[0].message.content
    return {
        "summary": summary,
        "transcript": transcript
    }