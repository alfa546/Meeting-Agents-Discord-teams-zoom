import asyncio
import subprocess
import os
from datetime import datetime

async def record_audio(duration_seconds: int = 3600, output_dir: str = "recordings") -> str:
    """Meeting ka audio record karo"""
    
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/meeting_{timestamp}.wav"
    
    print(f"Recording audio: {output_file}")
    
    # ffmpeg se system audio capture karo
    cmd = [
        'ffmpeg',
        '-f', 'pulse',
        '-i', 'default',
        '-t', str(duration_seconds),
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        output_file,
        '-y'
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    
    await process.wait()
    print(f"Recording saved: {output_file}")
    return output_file