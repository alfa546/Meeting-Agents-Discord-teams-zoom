import asyncio
from playwright.async_api import async_playwright

async def join_google_meet(link: str):
    """Google Meet automatically join karo"""
    print(f"Joining meeting: {link}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--use-fake-ui-for-media-stream',
                '--use-fake-device-for-media-stream',
            ]
        )
        
        context = await browser.new_context(
            permissions=['camera', 'microphone']
        )
        
        page = await context.new_page()
        
        print("Opening meeting link...")
        await page.goto(link)
        await page.wait_for_timeout(3000)
        
        # Mic aur camera off karo
        try:
            await page.click('[data-is-muted="false"][data-tooltip*="microphone"]', timeout=3000)
            print("Mic muted")
        except:
            pass
        
        try:
            await page.click('[data-is-muted="false"][data-tooltip*="camera"]', timeout=3000)
            print("Camera off")
        except:
            pass
        
        # Join button click karo
        try:
            await page.click('text=Join now', timeout=5000)
            print("Joined meeting!")
        except:
            try:
                await page.click('text=Ask to join', timeout=5000)
                print("Asked to join!")
            except:
                print("Join button not found - already in meeting?")
        
        # Audio record karo saath mein
        print("Recording for 60 minutes...")
        from bot.audio_capture import record_audio
        from bot.transcriber import transcribe_audio
        from agent.summarizer import summarize_transcript

        recording_task = asyncio.create_task(record_audio(3600))
        await page.wait_for_timeout(60 * 60 * 1000)

        audio_file = await recording_task
        print(f"Audio saved: {audio_file}")

        # Transcribe karo
        print("Transcribing...")
        transcript = transcribe_audio(audio_file)

        # Summary nikalo
        print("Summarizing...")
        result = summarize_transcript(transcript)
        print("Summary ready!")
        print(result['summary'])
        
        await browser.close()
        print("Meeting ended!")

async def test_join():
    link = input("Google Meet link paste karo: ")
    await join_google_meet(link)

if __name__ == "__main__":
    asyncio.run(test_join())