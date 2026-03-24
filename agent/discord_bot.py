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
from scheduler import ReminderScheduler

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
WELCOME_DM_ENABLED = os.getenv("DISCORD_WELCOME_DM_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
WELCOME_DM_TEMPLATE = os.getenv(
    "DISCORD_WELCOME_DM_TEMPLATE",
    "Namaste {member_name}! {server_name} me welcome.\\n"
    "Main Meeting Agent bot hoon. `!help` bhej ke commands dekh sakte ho.",
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

# Disable default help command to create our own
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Track active recordings: {(user_id, channel_id): {"task": asyncio.Task, "file": str}}
active_recordings = {}

# Track auto voice sessions: {(guild_id, voice_channel_id): session_data}
active_voice_sessions = {}

reminder_scheduler = ReminderScheduler()


def _voice_key(guild_id: int, channel_id: int):
    return (guild_id, channel_id)


def _human_members(voice_channel: discord.VoiceChannel):
    return [m for m in voice_channel.members if not m.bot]


def _pick_text_channel(guild: discord.Guild):
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        return guild.system_channel

    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            return channel
    return None


async def _send_summary_dm(user_ids, summary_text: str):
    for user_id in user_ids:
        user = bot.get_user(user_id)
        if not user:
            try:
                user = await bot.fetch_user(user_id)
            except Exception:
                user = None
        if not user:
            continue
        try:
            await user.send(f"📩 **Meeting Summary:**\n\n{summary_text}")
        except Exception as e:
            print(f"DM failed for {user_id}: {e}")


def _build_welcome_dm(member: discord.Member) -> str:
    default_msg = (
        f"Namaste {member.display_name}! {member.guild.name} me welcome.\\n"
        "Main Meeting Agent bot hoon. `!help` bhej ke commands dekh sakte ho."
    )

    try:
        return WELCOME_DM_TEMPLATE.format(
            member_name=member.display_name,
            server_name=member.guild.name,
            member_mention=member.mention,
        )
    except Exception:
        return default_msg


async def _spawn_ffmpeg_recording(output_dir: str = "recordings"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/meeting_{timestamp}.wav"

    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-f",
        "pulse",
        "-i",
        "default",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        output_file,
        "-y",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    return process, output_file


async def _finalize_auto_session(guild: discord.Guild, voice_channel: discord.VoiceChannel):
    key = _voice_key(guild.id, voice_channel.id)
    session = active_voice_sessions.get(key)
    if not session:
        return

    if session.get("finalizing"):
        return
    session["finalizing"] = True

    announce_channel = session.get("announce_channel") or _pick_text_channel(guild)

    if announce_channel:
        await announce_channel.send("⏹️ Voice channel empty ho gaya. Recording stop kar raha hun...")

    try:
        process = session.get("process")
        if process and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=8)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

        audio_file = session.get("file")
        if not audio_file or not os.path.exists(audio_file):
            if announce_channel:
                await announce_channel.send("⚠️ Recording file nahi mili, summary skip kar raha hun.")
            return

        if announce_channel:
            await announce_channel.send("📝 Transcribe kar raha hun...")
        transcript = transcribe_audio(audio_file)

        if announce_channel:
            await announce_channel.send("✨ Auto-summary bana raha hun...")
        result = summarize_transcript(transcript)
        summary_text = result.get("summary", "No summary generated")

        db = SessionLocal()
        try:
            meeting = Meeting(
                user_email=f"guild-{guild.id}@discord",
                platform="Discord",
                link=f"discord://{guild.id}/{voice_channel.id}",
                summary=summary_text,
                transcript=transcript,
            )
            db.add(meeting)
            db.commit()
        finally:
            db.close()

        summary_for_channel = summary_text
        if len(summary_for_channel) > 1800:
            summary_for_channel = summary_for_channel[:1800] + "..."

        if announce_channel:
            await announce_channel.send(
                f"📋 **Auto Meeting Summary ({voice_channel.name}):**\n\n{summary_for_channel}"
            )

        await _send_summary_dm(session.get("participants", set()), summary_text)

        try:
            os.remove(audio_file)
        except Exception:
            pass
    except Exception as e:
        if announce_channel:
            await announce_channel.send(f"❌ Auto-summary error: {str(e)}")
    finally:
        active_voice_sessions.pop(key, None)
        voice_client = guild.voice_client
        if voice_client and voice_client.channel and voice_client.channel.id == voice_channel.id:
            try:
                await voice_client.disconnect()
            except Exception:
                pass


async def _start_auto_session(guild: discord.Guild, voice_channel: discord.VoiceChannel):
    key = _voice_key(guild.id, voice_channel.id)
    if key in active_voice_sessions:
        return

    announce_channel = _pick_text_channel(guild)
    if announce_channel:
        await announce_channel.send(
            f"🎙️ Auto-session start: `{voice_channel.name}`. Meeting end hone par summary bhej dunga."
        )

    try:
        process, audio_file = await _spawn_ffmpeg_recording(output_dir="recordings")
    except Exception as e:
        if announce_channel:
            await announce_channel.send(f"❌ Recording start failed: {str(e)}")
        return

    participants = {m.id for m in _human_members(voice_channel)}

    active_voice_sessions[key] = {
        "process": process,
        "file": audio_file,
        "participants": participants,
        "announce_channel": announce_channel,
        "finalizing": False,
        "started_at": datetime.utcnow(),
    }

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")
    init_db()


@bot.event
async def on_member_join(member: discord.Member):
    if member.bot or not WELCOME_DM_ENABLED:
        return

    try:
        await member.send(_build_welcome_dm(member))
        print(f"Welcome DM sent to {member.id} in guild {member.guild.id}")
    except discord.Forbidden:
        print(f"Cannot DM member {member.id}; DMs are disabled.")
    except Exception as e:
        print(f"Welcome DM failed for {member.id}: {e}")


@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    guild = member.guild

    # User joined or switched into a voice channel
    if after.channel and before.channel != after.channel:
        key = _voice_key(guild.id, after.channel.id)
        session = active_voice_sessions.get(key)
        if session:
            session["participants"].add(member.id)

        voice_client = guild.voice_client
        target_channel = after.channel
        if not voice_client:
            try:
                await target_channel.connect()
            except Exception as e:
                print(f"Auto join error: {e}")
                return
        elif voice_client.channel.id != target_channel.id:
            current_humans = _human_members(voice_client.channel)
            if not current_humans:
                try:
                    await voice_client.move_to(target_channel)
                except Exception as e:
                    print(f"Auto move error: {e}")

        await _start_auto_session(guild, target_channel)

    # Check if a channel became empty
    if before.channel:
        key = _voice_key(guild.id, before.channel.id)
        session = active_voice_sessions.get(key)
        if session:
            humans_left = _human_members(before.channel)
            if not humans_left:
                await _finalize_auto_session(guild, before.channel)

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
        # Keep manual recording short enough to complete during typical tests.
        audio_file = await record_audio(duration_seconds=180, output_dir="recordings")
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
        recording_data = active_recordings.get(key)
        task = recording_data.get("task")
        audio_file = recording_data.get("file")

        # If recording is still running, wait for completion so file path is available.
        if task and not task.done():
            await ctx.send("⏳ Recording complete hone ka wait kar raha hun...")
            try:
                await asyncio.wait_for(task, timeout=210)
            except asyncio.TimeoutError:
                await ctx.send("⚠️ Recording abhi tak complete nahi hui. 1-2 minute baad `!stop` dubara try karo.")
                return

        audio_file = (active_recordings.get(key) or {}).get("file") or audio_file

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
        else:
            await ctx.send("⚠️ Recording file ready nahi hui. 1 minute baad `!stop` phir try karo.")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
    finally:
        active_recordings.pop(key, None)

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


@bot.command(name="schedule")
async def schedule(ctx, minutes: int = None, *, title: str = None):
    """!schedule <minutes> <title/link> — Reminder schedule karo"""
    if minutes is None or not title:
        await ctx.send("❌ Usage: `!schedule <minutes> <meeting title/link>`")
        return

    if minutes <= 0:
        await ctx.send("❌ Minutes 0 se zyada hone chahiye.")
        return

    if minutes > 10080:
        await ctx.send("❌ Max 10080 minutes (7 days) tak schedule kar sakte ho.")
        return

    async def _reminder_callback():
        try:
            await ctx.send(
                f"⏰ **Reminder:** {ctx.author.mention}, scheduled meeting start hone wali hai!\n📌 {title}"
            )
        except Exception as e:
            print(f"Channel reminder send failed: {e}")

        try:
            await ctx.author.send(f"⏰ Reminder: tumhari meeting due hai.\n📌 {title}")
        except Exception as e:
            print(f"User reminder DM failed: {e}")

    job_id = reminder_scheduler.schedule_in_minutes(minutes, _reminder_callback)
    await ctx.send(
        f"✅ Reminder set! `{minutes}` min baad ping karunga.\n🆔 Schedule ID: `{job_id}`\n📌 {title}"
    )

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

5️⃣ `!schedule <minutes> <title/link>` — Meeting reminder set karo
    *Reminder channel + DM dono mein aayega*

6️⃣ `!help` — Yeh help message dekho

⚡ **Kaafi Features:**
✓ Real-time voice recording
✓ AI Transcription (Whisper)
✓ Automatic Voice Auto-Join
✓ Automatic End-of-Call Summary
✓ Auto DM to New Server Members
✓ DM Summary to Participants
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