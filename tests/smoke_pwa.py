from __future__ import annotations
import os,re
from playwright.sync_api import sync_playwright

URL=os.environ.get('SMOKE_URL','http://127.0.0.1:8000/')

def wait_loaded(page):
    page.wait_for_function("document.querySelector('#dataState') && document.querySelector('#dataState').textContent.includes('BONUS+')",timeout=20000)
    text=page.locator('#dataState').inner_text()
    m=re.search(r'BONUS\+\s+(\d+)日',text)
    assert m and int(m.group(1))>0,text
    assert 'BONUS+データ取得失敗' not in text,text

def target_offer(page):
    return page.evaluate(r'''() => {
      const cat=bonus.store_catalog||[];
      let d=(bonus.days||[]).find(x=>x.date==='2026-08-17'&&(x.offers||[]).some(o=>(cat[o[0]]||[])[1]==='tplink'&&Number(o[1])===5));
      if(!d)d=(bonus.days||[]).find(x=>x.status==='ok'&&Array.isArray(x.offers)&&x.offers.length);
      if(!d)return null;
      let o=d.offers.find(o=>(cat[o[0]]||[])[1]==='tplink')||d.offers[0],c=cat[o[0]]||[];
      return {date:d.date,name:c[0]||'',slug:c[1]||'',rate:Number(o[1])};
    }''')

def check_offer(page,target):
    assert target and target['name'] and target['date'] and target['rate']>=0,target
    y,m,d=map(int,target['date'].split('-'))
    page.evaluate("([y,m,d])=>{view=new Date(y,m-1,1);selectedIso=`${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`;render()}",[y,m,d])
    assert page.locator('#monthTitle').inner_text()==f'{y}年 {m}月'
    page.locator('#shop').fill(target['name']);page.locator('#searchBtn').click()
    page.get_by_role('button',name=f'{m}月{d}日').click()
    detail=page.locator('#detail').inner_text()
    assert f"BONUS+ +{target['rate']:g}%" in detail,detail
    assert target['name'] in detail,detail
    if target['slug']:
        page.locator('#shop').fill(f"https://store.shopping.yahoo.co.jp/{target['slug']}/");page.locator('#searchBtn').click()
        page.get_by_role('button',name=f'{m}月{d}日').click()
        assert f"BONUS+ +{target['rate']:g}%" in page.locator('#detail').inner_text()

def check_campaign_metadata(page):
    page.locator('#shop').fill('')
    page.evaluate(r'''() => {
      campaigns={campaigns:[{title:'Brand Week',dates:['2026-08-24'],rate:null,rate_label:'最大25%',is_total:true,is_max:true,entry_required:true,target_store_limited:true,conditions:['要エントリー 対象ストア限定 付与上限あり']}]};
      view=new Date(2026,7,1);selectedIso='2026-08-24';render();
    }''')
    cell=page.get_by_role('button',name='8月24日')
    assert 'Brand Week 最大25%' in cell.inner_text(),cell.inner_text()
    cell.click();detail=page.locator('#detail').inner_text()
    assert 'Brand Week 最大25%' in detail,detail
    assert '要エントリー 対象ストア限定 付与上限あり' in detail,detail
    assert '単純加算しません' in detail,detail

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        iphone=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True,locale='ja-JP',timezone_id='Asia/Tokyo',accept_downloads=True)
        page=iphone.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);target=target_offer(page);check_offer(page,target)
        page.evaluate("navigator.serviceWorker && navigator.serviceWorker.ready")
        page.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller !== null",timeout=10000)
        page.evaluate("load()") ; wait_loaded(page)
        cache_keys=page.evaluate("async()=> (await (await caches.open('otokubi-data-v1')).keys()).map(r=>r.url)")
        assert len(cache_keys)==2,cache_keys
        assert all('?v=' not in u for u in cache_keys),cache_keys
        iphone.set_offline(True);page.reload(wait_until='domcontentloaded');wait_loaded(page);check_offer(page,target);iphone.set_offline(False)
        with page.expect_download(timeout=10000) as dl: page.locator('#pngBtn').click()
        assert dl.value.suggested_filename.endswith('.png')
        iphone.close()

        desktop=browser.new_context(viewport={'width':1440,'height':900},locale='ja-JP',timezone_id='Asia/Tokyo')
        page=desktop.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);check_offer(page,target_offer(page));check_campaign_metadata(page)
        cols=page.locator('.workspace').evaluate("e=>getComputedStyle(e).gridTemplateColumns")
        widths=[float(x) for x in re.findall(r'([0-9.]+)px',cols)]
        assert len(widths)==2 and widths[0]>widths[1]>=350,cols
        desktop.close();browser.close()
    print('PWA smoke: PASS (store/date + campaign labels + iPhone offline + bounded cache + Windows + PNG)')

if __name__=='__main__': main()
