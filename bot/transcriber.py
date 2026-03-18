import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe_audio(file_path: str) -> str:
    """Audio file ko text mein convert karo Groq Whisper se"""
    print(f"Transcribing: {file_path}")
    
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file,
            response_format="text"
        )
    
    return transcription

def save_transcript(transcript: str, output_path: str):
    """Transcript ko file mein save karo"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript)
    print(f"Transcript saved: {output_path}")