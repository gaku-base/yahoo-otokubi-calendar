from __future__ import annotations
import asyncio, json, re, html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'; DATA.mkdir(exist_ok=True)
JST = timezone(timedelta(hours=9))
LIST_URL = 'https://shopping.yahoo.co.jp/promotion/campaign/bsplus/list/'
GUIDE_URL = 'https://shopping.yahoo.co.jp/promotion/campaign/guide/'
SCHEMA = 4
VERSION = '0.6.0'
MAX_EVENT_CONCURRENCY = 4

MAJOR_CAMPAIGN_KEYWORDS = (
    'プレミアムな日曜日','ヤフショ感謝デー','爆買','Brand Week','ブランドウィーク',
    '超PayPay祭','ファーストデイ','買う！買う！サンデー','ポイントアップ','最大+','最大＋'
)
EXCLUDE_CAMPAIGN_KEYWORDS = ('対象者限定','クーポン','ebookjapan','ZOZOTOWN')
SKIP_OPTION_LABELS = ('選択してください','カテゴリを選択','すべて','全て','指定なし','カテゴリーを選択')

def clean(s: str) -> str:
    return re.sub(r'\s+', ' ', s or '').strip()

def norm(s: str) -> str:
    s = clean(s).lower().translate(str.maketrans({'！':'!','＆':'&','　':' ','／':'/','－':'-'}))
    return re.sub(r'[\s\-_・･/]+', '', s)

def store_slug(url: str) -> str:
    try:
        u = urlparse(url)
        host = u.netloc.lower().split(':')[0]
        if host == 'store.shopping.yahoo.co.jp':
            return (u.path.strip('/').split('/') or [''])[0].lower()
    except Exception:
        pass
    return ''

def parse_rate_heading(text: str):
    m = re.search(r'\+?\s*(\d{1,2}(?:\.\d+)?)\s*%\s*対象ストア', clean(text), re.I)
    return float(m.group(1)) if m else None

def parse_date_from_anchor(label: str, today=None):
    m = re.search(r'(\d{1,2})月\s*(\d{1,2})日', label)
    if not m: return None
    mon, day = map(int, m.groups()); now = today or datetime.now(JST).date(); c=[]
    for y in (now.year-1, now.year, now.year+1):
        try: c.append(datetime(y,mon,day,tzinfo=JST).date())
        except ValueError: pass
    return min(c,key=lambda d:(abs((d-now).days), d < now)).isoformat() if c else None

def parse_static_event_html(raw_html: str):
    txt = re.sub(r'<script\b[^>]*>.*?</script>', ' ', raw_html, flags=re.I|re.S)
    txt = re.sub(r'<style\b[^>]*>.*?</style>', ' ', txt, flags=re.I|re.S)
    token_re = re.compile(r'<h[1-6]\b[^>]*>(.*?)</h[1-6]>|<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I|re.S)
    rate=None; out=[]; headings=[]
    for m in token_re.finditer(txt):
        if m.group(1) is not None:
            heading=clean(html.unescape(re.sub(r'<[^>]+>',' ',m.group(1))))
            r=parse_rate_heading(heading)
            if r is not None: rate=r; headings.append(r)
        else:
            href=html.unescape(m.group(2) or '')
            name=clean(html.unescape(re.sub(r'<[^>]+>',' ',m.group(3) or '')))
            if rate is not None and name and 'store.shopping.yahoo.co.jp/' in href:
                out.append({'name':name,'url':href,'slug':store_slug(href),'rate':rate,'categories':['初期表示']})
    return dedupe_stores(out), sorted(set(headings), reverse=True)

def dedupe_stores(stores):
    uniq={}
    for s in stores:
        name,url=clean(s.get('name')),s.get('url',''); rate=s.get('rate')
        if not name or not url or rate is None: continue
        slug=s.get('slug') or store_slug(url); key=(slug or norm(name), float(rate))
        cats=[]
        for c in s.get('categories',[]) or []:
            c=clean(c)
            if c and c not in cats: cats.append(c)
        row={'name':name,'url':url,'slug':slug,'rate':float(rate),'categories':cats}
        if key not in uniq:
            uniq[key]=row
        else:
            for c in cats:
                if c not in uniq[key]['categories']: uniq[key]['categories'].append(c)
            if not uniq[key].get('slug') and slug: uniq[key]['slug']=slug
    return list(uniq.values())

async def settle(page, ms=180):
    await page.wait_for_timeout(ms)

async def get_sections(page):
    return await page.evaluate(r'''() => {
      const all=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6,select')];
      const sections=[]; let current=null; let selectIndex=0;
      const globalSelects=[...document.querySelectorAll('select')];
      for (const el of all) {
        if (/^H[1-6]$/.test(el.tagName)) {
          const m=(el.innerText||'').replace(/\s+/g,' ').match(/\+?\s*(\d{1,2}(?:\.\d+)?)\s*%\s*対象ストア/i);
          if (m) { current={rate:Number(m[1]), heading:(el.innerText||'').trim(), selectIndexes:[]}; sections.push(current); }
        } else if (el.tagName==='SELECT' && current) {
          selectIndex=globalSelects.indexOf(el); if (selectIndex>=0) current.selectIndexes.push(selectIndex);
        }
      }
      return sections;
    }''')

async def read_rate_stores(page, rate: float, category: str):
    rows = await page.evaluate(r'''(targetRate) => {
      const heads=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')];
      const rateRe=/\+?\s*(\d{1,2}(?:\.\d+)?)\s*%\s*対象ストア/i;
      const h=heads.find(x=>{const m=(x.innerText||'').match(rateRe); return m && Number(m[1])===Number(targetRate)});
      if(!h) return [];
      const out=[]; let n=h.nextElementSibling;
      while(n){
        if(/^H[1-6]$/.test(n.tagName)){ const m=(n.innerText||'').match(rateRe); if(m) break; }
        const anchors=n.matches?.('a')?[n]:[...(n.querySelectorAll?.('a')||[])];
        for(const a of anchors){ const href=a.href||'', name=(a.innerText||'').replace(/\s+/g,' ').trim(); if(name && href.includes('store.shopping.yahoo.co.jp/')) out.push({name,href}); }
        n=n.nextElementSibling;
      }
      return out;
    }''', rate)
    return dedupe_stores([{'name':r['name'],'url':r['href'],'slug':store_slug(r['href']),'rate':rate,'categories':[category]} for r in rows])

async def select_options(page, select_index: int):
    return await page.locator('select').nth(select_index).evaluate(r'''s => [...s.options].map((o,i)=>({i,value:o.value||'',text:(o.innerText||o.textContent||'').replace(/\s+/g,' ').trim(),disabled:!!o.disabled}))''')

async def collect_all_categories(page):
    sections=await get_sections(page)
    all_stores=[]
    diag={'sections':[],'rate_sections':len(sections),'categories_total':0,'categories_attempted':0,'categories_succeeded':0,'categories_failed':0,'failures':[]}
    for section in sections:
        rate=section['rate']; sd={'rate':rate,'selects':len(section['selectIndexes']),'categories_total':0,'categories_succeeded':0,'categories_failed':0}
        initial=await read_rate_stores(page,rate,'初期表示'); all_stores.extend(initial)
        if not section['selectIndexes']:
            sd['static_only']=True; diag['sections'].append(sd); continue
        for si in section['selectIndexes']:
            options=await select_options(page,si)
            candidates=[]
            for opt in options:
                text=clean(opt.get('text','')); val=opt.get('value','')
                if opt.get('disabled') or text in SKIP_OPTION_LABELS or (not val and not text): continue
                candidates.append(opt)
            sd['categories_total']+=len(candidates); diag['categories_total']+=len(candidates)
            for opt in candidates:
                text=clean(opt.get('text','')) or f"option-{opt['i']}"; diag['categories_attempted']+=1
                try:
                    sel=page.locator('select').nth(si)
                    if opt.get('value'):
                        await sel.select_option(value=opt['value'],timeout=2500)
                    else:
                        await sel.select_option(index=opt['i'],timeout=2500)
                    await settle(page)
                    rows=await read_rate_stores(page,rate,text)
                    if not rows: raise RuntimeError('category yielded zero store rows')
                    all_stores.extend(rows); sd['categories_succeeded']+=1; diag['categories_succeeded']+=1
                except Exception as e:
                    sd['categories_failed']+=1; diag['categories_failed']+=1
                    if len(diag['failures'])<50: diag['failures'].append({'rate':rate,'select':si,'category':text,'message':clean(repr(e))[:220]})
        diag['sections'].append(sd)
    stores=dedupe_stores(all_stores); diag['stores_total']=len(stores)
    return stores,diag,sorted({s['rate'] for s in stores},reverse=True)

def quality_status(stores, heading_rates, diag):
    if not heading_rates or not stores: return 'parse_error','rate headings or store links were not parsed'
    if diag.get('rate_sections',0) != len(heading_rates): return 'partial','rate section count mismatch'
    if diag.get('categories_failed',0): return 'partial','one or more categories failed; non-membership is not trustworthy'
    for section in diag.get('sections',[]):
        if section.get('selects',0)>0 and section.get('categories_total',0)!=section.get('categories_succeeded',0):
            return 'partial','not all category options were captured'
    return 'ok',''

async def scrape_event(browser, event, sem):
    date,href,label=event
    rec={'date':date,'url':href,'label':label,'status':'ok','stores':[],'rates':[],'diagnostics':{}}
    async with sem:
        page=await browser.new_page(locale='ja-JP',timezone_id='Asia/Tokyo',user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1')
        try:
            resp=await page.goto(href,wait_until='domcontentloaded',timeout=30000); await settle(page,250)
            if resp and resp.status>=400: raise RuntimeError(f'HTTP {resp.status}')
            sections=await get_sections(page); heading_rates=sorted({float(s['rate']) for s in sections},reverse=True)
            stores,diag,rates=await collect_all_categories(page)
            rec['stores']=stores; rec['rates']=rates; rec['heading_rates']=heading_rates; rec['diagnostics']=diag
            status,error=quality_status(stores,heading_rates,diag); rec['status']=status
            if error: rec['error']=error
        except Exception as e:
            rec['status']='fetch_error'; rec['error']=clean(repr(e))[:500]
        finally:
            await page.close()
    return rec

async def collect_bonus(browser):
    out={'schema':SCHEMA,'version':VERSION,'source':LIST_URL,'updated_at':datetime.now(JST).isoformat(),'days':[],'errors':[],'list_diagnostics':{}}
    page=await browser.new_page(locale='ja-JP',timezone_id='Asia/Tokyo')
    try:
        resp=await page.goto(LIST_URL,wait_until='domcontentloaded',timeout=30000); await settle(page,250)
        if resp and resp.status>=400: raise RuntimeError(f'HTTP {resp.status}')
        anchors=await page.locator('a').evaluate_all("els => els.map(a => ({text:(a.innerText||'').trim(),href:a.href||''}))")
    except Exception as e:
        out['errors'].append({'stage':'list','message':clean(repr(e))}); await page.close(); return out
    await page.close()
    events=[]; seen=set()
    for a in anchors:
        label,href=clean(a.get('text')),a.get('href','')
        if '/promotion/campaign/bsplus/list/event/' not in href or href in seen: continue
        date=parse_date_from_anchor(label)
        if not date: continue
        seen.add(href); events.append((date,href,label))
    events.sort(key=lambda x:(x[0],x[1])); out['list_diagnostics']['event_links']=len(events)
    if not events: out['errors'].append({'stage':'list','message':'No dated event links parsed'}); return out
    sem=asyncio.Semaphore(MAX_EVENT_CONCURRENCY)
    out['days']=await asyncio.gather(*(scrape_event(browser,e,sem) for e in events))
    return out

def parse_jp_dates(text:str):
    found=[]
    for pat in [r'(20\d{2})[/-](\d{1,2})[/-](\d{1,2})',r'(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日']:
        for y,m,d in re.findall(pat,text):
            try: found.append(datetime(int(y),int(m),int(d),tzinfo=JST).date())
            except ValueError: pass
    return sorted(set(found))

def expand_period(text:str):
    dates=parse_jp_dates(text)
    if not dates:return []
    if len(dates)==1:return [dates[0].isoformat()]
    start,end=dates[0],dates[-1]
    if end<start or (end-start).days>93:return [d.isoformat() for d in dates]
    return [(start+timedelta(days=i)).isoformat() for i in range((end-start).days+1)]

def is_major_campaign(title: str, block: str=''):
    t=clean(title); b=clean(block)
    if not t:return False
    if any(k in t for k in EXCLUDE_CAMPAIGN_KEYWORDS):return False
    return any(k.lower() in (t+' '+b).lower() for k in MAJOR_CAMPAIGN_KEYWORDS)

def parse_campaigns_from_text(text:str):
    lines=[clean(x) for x in text.splitlines() if clean(x)]; campaigns=[]
    for i,line in enumerate(lines):
        if '開催期間' not in line:continue
        block_lines=[line]
        for j in range(i+1,min(i+10,len(lines))):
            if '開催期間' in lines[j]:break
            block_lines.append(lines[j])
        period=line
        if not parse_jp_dates(period) and len(block_lines)>1:period=' '.join(block_lines[:2])
        dates=expand_period(period)
        if not dates:continue
        window=lines[max(0,i-8):i]; reject=('開催期間','注文金額','付与率','付与上限','対象ストア','対象商品','値引','条件','エントリー','※'); title=''
        for x in reversed(window):
            if len(x)>80 or any(x.startswith(r) for r in reject):continue
            if re.fullmatch(r'[\-–—|｜:： ]+',x):continue
            title=x;break
        block=' '.join(window[-3:]+block_lines)
        if title and is_major_campaign(title,block):campaigns.append({'title':title,'period':period,'dates':dates})
    uniq=[];seen=set()
    for c in campaigns:
        key=(norm(c['title']),tuple(c['dates']))
        if key not in seen:seen.add(key);uniq.append(c)
    return uniq

async def collect_guide(browser):
    out={'schema':SCHEMA,'version':VERSION,'source':GUIDE_URL,'updated_at':datetime.now(JST).isoformat(),'campaigns':[],'errors':[]}
    page=await browser.new_page(locale='ja-JP',timezone_id='Asia/Tokyo')
    try:
        resp=await page.goto(GUIDE_URL,wait_until='domcontentloaded',timeout=30000);await settle(page,250)
        if resp and resp.status>=400:raise RuntimeError(f'HTTP {resp.status}')
        body=await page.locator('body').inner_text(timeout=10000);out['campaigns']=parse_campaigns_from_text(body)
    except Exception as e:out['errors'].append({'message':clean(repr(e))[:500]})
    finally:await page.close()
    return out

KNOWN_REGRESSIONS=[{'date':'2026-08-17','slug':'tplink','rate':5.0,'label':'TP-Link公式ダイレクト'}]

def check_known_regressions(bonus):
    issues=[];bydate={d.get('date'):d for d in bonus.get('days',[])}
    for r in KNOWN_REGRESSIONS:
        day=bydate.get(r['date'])
        if not day:issues.append(f"Regression date missing: {r['date']}");continue
        hits=[s for s in day.get('stores',[]) if s.get('slug')==r['slug'] and float(s.get('rate',-1))==r['rate']]
        if not hits:issues.append(f"Regression failed: {r['date']} {r['slug']} expected +{r['rate']:g}%")
    return issues

def validate_output(bonus,guide):
    issues=[];days=bonus.get('days',[])
    if not days:issues.append('BONUS+ day list is empty')
    if bonus.get('list_diagnostics',{}).get('event_links')!=len(days):issues.append('Not every event link produced a day record')
    ok=sum(d.get('status')=='ok' for d in days);partial=sum(d.get('status')=='partial' for d in days);bad=sum(d.get('status') in ('parse_error','fetch_error') for d in days)
    incomplete=[d.get('date') for d in days if d.get('status')!='ok']
    if incomplete:issues.append(f"Incomplete BONUS+ days: {len(incomplete)}")
    for d in days:
        dg=d.get('diagnostics',{})
        if dg.get('categories_total')!=dg.get('categories_succeeded'):issues.append(f"Category completeness failed: {d.get('date')}")
    if guide.get('errors'):issues.append('Guide fetch/parser reported errors')
    issues.extend(check_known_regressions(bonus))
    return {'ok':not issues,'issues':issues[:50],'counts':{'days':len(days),'ok':ok,'partial':partial,'bad':bad,'campaigns':len(guide.get('campaigns',[])),'stores':sum(len(d.get('stores',[])) for d in days),'categories':sum(d.get('diagnostics',{}).get('categories_total',0) for d in days)}}

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        bonus=await collect_bonus(browser);guide=await collect_guide(browser);await browser.close()
    validation=validate_output(bonus,guide);bonus['validation']=validation;guide['validation']=validation
    (DATA/'bonus.json').write_text(json.dumps(bonus,ensure_ascii=False,indent=2),encoding='utf-8')
    (DATA/'campaigns.json').write_text(json.dumps(guide,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(validation,ensure_ascii=False))
    if not validation['ok']:raise SystemExit(2)

if __name__=='__main__':asyncio.run(main())
