from __future__ import annotations

import asyncio
from pathlib import Path

SRC = Path(__file__).with_name("scrape.py")
source = SRC.read_text(encoding="utf-8")

replacements = {
    "async def wait_stable(page, ms=450):": "async def wait_stable(page, ms=250):",
    "try: await page.wait_for_load_state('networkidle', timeout=8000)": "try: await page.wait_for_load_state('networkidle', timeout=4000)",
    "events.sort(); now=datetime.now(JST).date(); lo,hi=now-timedelta(days=45),now+timedelta(days=75)": "events.sort(); now=datetime.now(JST).date(); lo,hi=now-timedelta(days=1),now+timedelta(days=45)",
    "if __name__=='__main__': asyncio.run(main())": "if __name__=='__main__': pass",
}

for old, new in replacements.items():
    if old not in source:
        raise RuntimeError(f"Expected scraper source fragment not found: {old}")
    source = source.replace(old, new, 1)

namespace = {
    "__name__": "yahoo_scraper_fast_runtime",
    "__file__": str(SRC),
}
exec(compile(source, str(SRC), "exec"), namespace)
asyncio.run(namespace["main"]())
