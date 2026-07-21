"""Configuración manual de cookies para SpecialChem.

SpecialChem (coatings.specialchem.com) está protegido por Cloudflare Turnstile.
Este script abre un navegador real para que te loguees manualmente,
luego guarda las cookies para que el scraper las reutilice.

Uso:
  python imports/login_setup_specialchem.py

El script abre Chromium, navega a SpecialChem, y espera hasta 3 minutos
a que resuelvas el desafío de Cloudflare y/o te loguees.
El navegador se cierra SOLO cuando presionas Enter.
"""

import asyncio
import json
import os
import sys
import time

COOKIE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "specialchem_auth.json"
)
AUTH_STATE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "specialchem_auth_state.json"
)


async def wait_for_page_load(page, timeout=180):
    """Espera hasta que la página supere el challenge de Cloudflare."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            title = await page.title()
            text = await page.inner_text("body") if await page.query_selector("body") else ""

            if "Just a moment" not in text and "security" not in text.lower() and text.strip():
                return True

            await asyncio.sleep(2)
        except Exception:
            await asyncio.sleep(2)
    return False


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright no está instalado.")
        print("Instálalo con: pip install playwright && playwright install chromium")
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        # ── Si ya hay un auth state guardado, restaurarlo ──
        if os.path.exists(AUTH_STATE_PATH):
            try:
                with open(AUTH_STATE_PATH) as f:
                    state = json.load(f)
                await context.add_cookies(state.get("cookies", []))
                print("  ✓ Cookies previas restauradas desde", AUTH_STATE_PATH)
            except Exception:
                pass

        page = await context.new_page()

        print("=" * 60)
        print("  CONFIGURACIÓN DE COOKIES — SpecialChem")
        print("=" * 60)
        print()
        print("  Se abrirá una ventana del navegador.")
        print()
        print("  PASOS:")
        print("  1. Espera a que cargue coatings.specialchem.com")
        print("  2. Si ves el challenge de Cloudflare, resuélvelo (check)")
        print("  3. Si tienes cuenta, navega al LOGIN e inicia sesión")
        print("     (botón 'Sign In' arriba a la derecha)")
        print("  4. Las cookies se guardarán automáticamente")
        print()
        print("  ⚠️  NO CIERRES el navegador hasta que veas el mensaje de éxito")
        print("  ⚠️  El navegador se cerrará automáticamente al presionar Enter")
        print()

        await page.goto(
            "https://coatings.specialchem.com/",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print("  ⏳ Esperando que resuelvas el desafío de Cloudflare...")
        success = await wait_for_page_load(page, timeout=180)

        if success:
            print("  ✓ Página cargada — desafío superado (o no requerido)")
        else:
            print("  ⚠️  No se pudo detectar automáticamente. Continuando...")

        print()
        print("  ────────────────────────────────────────────")
        print("  📌 Ahora tienes el navegador ABIERTO.")
        print("  📌 Si tienes cuenta: inicia sesión ahora.")
        print("  📌 Presiona ENTER acá cuando estés listo")
        print("     (las cookies se guardarán en ese momento)")
        print("  ────────────────────────────────────────────")
        print()

        # ── Esperar a que el usuario presione Enter ──
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sys.stdin.readline)

        # ── Guardar cookies ──
        cookies = await context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}
        os.makedirs(os.path.dirname(COOKIE_PATH), exist_ok=True)

        with open(COOKIE_PATH, "w") as f:
            json.dump(cookie_dict, f, indent=2)
        print(f"\n  ✓ Cookies guardadas ({len(cookie_dict)} cookies) en {COOKIE_PATH}")

        state = await context.storage_state()
        with open(AUTH_STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
        print(f"  ✓ Auth state guardado en {AUTH_STATE_PATH}")
        print()
        print("  Listo. El scraper usará estas cookies automáticamente.")
        print("  Cerrando navegador...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
