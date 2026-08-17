from __future__ import annotations
import os,re
from playwright.sync_api import sync_playwright

URL=os.environ.get('SMOKE_URL','http://127.0.0.1:8000/')

def wait_loaded(page):
    page.wait_for_function("document.querySelector('#dataState') && document.querySelector('#dataState').textContent.includes('BONUS+')",timeout=20000)
    text=page.locator('#dataState').inner_text()
    assert 'BONUS+ 47日' in text, text
    assert 'BONUS+データ取得失敗' not in text, text

def go_aug_2026(page):
    page.evaluate("view=new Date(2026,7,1);selectedIso='2026-08-17';render()")
    assert page.locator('#monthTitle').inner_text()=='2026年 8月'

def check_tplink(page):
    go_aug_2026(page)
    page.locator('#shop').fill('TP-Link公式ダイレクト')
    page.locator('#searchBtn').click()
    page.get_by_role('button',name='8月17日').click()
    detail=page.locator('#detail').inner_text()
    assert 'BONUS+ +5%' in detail, detail
    assert 'TP-Link公式ダイレクト' in detail, detail
    page.locator('#shop').fill('https://store.shopping.yahoo.co.jp/tplink/')
    page.locator('#searchBtn').click()
    page.get_by_role('button',name='8月17日').click()
    assert 'BONUS+ +5%' in page.locator('#detail').inner_text()

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])

        iphone=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True,locale='ja-JP',timezone_id='Asia/Tokyo',accept_downloads=True)
        page=iphone.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);check_tplink(page)
        page.evaluate("navigator.serviceWorker && navigator.serviceWorker.ready")
        page.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller !== null",timeout=10000)
        page.evaluate("load()") ; wait_loaded(page)
        cache_keys=page.evaluate("async()=> (await (await caches.open('otokubi-data-v1')).keys()).map(r=>r.url)")
        assert len(cache_keys)==2,cache_keys
        assert all('?v=' not in u for u in cache_keys),cache_keys
        iphone.set_offline(True);page.reload(wait_until='domcontentloaded');wait_loaded(page);check_tplink(page);iphone.set_offline(False)
        with page.expect_download(timeout=10000) as dl:
            page.locator('#pngBtn').click()
        assert dl.value.suggested_filename.endswith('.png')
        iphone.close()

        desktop=browser.new_context(viewport={'width':1440,'height':900},locale='ja-JP',timezone_id='Asia/Tokyo')
        page=desktop.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);check_tplink(page)
        cols=page.locator('.workspace').evaluate("e=>getComputedStyle(e).gridTemplateColumns")
        widths=[float(x) for x in re.findall(r'([0-9.]+)px',cols)]
        assert len(widths)==2 and widths[0]>widths[1]>=350,cols
        desktop.close();browser.close()
    print('PWA smoke: PASS (iPhone online/offline + bounded cache + Windows + TP-Link + PNG)')

if __name__=='__main__': main()
