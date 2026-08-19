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

def synthetic_days(overrides=None):
    overrides=overrides or {}
    return ','.join([f"{{date:'2026-08-{d:02d}',status:'ok',offers:[[0,{overrides.get(d,5)}]]}}" for d in range(1,32)])

def check_total_point_display(page):
    days=synthetic_days({2:10});page.evaluate(f'''() => {{
      window.__OTOKUBI_TODAY__='2026-08-01';
      bonus={{rate_caps:{{'5':5000,'10':10000}},store_catalog:[['テストショップ','test-shop']],days:[{days}]}};
      campaigns={{campaigns:[{{title:'5のつく日',dates:['2026-08-05'],rate:4,rate_label:'+4%',is_total:false,is_max:false,informational:false,rankable:true,target_store_limited:false,eligibility_rule:'all',conditions:['要エントリー 指定支払い方法あり 付与上限1,000円相当']}}]}};
      activeShopQuery='https://store.shopping.yahoo.co.jp/test-shop/';document.querySelector('#shop').value='テストショップ';document.querySelector('#purchaseAmount').value='35980';document.querySelector('#fiveDayEligible').checked=true;document.querySelector('#yahooRank').value='unknown';view=new Date(2026,7,1);selectedIso='';render();
    }}''')
    page.wait_for_function("document.querySelector('#top3Strip .top3Item') !== null");texts=page.locator('#top3Strip .top3Item').all_inner_texts();assert '1位' in texts[0] and '2日' in texts[0] and '合計 約5,590pt' in texts[0] and '通常7%' in texts[0] and '通常日比 +1,635pt' in texts[0],texts;assert any('5日' in t and '合計 約4,955pt' in t and '通常日比 +1,000pt' in t for t in texts),texts
    day2=page.get_by_role('button',name='8月2日');assert '計 5,590pt' in day2.inner_text(),day2.inner_text();day2.click();detail=page.locator('#detail').inner_text();assert '合計獲得 約5,590pt' in detail,detail;assert '通常ポイント 7% 約2,320pt' in detail,detail;assert 'BONUS+ 約3,270pt' in detail,detail;assert '通常日比 +1,635pt' in detail,detail
    day1=page.get_by_role('button',name='8月1日');assert '計 3,955pt' in day1.inner_text(),day1.inner_text();day1.click();detail=page.locator('#detail').inner_text();assert '通常日と同じ水準' in detail and '合計獲得 約3,955pt' in detail and '通常ポイント 7% 約2,320pt' in detail,detail

def check_same_day_happy24(page):
    days=synthetic_days();page.evaluate(f'''() => {{
      window.__OTOKUBI_TODAY__='2026-08-19';
      bonus={{rate_caps:{{'5':5000}},store_catalog:[['テストショップ','test-shop']],days:[{days}]}};
      campaigns={{campaigns:[{{title:'ハッピー24アワー',dates:['2026-08-19'],rate:4,rate_label:'+4%',is_total:false,is_max:false,informational:false,rankable:true,target_store_limited:false,eligibility_rule:'all',same_day_discovery:true,conditions:['要エントリー 注文3,000円～ 付与上限2,000円相当']}}]}};
      activeShopQuery='https://store.shopping.yahoo.co.jp/test-shop/';document.querySelector('#shop').value='テストショップ';document.querySelector('#purchaseAmount').value='35980';view=new Date(2026,7,1);selectedIso='';render();
    }}''')
    r=page.evaluate("()=>OtokubiDailyPoints.scoreDay('2026-08-19',19,activeShopQuery,35980)");assert r['campaignRate']==4 and r['campaignPoints']==1308 and r['totalPoints']==5263,r
    cell=page.get_by_role('button',name='8月19日');assert '計 5,263pt' in cell.inner_text(),cell.inner_text();cell.click();detail=page.locator('#detail').inner_text();assert 'ハッピー24アワー 約1,308pt' in detail and '合計獲得 約5,263pt' in detail,detail

def check_unknown_day_zero(page):
    days=synthetic_days({2:10});page.evaluate(f'''() => {{
      window.__OTOKUBI_TODAY__='2026-08-01';
      bonus={{rate_caps:{{'5':5000,'10':10000}},store_catalog:[['テストショップ','test-shop']],days:[{days}]}};
      campaigns={{campaigns:[{{title:'ボーナスストアPlus 優良ストアでさらに+3%',dates:['2026-08-18'],rate:3,rate_label:'+3%',is_total:false,is_max:false,informational:false,rankable:true,target_store_limited:true,eligibility_rule:'preferred_bonus_store',conditions:['注文3,000円～ 付与上限5,000円相当']}}]}};
      activeShopQuery='https://store.shopping.yahoo.co.jp/test-shop/';document.querySelector('#shop').value='テストショップ';document.querySelector('#purchaseAmount').value='35980';view=new Date(2026,7,1);selectedIso='';render();
    }}''')
    page.wait_for_function("document.querySelector('#top3Strip .top3Notice') !== null");notice=page.locator('#top3Strip .top3Notice').inner_text();assert '未確認分は0ptとして順位計算' in notice,notice
    cell=page.get_by_role('button',name='8月18日');text=cell.inner_text();assert '計 3,955pt※' in text and '計 要確認' not in text,text;cell.click();detail=page.locator('#detail').inner_text();assert '合計獲得 約3,955pt' in detail and '未確認分 0pt計上' in detail and '未確認特典 0pt' in detail and '優良ストア対象可否を自動判定できない' in detail,detail;assert '合計獲得 要確認' not in detail,detail

def check_premium_sunday_and_rank(page):
    days=synthetic_days({2:10});page.evaluate(f'''() => {{
      window.__OTOKUBI_TODAY__='2026-08-01';
      bonus={{rate_caps:{{'5':5000,'10':10000}},store_catalog:[['テストショップ','test-shop']],days:[{days}]}};
      campaigns={{campaigns:[
        {{title:'プレミアムな日曜日',dates:['2026-08-23'],rate:5,rate_label:'+5%',is_total:false,is_max:false,informational:false,rankable:true,target_store_limited:true,eligibility_rule:'campaign_target_store',conditions:['注文5,000円～ 付与上限2,000円相当']}},
        {{title:'ヤフショ感謝デー',dates:['2026-08-22'],rate:5,rate_label:'最大+5%',is_total:false,is_max:true,informational:false,rankable:true,target_store_limited:true,eligibility_rule:'campaign_target_store',conditions:['付与上限1,000円相当']}}
      ]}};activeShopQuery='https://store.shopping.yahoo.co.jp/test-shop/';document.querySelector('#shop').value='テストショップ';document.querySelector('#purchaseAmount').value='35980';document.querySelector('#yahooRank').value='unknown';view=new Date(2026,7,1);selectedIso='';render();
    }}''')
    r=page.evaluate("()=>OtokubiDailyPoints.scoreDay('2026-08-23',23,activeShopQuery,35980)");assert r['pointExact'] is True and r['campaignPoints']==1635 and r['basePoints']==2320 and r['totalPoints']==5590,r
    r=page.evaluate("()=>OtokubiDailyPoints.scoreDay('2026-08-22',22,activeShopQuery,35980)");assert r['pointExact'] is False and r['campaignPoints']==0 and r['totalPoints']==3955,r
    page.get_by_role('button',name='8月22日').click();detail=page.locator('#detail').inner_text();assert '合計獲得 約3,955pt' in detail and 'ヤフショランク未設定' in detail and '0ptとして計上' in detail,detail
    page.locator('#yahooRank').select_option('gold');r=page.evaluate("()=>OtokubiDailyPoints.scoreDay('2026-08-22',22,activeShopQuery,35980)");assert r['pointExact'] is True and r['campaignPoints']==1000 and r['totalPoints']==4955,r

def check_past_days_excluded(page):
    days=synthetic_days({2:10,18:7,20:10});page.evaluate(f'''() => {{
      window.__OTOKUBI_TODAY__='2026-08-18';
      bonus={{rate_caps:{{'5':5000,'7':7000,'10':10000}},store_catalog:[['テストショップ','test-shop']],days:[{days}]}};
      campaigns={{campaigns:[]}};activeShopQuery='https://store.shopping.yahoo.co.jp/test-shop/';document.querySelector('#shop').value='テストショップ';document.querySelector('#purchaseAmount').value='35980';view=new Date(2026,7,1);selectedIso='';render();
    }}''')
    page.wait_for_function("document.querySelectorAll('#calendar .day.pastDay').length===17")
    a=page.evaluate("()=>OtokubiDailyPoints.monthAnalysis()");assert a['today']=='2026-08-18' and a['pastCount']==17,a;assert a['activeRows'][0]['iso']=='2026-08-18',a['activeRows'][0]
    day2=page.get_by_role('button',name='8月2日');assert 'pastDay' in (day2.get_attribute('class') or '');assert '過去' in day2.inner_text();assert '計 ' not in day2.inner_text();assert not any(x in (day2.get_attribute('class') or '') for x in ('rank1','rank2','rank3'))
    today=page.get_by_role('button',name='8月18日');assert 'pastDay' not in (today.get_attribute('class') or '');assert '計 ' in today.inner_text()
    texts=page.locator('#top3Strip .top3Item').all_inner_texts();assert texts and '20日' in texts[0],texts;assert all('2日' not in t for t in texts),texts;assert any('18日' in t for t in texts),texts
    day2.click();detail=page.locator('#detail').inner_text();assert '過去日・順位対象外' in detail and '過去日の参考ポイント' in detail and '現在のお得日順位には反映しません' in detail,detail

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        iphone=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True,locale='ja-JP',timezone_id='Asia/Tokyo',accept_downloads=True);page=iphone.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);assert 'v0.9.9' in page.locator('.versionBadge').inner_text();assert '通常ポイント 7%' in page.locator('#calcAssumption').inner_text();assert '過去日は順位対象外' in page.locator('#calcAssumption').inner_text();assert '未確認条件は0pt' in page.locator('#calcAssumption').inner_text();assert '当日発表のデイリーボーナス' in page.locator('#calcAssumption').inner_text();page.wait_for_function("window.OtokubiFreshCampaigns !== undefined");assert page.locator('#fiveDayEligible').is_checked();assert page.locator('#yahooRank').input_value() in ('unknown','silver','gold','none');check_sunday_start(page);check_mobile_bonus_badge(page);check_alias(page,'ジョーシン','joshin');check_alias(page,'ヤマダ電機','yamada-denki');iphone.close()
        desktop=browser.new_context(viewport={'width':1440,'height':900},locale='ja-JP',timezone_id='Asia/Tokyo');page=desktop.new_page();page.goto(URL,wait_until='domcontentloaded');wait_loaded(page);check_total_point_display(page);check_same_day_happy24(page);check_unknown_day_zero(page);check_premium_sunday_and_rank(page);check_past_days_excluded(page);desktop.close();browser.close()
    print('PWA smoke: PASS (v0.9.9 fresh campaign fallback + same-day bonus + past exclusion + total points + unresolved as zero)')
if __name__=='__main__':main()
