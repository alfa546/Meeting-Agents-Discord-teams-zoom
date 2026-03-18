import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from agent.summarizer import summarize_transcript

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")

@bot.command(name="meeting")
async def meeting(ctx, link: str = None):
    """!meeting [link] — Meeting join karo"""
    if not link:
        await ctx.send("❌ Link bhejo: `!meeting https://meet.google.com/xxx`")
        return
    await ctx.send(f"✅ Meeting join kar raha hun: {link}\n⏳ Recording shuru hogi...")

@bot.command(name="summary")
async def summary(ctx, *, transcript: str = None):
    """!summary [text] — Kisi bhi text ki summary nikalo"""
    if not transcript:
        await ctx.send("❌ Text bhejo: `!summary Ali ne kaha...`")
        return
    await ctx.send("⏳ Summary bana raha hun...")
    result = summarize_transcript(transcript)
    
    # Discord 2000 char limit hai
    summary_text = result["summary"]
    if len(summary_text) > 1900:
        summary_text = summary_text[:1900] + "..."
    
    await ctx.send(f"📋 **Meeting Summary:**\n\n{summary_text}")

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("🟢 Bot online hai! Meeting Agent ready.")

bot.run(TOKEN)