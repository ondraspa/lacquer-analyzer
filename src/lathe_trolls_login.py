"""Interactive login helper for LatheTrolls — opens Chromium via Playwright.

Usage:
    python -m src.lathe_trolls_login
    # or from code:
    from src.lathe_trolls_login import run_login_setup
    run_login_setup(auth_path="config/auth_state.json")
"""

import sys
from pathlib import Path


def run_login_setup(auth_path: str = "config/auth_state.json") -> bool:
    """Open a Chromium window, let the user log into lathetrolls.com,
    and save the authenticated storage state to *auth_path*.

    Returns:
        True if auth state was saved, False on error or if cancelled.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[-] playwright is not installed. Run:   pip install playwright && playwright install chromium")
        return False

    auth_file = Path(auth_path)
    auth_file.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--start-maximized"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            no_viewport=True,
        )
        page = context.new_page()

        print("[*] Opening LatheTrolls login page...")
        page.goto("https://www.lathetrolls.com/ucp.php?mode=login")

        print("\n" + "=" * 60)
        print("CRITICAL STEPS REQUIRED:")
        print("1. Type your username and password.")
        print("2. You MUST check the box that says:")
        print("   'Log me on automatically each visit' (or 'Remember me')")
        print("3. Click Login.")
        print("4. Wait until the main forum dashboard completely loads.")
        print("5. Then come back to this terminal.")
        print("=" * 60)

        input("\nPress ENTER in this terminal ONLY AFTER you are fully logged in... ")

        context.storage_state(path=str(auth_file))
        print(f"[+] Fresh session saved to '{auth_file}'")

        # Verify the saved state contains valid cookies
        import json
        with open(auth_file) as f:
            state = json.load(f)
        cookie_count = len(state.get("cookies", []))
        print(f"[+] Contains {cookie_count} cookies")
        if cookie_count == 0:
            print("[-] WARNING: No cookies saved! Login may have failed.")
            return False

        browser.close()
        return True


def main():
    auth_path = "config/auth_state.json"
    if len(sys.argv) > 1:
        auth_path = sys.argv[1]
    success = run_login_setup(auth_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
