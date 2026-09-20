#!/usr/bin/env python3
"""Génère les PNG App Store (1290×2796) depuis les mockups HTML locaux."""

from __future__ import annotations

import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML_DIR = ROOT / "html"
OUT_67 = ROOT / "iphone-6.7"
OUT_65 = ROOT / "iphone-6.5"

# Ordre App Store Connect (Lots A + B + C)
FILES = [
    ("01-onboarding-mission.png", "01-onboarding-mission.html"),
    ("02-onboarding-parcours.png", "02-onboarding-parcours.html"),
    ("03-onboarding-charte.png", "03-onboarding-charte.html"),
    ("04-parcours-curated.png", "04-parcours-curated.html"),
    ("05-messages-guides.png", "05-messages-guides.html"),
    ("06-coaching.png", "06-coaching.html"),
    ("07-objectif-profil.png", "07-objectif-profil.html"),
    ("08-interets.png", "08-interets.html"),
]

VIEWPORT = {"width": 390, "height": 844}
TARGET_67 = (1290, 2796)
TARGET_65 = (1242, 2688)


async def main() -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright requis : pip install playwright && playwright install chromium"
        ) from exc

    OUT_67.mkdir(parents=True, exist_ok=True)
    OUT_65.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=TARGET_67[0] / VIEWPORT["width"],
        )
        page = await context.new_page()

        from PIL import Image

        for out_name, html_name in FILES:
            html_path = HTML_DIR / html_name
            if not html_path.exists():
                print(f"SKIP missing {html_name}")
                continue
            url = html_path.as_uri()
            await page.goto(url, wait_until="networkidle")
            tmp = OUT_67 / f"_tmp_{out_name}"
            await page.screenshot(path=str(tmp), type="png")
            img = Image.open(tmp).convert("RGB")
            img = img.resize(TARGET_67, Image.Resampling.LANCZOS)
            out_67 = OUT_67 / out_name
            img.save(out_67, optimize=True)
            tmp.unlink(missing_ok=True)
            print(f"OK {out_67} ({out_67.stat().st_size // 1024} KB)")

            img_65 = img.resize(TARGET_65, Image.Resampling.LANCZOS)
            out_65 = OUT_65 / out_name
            img_65.save(out_65, optimize=True)
            print(f"OK {out_65}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
