import asyncio
from playwright.async_api import async_playwright


async def join_google_meet(link: str, bot_name: str = "Meeting Bot",
                            bot_email: str = "", bot_password: str = ""):
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

        # STEP 1 — Pehle Google login karo
        if bot_email and bot_password:
            print(f"Logging in as: {bot_email}")
            try:
                await page.goto('https://accounts.google.com/signin/v2/identifier')
                await page.wait_for_timeout(3000)
                await page.screenshot(path="debug_step1.png")
                print("Step 1 screenshot saved!")

                # Email daalo
                email_input = await page.wait_for_selector('input[type="email"]', timeout=10000)
                await email_input.fill(bot_email)
                await page.wait_for_timeout(1000)
                
                # Next click karo
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(3000)
                await page.screenshot(path="debug_step2.png")
                print("Step 2 screenshot saved!")

                # Password daalo
                password_input = await page.wait_for_selector('input[type="password"]', timeout=10000)
                await password_input.fill(bot_password)
                await page.wait_for_timeout(1000)
                
                # Login karo
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(5000)
                await page.screenshot(path="debug_step3.png")
                print("Step 3 screenshot saved — login done!")

            except Exception as e:
                print(f"Login error: {e}")
                await page.screenshot(path="debug_login_error.png")

        # STEP 2 — Meeting join karo
        print("Opening meeting link...")
        await page.goto(link)
        await page.wait_for_timeout(5000)
        await page.screenshot(path="debug_meet.png")
        print("Meeting screenshot saved!")

        # Mic off
        try:
            await page.click('[data-is-muted="false"][data-tooltip*="microphone"]', timeout=3000)
        except:
            pass

        # Camera off
        try:
            await page.click('[data-is-muted="false"][data-tooltip*="camera"]', timeout=3000)
        except:
            pass

        # Join button
        try:
            await page.click('text=Join now', timeout=5000)
            print(f"✅ Joined as '{bot_name}'!")
        except:
            try:
                await page.click('text=Ask to join', timeout=5000)
                print(f"✅ Asked to join as '{bot_name}'!")
            except:
                print("Join button not found")

        # Audio record
        print("Recording for 60 minutes...")
        from bot.audio_capture import record_audio
        from bot.transcriber import transcribe_audio
        from agent.summarizer import summarize_transcript

        recording_task = asyncio.create_task(record_audio(3600))
        await page.wait_for_timeout(60 * 60 * 1000)

        audio_file = await recording_task
        transcript = transcribe_audio(audio_file)

        if transcript:
            result = summarize_transcript(transcript)
            print("Summary ready!")
            return result['summary']

        await browser.close()
        print("Meeting ended!")


async def test_join():
    link = input("Google Meet link: ")
    name = input("Your name: ")
    email = input("Gmail: ")
    password = input("Password: ")
    await join_google_meet(link, name, email, password)


if __name__ == "__main__":
    asyncio.run(test_join())