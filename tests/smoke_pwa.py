from __future__ import annotations
import json,os,re
from playwright.sync_api import sync_playwright

URL=os.environ.get('SMOKE_URL','http://127.0.0.1:8000/')

def wait_loaded(page):
    page.wait_for_function("document.querySelector('#dataState') && document.querySelector('#dataState').textContent.includes('BONUS+')",timeout=20000)
    text=page.locator('#dataState').inner_text();m=re.search(r'BONUS\+\s+(\d+)日',text)
    assert m and int(m.group(1))>0,text;assert 'BONUS+データ取得失敗' not in text,text

def check_sunday_start(page):
    page.evaluate("()=>{view=new Date(2026,7,1);selectedIso='';render()}")
    assert page.locator('#calendar .dow').all_inner_texts()==['日','月','火','水','木','金','土']
    aug_col=page.evaluate("()=>{const cal=document.querySelector('#calendar'),b=[...cal.querySelectorAll('button.day')].find(x=>x.getAttribute('aria-label')==='8月1日');return ([...cal.children].indexOf(b)-7)%7}")
    assert aug_col==6,aug_col
    page.evaluate("()=>{view=new Date(2026,8,1);selectedIso='';render()}")
    sep_col=page.evaluate("()=>{const cal=document.querySelector('#calendar'),b=[...cal.querySelectorAll('button.day')].find(x=>x.getAttribute('aria-label')==='9月1日');return ([...cal.children].indexOf(b)-7)%7}")
    assert sep_col==2,sep_col
    page.evaluate("()=>{view=new Date(2026,7,1);selectedIso='';render()}")

def target_offer(page):
    return page.evaluate(r'''() => {const cat=bonus.store_catalog||[];let d=(bonus.days||[]).find(x=>x.date==='2026-08-17'&&(x.offers||[]).some(o=>(cat[o[0]]||[])[1]==='tplink'&&Number(o[1])===5));if(!d)d=(bonus.days||[]).find(x=>x.status==='ok'&&Array.isArray(x.offers)&&x.offers.length);if(!d)return null;let o=d.offers.find(o=>(cat[o[0]]||[])[1]==='tplink')||d.offers[0],c=cat[o[0]]||[];return {date:d.date,name:c[0]||'',slug:c[1]||'',rate:Number(o[1])};}''')

def check_offer(page,target):
    assert target and target['name'] and target['date'] and target['rate']>=0,target;y,m,d=map(int,target['date'].split('-'))
    page.evaluate("([y,m,d])=>{view=new Date(y,m-1,1);selectedIso=`${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`;render()}",[y,m,d]);assert page.locator('#monthTitle').inner_text()==f'{y}年 {m}月'
    page.locator('#shop').fill(target['name']);page.locator('#searchBtn').click();page.get_by_role('button',name=f'{m}月{d}日').click();detail=page.locator('#detail').inner_text();assert f"BONUS+ +{target['rate']:g}%" in detail and target['name'] in detail,detail
    if target['slug']:
        page.locator('#shop').fill(f"https://store.shopping.yahoo.co.jp/{target['slug']}/");page.locator('#searchBtn').click();page.get_by_role('button',name=f'{m}月{d}日').click();assert f"BONUS+ +{target['rate']:g}%" in page.locator('#detail').inner_text()

def check_mobile_bonus_badge(page):
    page.wait_for_function("document.querySelector('#calendar .bonusRateBadge .bonusRate') !== null")
    badge=page.locator('#calendar .bonusRateBadge .bonusRate').first
    font=float(badge.evaluate("e=>parseFloat(getComputedStyle(e).fontSize)"))
    assert font>=14,font
    assert '%' in badge.inner_text()
    assert page.locator('#calendar .bonusRateBadge .bonusPrefix').first.inner_text()=='BONUS+'

def check_known_alias(page,query,slug):
    target=page.evaluate("([query,slug])=>{const c=OtokubiCore.searchCatalog(bonus.store_catalog,query,8).find(x=>x.slug===slug);if(!c)return null;for(const d of bonus.days||[]){const o=(d.offers||[]).find(x=>x[0]===c.id);if(o)return{name:c.name,slug:c.slug,date:d.date,rate:Number(o[1]),score:c.score}}return null}",[query,slug])
    assert target,target;assert target['score']>=98,target;y,m,d=map(int,target['date'].split('-'))
    page.evaluate("([y,m])=>{view=new Date(y,m-1,1);selectedIso=''}",[y,m]);page.locator('#shop').fill(query);page.locator('#searchBtn').click()
    assert page.locator('#shop').input_value()==target['name'];suggest=page.locator('#shopSuggestions').inner_text();assert target['name'] in suggest,suggest
    page.get_by_role('button',name=f'{m}月{d}日').click();detail=page.locator('#detail').inner_text();assert target['name'] in detail and f"BONUS+ +{target['rate']:g}%" in detail,detail

def check_campaign_metadata(page):
    page.locator('#shop').fill('');page.evaluate(r'''() => {campaigns={campaigns:[{title:'Brand Week',dates:['2026-08-24'],rate:null,rate_label:'最大25%',is_total:true,is_max:true,entry_required:true,target_store_limited:true,eligibility_rule:'campaign_target_store',rankable:true,conditions:['要エントリー 対象ストア限定 付与上限あり']}]};view=new Date(2026,7,1);selectedIso='2026-08-24';render();}''')
    cell=page.get_by_role('button',name='8月24日');assert 'Brand Week 最大25%' in cell.inner_text(),cell.inner_text();cell.click();detail=page.locator('#detail').inner_text();assert 'Brand Week 最大25%' in detail and '要エントリー 対象ストア限定 付与上限あり' in detail and '単純加算しません' in detail,detail

def check_top3_ranking(page):
    page.locator('#purchaseAmount').fill('')
    page.evaluate(r'''() => {
      bonus={store_catalog:[['テストショップ','test-shop']],days:[
        {date:'2026-08-01',status:'ok',offers:[[0,5]]},
        {date:'2026-08-02',status:'ok',offers:[[0,10]]},
        {date:'2026-08-03',status:'ok',offers:[]},
        {date:'2026-08-04',status:'ok',offers:[[0,7]]},
        {date:'2026-08-05',status:'ok',offers:[[0,5]]},
        {date:'2026-08-06',status:'ok',offers:[[0,5]]}
      ]};
      campaigns={campaigns:[
        {title:'最大表示',dates:['2026-08-01'],rate:20,is_total:true,target_store_limited:false},
        {title:'対象ストア限定',dates:['2026-08-04'],rate:10,is_total:false,target_store_limited:true,eligibility_rule:'campaign_target_store'}
      ]};
      activeShopQuery='https://store.shopping.yahoo.co.jp/test-shop/';document.querySelector('#shop').value='テストショップ';view=new Date(2026,7,1);selectedIso='';render();
    }''')
    page.wait_for_function("document.querySelectorAll('#top3Strip .top3Item').length===3")
    absent=page.get_by_role('button',name='8月3日');assert 'BONUS+' not in absent.inner_text(),absent.inner_text();absent.click();detail=page.locator('#detail').inner_text();assert 'BONUS+' not in detail,detail;assert '確認済み追加特典の順位なし（基本還元は対象）' in detail and '7%' in detail,detail
    texts=page.locator('#top3Strip .top3Item').all_inner_texts();assert all('3日' not in t for t in texts),texts
    assert '1位' in texts[0] and '2日' in texts[0] and '合計17%' in texts[0],texts
    assert '2位' in texts[1] and '5日' in texts[1] and '合計16%' in texts[1],texts
    assert '3位' in texts[2] and '1日' in texts[2] and '合計15%' in texts[2],texts
    page.locator('#purchaseAmount').fill('100000')
    page.wait_for_function("document.querySelector('#top3Strip .top3Item strong')?.textContent.includes('15,544pt')")
    texts=page.locator('#top3Strip .top3Item').all_inner_texts();assert '1位' in texts[0] and '2日' in texts[0] and '15,544pt' in texts[0],texts
    assert '2位' in texts[1] and '1日' in texts[1] and '12,999pt' in texts[1],texts
    assert '3位' in texts[2] and '4日' in texts[2] and '12,817pt' in texts[2],texts
    assert page.locator('#calendar .day.rank1').get_attribute('aria-label')=='8月2日';assert page.locator('#calendar .day.rank2').get_attribute('aria-label')=='8月1日';assert page.locator('#calendar .day.rank3').get_attribute('aria-label')=='8月4日'
    page.locator('#top3Strip .top3Item').first.click();detail=page.locator('#detail').inner_text();assert '今月のお得度 1位' in detail and '予定購入 100,000円' in detail and '約15,544pt' in detail,detail;assert '基本7% 約6,454pt' in detail and 'エントリー済' in detail and 'クーポンは使用しない' in detail,detail
    page.get_by_role('button',name='8月5日').click();detail=page.locator('#detail').inner_text();assert '今月のお得度 4位' in detail and '約11,999pt' in detail,detail;assert 'BONUS+ 約4,545pt' in detail and 'キャンペーン 約1,000pt' in detail and '基本7% 約6,454pt' in detail,detail
    page.get_by_role('button',name='8月3日').click();detail=page.locator('#detail').inner_text();assert '確認済み追加特典の順位なし（基本還元は対象）' in detail and '約6,454pt' in detail,detail;assert 'BONUS+' not in detail,detail
    page.locator('#purchaseAmount').fill('35980');page.get_by_role('button',name='8月6日').click();detail=page.locator('#detail').inner_text();assert '概算獲得 約3,955pt' in detail,detail;assert '基本7% 約2,320pt' in detail and 'BONUS+ 約1,635pt' in detail,detail;assert 'ストア 327pt' in detail and 'LINE連携 981pt' in detail and 'LYP 654pt' in detail and 'PayPayクレジット 358pt' in detail,detail

def check_unknown_bonus_cap_fail_closed(page):
    page.locator('#purchaseAmount').fill('100000')
    page.evaluate(r'''() => {
      bonus={store_catalog:[['未来テスト店','future-shop']],days:[{date:'2026-09-02',status:'ok',offers:[[0,9]]}]};
      campaigns={campaigns:[]};activeShopQuery='https://store.shopping.yahoo.co.jp/future-shop/';document.querySelector('#shop').value='未来テスト店';view=new Date(2026,8,1);selectedIso='';render();
    }''')
    page.wait_for_function("document.querySelector('#top3Strip .top3Item small')?.textContent.includes('上限未確認')")
    top=page.locator('#top3Strip .top3Item').first.inner_text();assert '合計16%' in top and '上限未確認のため率で順位' in top,top
    page.get_by_role('button',name='9月2日').click();detail=page.locator('#detail').inner_text();assert '概算ポイントには未加算' in detail and 'ポイント額ではなく還元率で比較' in detail,detail
    assert 'BONUS+ 約' not in detail,detail

def check_auto_campaign_eligibility(page):
    page.locator('#purchaseAmount').fill('')
    page.evaluate(r'''() => {
      bonus={store_catalog:[['対象ショップ','target-shop']],days:[
        {date:'2026-08-18',status:'ok',offers:[[0,5]]},
        {date:'2026-08-19',status:'ok',offers:[]}
      ]};
      campaigns={campaigns:[
        {title:'ボーナスストアPlusでさらに+2%',dates:['2026-08-18','2026-08-19'],rate:2,rate_label:'+2%',is_total:false,is_max:false,informational:false,rankable:true,target_store_limited:true,eligibility_rule:'bonus_plus_member',conditions:['注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定']},
        {title:'ボーナスストアPlus 優良ストアでさらに+3%',dates:['2026-08-18'],rate:3,rate_label:'+3%',is_total:false,is_max:false,informational:false,rankable:true,target_store_limited:true,eligibility_rule:'preferred_bonus_store',conditions:['注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定']},
        {title:'ボーナスストアPlusくじ',dates:['2026-08-18','2026-08-19'],rate:null,rate_label:'最大1万円相当',is_total:false,is_max:true,informational:true,rankable:false,target_store_limited:true,eligibility_rule:'campaign_target_store',conditions:['対象ストア限定 1注文1,000円～69,999円']}
      ]};
      activeShopQuery='https://store.shopping.yahoo.co.jp/target-shop/';document.querySelector('#shop').value='対象ショップ';view=new Date(2026,7,1);selectedIso='';render();
    }''')
    page.get_by_role('button',name='8月18日').click();detail=page.locator('#detail').inner_text();assert 'BONUS+ +5%' in detail,detail;assert '最大1万円相当' in detail,detail;assert '表示上の合計還元率 14%' in detail and '確認済み企画 +2%' in detail,detail;assert '17%' not in detail,detail
    page.get_by_role('button',name='8月19日').click();detail=page.locator('#detail').inner_text();assert '最大1万円相当' in detail,detail;assert '表示上の合計還元率 7%' in detail,detail;assert '確認済み企画 +2%' not in detail,detail;assert 'BONUS+ +5%' not in detail,detail

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        iphone=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True,locale='ja-JP',timezone_id='Asia/Tokyo',accept_downloads=True)
        page=iphone.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);assert page.locator('#purchaseAmount').is_visible();assert 'v0.9.3' in page.locator('.versionBadge').inner_text();assumption=page.locator('#calcAssumption').inner_text();assert '基本7%' in assumption and 'LINE連携3%' in assumption and 'LYPプレミアム2%' in assumption and 'PayPayクレジット1%' in assumption;assert 'エントリー済' in assumption and 'クーポンは使用しない' in assumption;assert page.evaluate('OTOKUBI_CALC_ASSUMPTIONS.entryCompleted && OTOKUBI_CALC_ASSUMPTIONS.ignoreCoupons') is True;check_sunday_start(page);target=target_offer(page);check_offer(page,target);check_mobile_bonus_badge(page);check_known_alias(page,'ジョーシン','joshin');check_known_alias(page,'ヤマダ電機','yamada-denki')
        page.wait_for_function("document.querySelector('#top3Strip') !== null");assert page.locator('#top3Strip').is_visible()
        page.evaluate("navigator.serviceWorker && navigator.serviceWorker.ready");page.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller !== null",timeout=10000);page.evaluate("load()");wait_loaded(page);assert page.locator('#calendar .dow').first.inner_text()=='日'
        cache_keys=page.evaluate("async()=> (await (await caches.open('otokubi-data-v1')).keys()).map(r=>r.url)")
        assert len(cache_keys)==3,cache_keys;assert all('?v=' not in u for u in cache_keys),cache_keys;assert {u.rsplit('/',1)[-1] for u in cache_keys}=={'bonus.json','campaigns.json','status.json'},cache_keys
        iphone.set_offline(True);page.reload(wait_until='domcontentloaded');wait_loaded(page);assert page.locator('#calendar .dow').first.inner_text()=='日';check_known_alias(page,'ジョーシン','joshin');assert page.locator('#top3Strip').is_visible();iphone.set_offline(False)
        with page.expect_download(timeout=10000) as dl:page.locator('#pngBtn').click()
        assert dl.value.suggested_filename.endswith('.png');iphone.close()

        desktop=browser.new_context(viewport={'width':1440,'height':900},locale='ja-JP',timezone_id='Asia/Tokyo')
        page=desktop.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);check_sunday_start(page);check_offer(page,target_offer(page));check_known_alias(page,'Joshin','joshin');check_known_alias(page,'ヤマダ電機','yamada-denki');check_campaign_metadata(page);check_top3_ranking(page);check_unknown_bonus_cap_fail_closed(page);check_auto_campaign_eligibility(page);cols=page.locator('.workspace').evaluate("e=>getComputedStyle(e).gridTemplateColumns");widths=[float(x) for x in re.findall(r'([0-9.]+)px',cols)];assert len(widths)==2 and widths[0]>widths[1]>=350,cols;desktop.close()

        statusctx=browser.new_context(viewport={'width':390,'height':844},locale='ja-JP',timezone_id='Asia/Tokyo',service_workers='block')
        failed={'schema':1,'version':'0.8.0','last_attempt_at':'2026-08-17T10:00:00+09:00','last_attempt_ok':False,'last_attempt_exit_code':2,'message':'最新更新失敗','issues':['Incomplete BONUS+ days: 1'],'attempt_counts':{'partial':1},'attempt_source_updated_at':'2026-08-17T10:00:00+09:00','last_good_updated_at':'2026-08-17T09:00:00+09:00'}
        statusctx.route('**/data/status.json*',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(failed,ensure_ascii=False)))
        page=statusctx.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);state=page.locator('#dataState').inner_text();assert '最新取得失敗' in state and '前回正常データを使用' in state,state;assert 'warning' in (page.locator('#dataState').get_attribute('class') or '');statusctx.close();browser.close()
    print('PWA smoke: PASS (v0.9.3 + mobile BONUS rate readability + future cap fail-closed + auto official campaigns + safe +2 eligibility + informational events + base 7% + Sunday-first + iPhone offline + Windows + PNG)')

if __name__=='__main__':main()
