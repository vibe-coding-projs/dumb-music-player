"""
Demo script: Full flow of adding a song to the music player.
Run with: python tests/demo_add_song.py
"""
from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://127.0.0.1:8080"


def demo_add_song():
    with sync_playwright() as p:
        # Launch browser with slow motion for visibility
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("\n" + "=" * 60)
        print("DEMO: Adding a song to the music player")
        print("=" * 60)

        # Step 1: Visit homepage
        print("\n[Step 1] Visiting homepage...")
        page.goto(BASE_URL)
        time.sleep(1)

        # Step 2: Go to admin login
        print("[Step 2] Navigating to admin login...")
        page.goto(f"{BASE_URL}/admin")
        time.sleep(1)

        # Step 3: Login with password
        print("[Step 3] Logging in as admin...")
        page.fill("input[type='password']", "changeme")
        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_url("**/admin/dashboard")
        print("         ✓ Login successful!")
        time.sleep(1)

        # Step 4: Go to add song page
        print("[Step 4] Going to 'Add Song' page...")
        page.goto(f"{BASE_URL}/admin/add-song")
        time.sleep(1)

        # Step 5: Search for a song
        search_query = "happy birthday piano"
        print(f"[Step 5] Searching for: '{search_query}'...")
        page.fill("input[name='search_query']", search_query)
        page.click("button[type='submit'], input[type='submit']")

        # Wait for search results
        print("         Waiting for YouTube search results...")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Step 6: Check if we got results
        print("[Step 6] Checking search results...")

        # Look for result cards/items
        results = page.locator("form[action*='download-song'], .result, .video-result, [class*='result']")
        result_count = results.count()

        if result_count > 0:
            print(f"         ✓ Found {result_count} result(s)!")
            time.sleep(1)

            # Step 7: Select the first radio button
            print("[Step 7] Selecting first video result...")
            first_radio = page.locator("input[name='selected_video']").first
            first_radio.click()
            time.sleep(0.5)

            # Get the title from data attribute
            title = first_radio.get_attribute("data-title")
            if title:
                print(f"         Selected: {title}")

            # Step 8: Click download button
            print("[Step 8] Clicking download button...")
            download_btn = page.locator("button#downloadButton, button[type='submit']").first

            if download_btn.is_visible():
                print("         Downloading from YouTube (this may take 1-2 minutes)...")
                download_btn.click()

                # Wait for redirect to dashboard (longer timeout for download)
                try:
                    page.wait_for_url("**/admin/dashboard", timeout=180000)
                    print("         ✓ Song downloaded and added successfully!")
                except Exception as e:
                    print(f"         ⚠ Download may have failed: {e}")
                    # Check current URL
                    print(f"         Current URL: {page.url}")
            else:
                print("         ⚠ Download button not found")
        else:
            print("         ⚠ No results found (YouTube search may have failed)")

        # Step 9: View the dashboard with the new song
        print("[Step 9] Viewing dashboard with songs...")
        page.goto(f"{BASE_URL}/admin/dashboard")
        time.sleep(2)

        # Step 10: Visit public homepage to see the song
        print("[Step 10] Viewing public homepage...")
        page.goto(BASE_URL)
        time.sleep(2)

        print("\n" + "=" * 60)
        print("DEMO COMPLETE!")
        print("=" * 60)
        print("\nBrowser will close in 5 seconds...")
        time.sleep(5)

        browser.close()


if __name__ == "__main__":
    demo_add_song()
