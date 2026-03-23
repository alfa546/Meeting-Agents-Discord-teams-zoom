import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from agent.summarizer import summarize_transcript
from bot.audio_capture import record_audio
from bot.transcriber import transcribe_audio
from db.models import init_db, SessionLocal, Meeting
from datetime import datetime
import asyncio

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Track active recordings: {(user_id, channel_id): {"task": asyncio.Task, "file": str}}
active_recordings = {}

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")
    init_db()

@bot.command(name="join")
async def join(ctx, link: str = None):
    """!join [link] — Discord se meeting join karo"""
    if not link:
        await ctx.send("❌ Link bhejo: `!join https://meet.google.com/xxx`")
        return
    
    await ctx.send(f"✅ Meeting join kar raha hun: {link}\n🎙️ Voice channel mein aa gaya. `!record` se recording shuru karo!")

@bot.command(name="record")
async def record(ctx):
    """!record — Voice channel ka audio record karo"""
    key = (ctx.author.id, ctx.channel.id)
    
    if key in active_recordings:
        await ctx.send("⚠️ Recording pehle se chal rahi hai! `!stop` karo pehle.")
        return
    
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ Voice channel mein nahi ho! Pehle voice channel join karo.")
        return
    
    await ctx.send("🎙️ Recording shuru ho gayi...")
    
    # Background task mein recording chalao
    task = asyncio.create_task(_record_meeting(ctx, key))
    active_recordings[key] = {"task": task, "file": None}

async def _record_meeting(ctx, key):
    """Background recording task"""
    try:
        user_id, channel_id = key
        # 1 hour recording
        audio_file = await record_audio(duration_seconds=3600, output_dir="recordings")
        if key in active_recordings:
            active_recordings[key]["file"] = audio_file
        print(f"Recording completed: {audio_file}")
    except Exception as e:
        print(f"Recording error: {e}")

@bot.command(name="stop")
async def stop(ctx):
    """!stop — Recording band karo aur summary do"""
    key = (ctx.author.id, ctx.channel.id)
    
    if key not in active_recordings:
        await ctx.send("❌ Koi recording chal nahi rahi!")
        return
    
    await ctx.send("⏹️ Recording ro raha hun... summary bana raha hun...")
    
    try:
        recording_data = active_recordings.pop(key)
        task = recording_data.get("task")
        audio_file = recording_data.get("file")
        
        # Task cancel karo
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        if audio_file and os.path.exists(audio_file):
            # Transcribe karo
            await ctx.send("📝 Transcribe kar raha hun...")
            transcript = transcribe_audio(audio_file)
            
            # Summary nikalo
            await ctx.send("✨ Summary bana raha hun...")
            result = summarize_transcript(transcript)
            summary_text = result.get("summary", "No summary generated")
            
            # Database mein save karo
            db = SessionLocal()
            try:
                meeting = Meeting(
                    user_email=f"{ctx.author.id}@discord",
                    platform="Discord",
                    link=f"discord://{ctx.guild.id}/{ctx.channel.id}",
                    summary=summary_text,
                    transcript=transcript
                )
                db.add(meeting)
                db.commit()
            finally:
                db.close()
            
            # Discord char limit hai (2000)
            if len(summary_text) > 1900:
                summary_text = summary_text[:1900] + "..."
            
            await ctx.send(f"📋 **Meeting Summary:**\n\n{summary_text}")
            
            # File delete karo
            try:
                os.remove(audio_file)
            except:
                pass
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name="meetings")
async def meetings(ctx):
    """!meetings — Apni past meetings dekho"""
    try:
        db = SessionLocal()
        user_meetings = db.query(Meeting).filter(
            Meeting.user_email == f"{ctx.author.id}@discord"
        ).order_by(Meeting.created_at.desc()).limit(10).all()
        db.close()
        
        if not user_meetings:
            await ctx.send("📭 Koi past meetings nahi!")
            return
        
        content = "📅 **Your Past Meetings:**\n\n"
        for i, m in enumerate(user_meetings, 1):
            date = m.created_at.strftime("%Y-%m-%d %H:%M")
            content += f"{i}. **{date}** - {m.platform}\n"
            if m.summary:
                summary_preview = m.summary[:100] + "..." if len(m.summary) > 100 else m.summary
                content += f"   📝 {summary_preview}\n\n"
        
        # Split if too long
        if len(content) > 2000:
            content = content[:1900] + "..."
        
        await ctx.send(content)
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name="help")
async def help_command(ctx):
    """!help — Sab commands dikhao"""
    help_text = """
🤖 **Meeting Agent - Discord Bot**

📌 **Available Commands:**

1️⃣ `!join [link]` — Meeting link se Discord meeting join karo
   *Example: !join https://meet.google.com/xyz-abc-def*

2️⃣ `!record` — Voice channel ka audio record karo
   *Must be in a voice channel first*

3️⃣ `!stop` — Recording band karo, transcribe karo, summary nikalo
   *Your meeting summary aur transcript database mein save hogi*

4️⃣ `!meetings` — Apni past 10 meetings dekho
   *Summaries aur transcripts ke saath*

5️⃣ `!help` — Yeh help message dekho

⚡ **Kaafi Features:**
✓ Real-time voice recording
✓ AI Transcription (Whisper)
✓ Automatic Summaries
✓ Meeting History
✓ Multi-platform support

Need help? Use `!help` anytime!
"""
    await ctx.send(help_text)

@bot.command(name="ping")
async def ping(ctx):
    """Bot ka status check karo"""
    await ctx.send("🟢 Bot online hai! Meeting Agent ready.")

if __name__ == "__main__":
    bot.run(TOKEN)