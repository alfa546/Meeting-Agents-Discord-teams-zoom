import asyncio
from playwright.async_api import async_playwright


async def join_google_meet(link: str, bot_name: str = "Meeting Bot"):
    """Google Meet automatically join karo"""
    print(f"Joining meeting: {link}")
    print(f"Bot name: {bot_name}")

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

        # Screenshot lo — dekho bot ko kya dikh raha hai
        await page.screenshot(path="debug_meet.png")
        print("Screenshot saved — debug_meet.png")

        # Bot ka naam set karo
        try:
            # Multiple selectors try karo
            for selector in [
                'input[placeholder="Your name"]',
                'input[aria-label="Your name"]',
                'input[data-placeholder="Your name"]',
                '[jsname="YPqjbf"]',
                'input[type="text"]'
            ]:
                try:
                    name_input = await page.wait_for_selector(selector, timeout=2000)
                    await name_input.fill(bot_name)
                    print(f"Name set: {bot_name}")
                    break
                except:
                    continue
        except:
            print("Name field not found - joining as guest")

        # Mic off karo
        try:
            await page.click('[data-is-muted="false"][data-tooltip*="microphone"]', timeout=3000)
            print("Mic muted")
        except:
            pass

        # Camera off karo
        try:
            await page.click('[data-is-muted="false"][data-tooltip*="camera"]', timeout=3000)
            print("Camera off")
        except:
            pass

        # Join button click karo
        try:
            await page.click('text=Join now', timeout=5000)
            print(f"'{bot_name}' joined meeting!")
        except:
            try:
                await page.click('text=Ask to join', timeout=5000)
                print(f"'{bot_name}' asked to join!")
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
    name = input("Bot ka naam: ")
    await join_google_meet(link, name)


if __name__ == "__main__":
    asyncio.run(test_join())