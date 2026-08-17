from __future__ import annotations
import asyncio, json
from playwright.async_api import async_playwright
import scrape as legacy
import scrape_v061 as v61

VERSION='0.6.2'

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        ctx=await browser.new_context(locale='ja-JP',timezone_id='Asia/Tokyo',user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139 Safari/537.36')
        page=await ctx.new_page()
        bonus=await v61.collect_bonus(page)
        bonus['version']=VERSION
        guide=await legacy.collect_guide(browser)
        guide['version']=VERSION
        await browser.close()
    validation=v61.validate(bonus,guide)
    bonus['validation']=validation; guide['validation']=validation
    (v61.DATA/'bonus.json').write_text(json.dumps(bonus,ensure_ascii=False,indent=2),encoding='utf-8')
    (v61.DATA/'campaigns.json').write_text(json.dumps(guide,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(validation,ensure_ascii=False))
    if not validation['ok']: raise SystemExit(2)

if __name__=='__main__': asyncio.run(main())
