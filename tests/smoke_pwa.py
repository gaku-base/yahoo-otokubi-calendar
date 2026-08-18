from __future__ import annotations
import os,re
from playwright.sync_api import sync_playwright
URL=os.environ.get('SMOKE_URL','http://127.0.0.1:8000/')

def wait_loaded(page):
    page.wait_for_function("document.querySelector('#dataState') && document.querySelector('#dataState').textContent.includes('BONUS+')",timeout=20000)
    text=page.locator('#dataState').inner_text();m=re.search(r'BONUS\+\s+(\d+)日',text);assert m and int(m.group(1))>0,text

def check_sunday_start(page):
    page.evaluate("()=>{view=new Date(2026,7,1);selectedIso='';render()}");assert page.locator('#calendar .dow').all_inner_texts()==['日','月','火','水','木','金','土']

def check_alias(page,query,slug):
    target=page.evaluate("([q,s])=>{const c=OtokubiCore.searchCatalog(bonus.store_catalog,q,8).find(x=>x.slug===s);if(!c)return null;for(const d of bonus.days||[]){const o=(d.offers||[]).find(x=>x[0]===c.id);if(o)return{name:c.name,date:d.date,rate:Number(o[1])}}return null}",[query,slug]);assert target,target
    y,m,d=map(int,target['date'].split('-'));page.evaluate("([y,m])=>{view=new Date(y,m-1,1);selectedIso=''}",[y,m]);page.locator('#shop').fill(query);page.locator('#searchBtn').click();assert page.locator('#shop').input_value()==target['name'];page.get_by_role('button',name=f'{m}月{d}日').click();assert target['name'] in page.locator('#detail').inner_text()

def check_mobile_bonus_badge(page):
    page.wait_for_function("document.querySelector('#calendar .bonusRateBadge .bonusRate') !== null");badge=page.locator('#calendar .bonusRateBadge .bonusRate').first;font=float(badge.evaluate("e=>parseFloat(getComputedStyle(e).fontSize)"));assert font>=14,font

def synthetic_days():
    return ','.join([f"{{date:'2026-08-{d:02d}',status:'ok',offers:[[0,{10 if d==2 else 5}]]}}" for d in range(1,32)])

def check_daily_point_comparison(page):
    days=synthetic_days();page.evaluate(f'''() => {{
      bonus={{rate_caps:{{'5':5000,'10':10000}},store_catalog:[['テストショップ','test-shop']],days:[{days}]}};
      campaigns={{campaigns:[]}};activeShopQuery='https://store.shopping.yahoo.co.jp/test-shop/';document.querySelector('#shop').value='テストショップ';document.querySelector('#purchaseAmount').value='35980';document.querySelector('#fiveDayEligible').checked=true;document.querySelector('#yahooRank').value='unknown';view=new Date(2026,7,1);selectedIso='';render();
    }}''')
    page.wait_for_function("document.querySelector('#top3Strip .top3Item') !== null");texts=page.locator('#top3Strip .top3Item').all_inner_texts();assert '1位' in texts[0] and '2日' in texts[0] and '+1,635pt' in texts[0],texts;assert any('5日' in t and '+1,000pt' in t for t in texts),texts
    day2=page.get_by_role('button',name='8月2日');assert '+3,270pt' in day2.inner_text(),day2.inner_text();day2.click();detail=page.locator('#detail').inner_text();assert '日によって変わる特典ポイント +3,270pt' in detail,detail;assert '通常日比 +1,635pt' in detail,detail;assert '基本7%' not in detail,detail
    day1=page.get_by_role('button',name='8月1日');day1.click();detail=page.locator('#detail').inner_text();assert '通常日と同じ水準' in detail,detail

def check_unknown_day_excluded(page):
    days=synthetic_days();page.evaluate(f'''() => {{
      bonus={{rate_caps:{{'5':5000,'10':10000}},store_catalog:[['テストショップ','test-shop']],days:[{days}]}};
      campaigns={{campaigns:[{{title:'ボーナスストアPlus 優良ストアでさらに+3%',dates:['2026-08-18'],rate:3,rate_label:'+3%',is_total:false,is_max:false,informational:false,rankable:true,target_store_limited:true,eligibility_rule:'preferred_bonus_store',conditions:['注文3,000円～ 付与上限5,000円相当']}}]}};
      activeShopQuery='https://store.shopping.yahoo.co.jp/test-shop/';document.querySelector('#shop').value='テストショップ';document.querySelector('#purchaseAmount').value='35980';view=new Date(2026,7,1);selectedIso='';render();
    }}''')
    page.wait_for_function("document.querySelector('#top3Strip .top3Notice') !== null");assert '要確認日' in page.locator('#top3Strip .top3Notice').inner_text();cell=page.get_by_role('button',name='8月18日');assert '要確認' in cell.inner_text(),cell.inner_text();cell.click();detail=page.locator('#detail').inner_text();assert '日別追加ポイント 要確認' in detail and '優良ストア対象可否を自動判定できない' in detail,detail

def check_premium_sunday_and_rank(page):
    days=synthetic_days();page.evaluate(f'''() => {{
      bonus={{rate_caps:{{'5':5000,'10':10000}},store_catalog:[['テストショップ','test-shop']],days:[{days}]}};
      campaigns={{campaigns:[
        {{title:'プレミアムな日曜日',dates:['2026-08-23'],rate:5,rate_label:'+5%',is_total:false,is_max:false,informational:false,rankable:true,target_store_limited:true,eligibility_rule:'campaign_target_store',conditions:['注文5,000円～ 付与上限2,000円相当']}},
        {{title:'ヤフショ感謝デー',dates:['2026-08-22'],rate:5,rate_label:'最大+5%',is_total:false,is_max:true,informational:false,rankable:true,target_store_limited:true,eligibility_rule:'campaign_target_store',conditions:['付与上限1,000円相当']}}
      ]}};activeShopQuery='https://store.shopping.yahoo.co.jp/test-shop/';document.querySelector('#shop').value='テストショップ';document.querySelector('#purchaseAmount').value='35980';document.querySelector('#yahooRank').value='unknown';view=new Date(2026,7,1);selectedIso='';render();
    }}''')
    r=page.evaluate("()=>OtokubiDailyPoints.scoreDay('2026-08-23',23,activeShopQuery,35980)");assert r['pointExact'] is True and r['campaignPoints']==1635,r
    r=page.evaluate("()=>OtokubiDailyPoints.scoreDay('2026-08-22',22,activeShopQuery,35980)");assert r['pointExact'] is False,r
    page.locator('#yahooRank').select_option('gold');r=page.evaluate("()=>OtokubiDailyPoints.scoreDay('2026-08-22',22,activeShopQuery,35980)");assert r['pointExact'] is True and r['campaignPoints']==1000,r

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        iphone=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True,locale='ja-JP',timezone_id='Asia/Tokyo',accept_downloads=True);page=iphone.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);assert 'v0.9.4' in page.locator('.versionBadge').inner_text();assert page.locator('#fiveDayEligible').is_checked();assert page.locator('#yahooRank').input_value() in ('unknown','silver','gold','none');check_sunday_start(page);check_mobile_bonus_badge(page);check_alias(page,'ジョーシン','joshin');check_alias(page,'ヤマダ電機','yamada-denki');iphone.close()
        desktop=browser.new_context(viewport={'width':1440,'height':900},locale='ja-JP',timezone_id='Asia/Tokyo');page=desktop.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);check_daily_point_comparison(page);check_unknown_day_excluded(page);check_premium_sunday_and_rank(page);desktop.close();browser.close()
    print('PWA smoke: PASS (v0.9.4 exact daily-changing points + uncertainty exclusion + mobile + aliases)')
if __name__=='__main__':main()
