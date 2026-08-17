from __future__ import annotations
import asyncio, json, re, html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'; DATA.mkdir(exist_ok=True)
JST = timezone(timedelta(hours=9))
LIST_URL = 'https://shopping.yahoo.co.jp/promotion/campaign/bsplus/list/'
GUIDE_URL = 'https://shopping.yahoo.co.jp/promotion/campaign/guide/'
SCHEMA = 3

MAJOR_CAMPAIGN_KEYWORDS = (
    'プレミアムな日曜日','ヤフショ感謝デー','爆買','Brand Week','ブランドウィーク',
    '超PayPay祭','ファーストデイ','買う！買う！サンデー','ポイントアップ','最大+','最大＋'
)
EXCLUDE_CAMPAIGN_KEYWORDS = ('対象者限定','クーポン','ebookjapan','ZOZOTOWN')

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
            if r is not None:
                rate=r; headings.append(r)
        else:
            href=html.unescape(m.group(2) or '')
            name=clean(html.unescape(re.sub(r'<[^>]+>',' ',m.group(3) or '')))
            if rate is not None and name and 'store.shopping.yahoo.co.jp/' in href:
                out.append({'name':name,'url':href,'slug':store_slug(href),'rate':rate})
    return dedupe_stores(out), sorted(set(headings), reverse=True)

def dedupe_stores(stores):
    uniq={}
    for s in stores:
        name,url=clean(s.get('name')),s.get('url','')
        rate=s.get('rate')
        if not name or not url or rate is None: continue
        slug=s.get('slug') or store_slug(url)
        key=(slug or norm(name), float(rate))
        row={'name':name,'url':url,'slug':slug,'rate':float(rate)}
        if key not in uniq or (not uniq[key].get('slug') and slug): uniq[key]=row
    return list(uniq.values())

async def wait_stable(page, ms=450):
    try: await page.wait_for_load_state('networkidle', timeout=8000)
    except Exception: pass
    await page.wait_for_timeout(ms)

async def read_visible_stores(page):
    rows = await page.evaluate(r'''() => {
      const heads=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')];
      const sections=[];
      for (const h of heads) {
        const m=(h.innerText||'').replace(/\s+/g,' ').match(/\+?\s*(\d{1,2}(?:\.\d+)?)\s*%\s*対象ストア/i);
        if (!m) continue;
        const rate=Number(m[1]); let node=h.nextElementSibling;
        while(node && !/^H[1-6]$/.test(node.tagName)) {
          for (const a of node.matches?.('a')?[node]:[...(node.querySelectorAll?.('a')||[])]) {
            const href=a.href||'', name=(a.innerText||'').replace(/\s+/g,' ').trim();
            if(name && href.includes('store.shopping.yahoo.co.jp/')) sections.push({name,href,rate});
          }
          node=node.nextElementSibling;
        }
      }
      return sections;
    }''')
    return dedupe_stores([{'name':r.get('name'),'url':r.get('href',''),'slug':store_slug(r.get('href','')),'rate':r.get('rate')} for r in rows])

async def get_rate_headings(page):
    headings=await page.locator('h1,h2,h3,h4,h5,h6').all_inner_texts()
    rates=[parse_rate_heading(x) for x in headings]
    return sorted({x for x in rates if x is not None}, reverse=True)

async def collect_all_categories(page):
    all_stores=[]
    diag={'selects_initial':0,'options_total':0,'options_attempted':0,'options_succeeded':0,'options_failed':0,'failures':[]}
    all_stores.extend(await read_visible_stores(page))
    select_defs = await page.locator('select').evaluate_all(r'''els => els.map((s,si) => ({si, options:[...s.options].map((o,oi)=>({oi,value:o.value,text:(o.innerText||'').trim(),disabled:o.disabled}))}))''')
    diag['selects_initial']=len(select_defs)
    candidates=[]
    for sd in select_defs:
        for opt in sd['options']:
            if opt.get('disabled'): continue
            val,text=opt.get('value',''),clean(opt.get('text',''))
            if not val or text in ('選択してください','カテゴリを選択','すべて','全て','指定なし'): continue
            candidates.append((sd['si'],opt['oi'],val,text))
    diag['options_total']=len(candidates)
    for si,oi,val,text in candidates:
        diag['options_attempted']+=1
        try:
            selects=page.locator('select')
            if await selects.count() <= si: raise RuntimeError('select disappeared')
            sel=selects.nth(si)
            try: await sel.select_option(value=val, timeout=5000)
            except Exception: await sel.select_option(index=oi, timeout=5000)
            await wait_stable(page)
            rows=await read_visible_stores(page)
            if not rows:
                raise RuntimeError('selection yielded zero store rows')
            all_stores.extend(rows); diag['options_succeeded']+=1
        except Exception as e:
            diag['options_failed']+=1
            if len(diag['failures'])<20: diag['failures'].append({'select':si,'option':text,'message':clean(repr(e))[:240]})
    stores=dedupe_stores(all_stores)
    diag['stores_total']=len(stores)
    return stores,diag

def quality_status(stores, heading_rates, diag):
    if not heading_rates or not stores: return 'parse_error','rate headings or store links were not parsed'
    attempted=diag.get('options_attempted',0); failed=diag.get('options_failed',0)
    if attempted and failed:
        return 'partial','some category selections failed; not-found results are not trustworthy'
    if len(stores) < 8:
        return 'partial','too few stores parsed to safely assert non-membership'
    return 'ok',''

async def collect_bonus(page):
    out={'schema':SCHEMA,'source':LIST_URL,'updated_at':datetime.now(JST).isoformat(),'days':[],'errors':[]}
    try:
        resp=await page.goto(LIST_URL,wait_until='domcontentloaded',timeout=60000); await wait_stable(page)
        anchors=await page.locator('a').evaluate_all("els => els.map(a => ({text:(a.innerText||'').trim(),href:a.href||''}))")
        if resp and resp.status >= 400: raise RuntimeError(f'HTTP {resp.status}')
    except Exception as e:
        out['errors'].append({'stage':'list','message':repr(e)}); return out
    events=[]; seen=set()
    for a in anchors:
        label,href=clean(a.get('text')),a.get('href','')
        if '/promotion/campaign/bsplus/list/event/' not in href or href in seen: continue
        seen.add(href); date=parse_date_from_anchor(label)
        if date: events.append((date,href,label))
    events.sort(); now=datetime.now(JST).date(); lo,hi=now-timedelta(days=45),now+timedelta(days=75)
    events=[e for e in events if lo<=datetime.fromisoformat(e[0]).date()<=hi]
    if not events: out['errors'].append({'stage':'list','message':'No dated event links parsed'})
    for date,href,label in events:
        rec={'date':date,'url':href,'label':label,'status':'ok','stores':[],'rates':[],'diagnostics':{}}
        try:
            resp=await page.goto(href,wait_until='domcontentloaded',timeout=60000); await wait_stable(page)
            if resp and resp.status >= 400: raise RuntimeError(f'HTTP {resp.status}')
            stores,diag=await collect_all_categories(page)
            heading_rates=await get_rate_headings(page)
            rec['stores']=stores; rec['rates']=sorted({s['rate'] for s in stores},reverse=True); rec['diagnostics']=diag; rec['heading_rates']=heading_rates
            status,error=quality_status(stores,heading_rates,diag); rec['status']=status
            if error: rec['error']=error
            rec['diagnostics']['heading_rates']=heading_rates
        except Exception as e:
            rec['status']='fetch_error'; rec['error']=clean(repr(e))[:500]
        out['days'].append(rec)
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
    cur=start; out=[]
    while cur<=end: out.append(cur.isoformat()); cur+=timedelta(days=1)
    return out

def is_major_campaign(title: str, block: str=''):
    t=clean(title); b=clean(block)
    if not t: return False
    if any(k in t for k in EXCLUDE_CAMPAIGN_KEYWORDS): return False
    return any(k.lower() in (t+' '+b).lower() for k in MAJOR_CAMPAIGN_KEYWORDS)

def parse_campaigns_from_text(text:str):
    lines=[clean(x) for x in text.splitlines() if clean(x)]; campaigns=[]
    for i,line in enumerate(lines):
        if '開催期間' not in line: continue
        block_lines=[line]
        for j in range(i+1,min(i+10,len(lines))):
            if '開催期間' in lines[j]: break
            block_lines.append(lines[j])
        period=line
        if not parse_jp_dates(period) and len(block_lines)>1:
            period=' '.join(block_lines[:2])
        dates=expand_period(period)
        if not dates: continue
        window=lines[max(0,i-8):i]
        reject=('開催期間','注文金額','付与率','付与上限','対象ストア','対象商品','値引','条件','エントリー','※')
        title=''
        for x in reversed(window):
            if len(x)>80 or any(x.startswith(r) for r in reject): continue
            if re.fullmatch(r'[\-–—|｜:： ]+',x): continue
            title=x; break
        block=' '.join(window[-3:]+block_lines)
        if title and is_major_campaign(title,block):
            campaigns.append({'title':title,'period':period,'dates':dates})
    uniq=[]; seen=set()
    for c in campaigns:
        key=(norm(c['title']),tuple(c['dates']))
        if key not in seen: seen.add(key); uniq.append(c)
    return uniq

async def collect_guide(page):
    out={'schema':SCHEMA,'source':GUIDE_URL,'updated_at':datetime.now(JST).isoformat(),'campaigns':[],'errors':[]}
    try:
        resp=await page.goto(GUIDE_URL,wait_until='domcontentloaded',timeout=60000); await wait_stable(page)
        if resp and resp.status >= 400: raise RuntimeError(f'HTTP {resp.status}')
        body=await page.locator('body').inner_text(timeout=10000)
        out['campaigns']=parse_campaigns_from_text(body)
    except Exception as e: out['errors'].append({'message':clean(repr(e))[:500]})
    return out

KNOWN_REGRESSIONS = [
    {'date':'2026-08-17','slug':'tplink','rate':5.0,'label':'TP-Link公式ダイレクト'},
]

def check_known_regressions(bonus):
    issues=[]
    bydate={d.get('date'):d for d in bonus.get('days',[])}
    for r in KNOWN_REGRESSIONS:
        day=bydate.get(r['date'])
        if not day: continue
        hits=[s for s in day.get('stores',[]) if s.get('slug')==r['slug'] and float(s.get('rate',-1))==r['rate']]
        if not hits: issues.append(f"Regression failed: {r['date']} {r['slug']} expected +{r['rate']:g}%")
    return issues

def validate_output(bonus, guide):
    issues=[]
    if not bonus.get('days'): issues.append('BONUS+ day list is empty')
    ok=sum(1 for d in bonus.get('days',[]) if d.get('status')=='ok')
    partial=sum(1 for d in bonus.get('days',[]) if d.get('status')=='partial')
    bad=sum(1 for d in bonus.get('days',[]) if d.get('status') in ('parse_error','fetch_error'))
    if bonus.get('days') and ok==0: issues.append('No BONUS+ day reached authoritative status=ok')
    if bad > max(3, len(bonus.get('days',[]))//4): issues.append(f'Too many failed BONUS+ days: {bad}')
    if guide.get('errors'): issues.append('Guide fetch/parser reported errors')
    issues.extend(check_known_regressions(bonus))
    return {'ok':not issues,'issues':issues,'counts':{'days':len(bonus.get('days',[])),'ok':ok,'partial':partial,'bad':bad,'campaigns':len(guide.get('campaigns',[]))}}

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=await browser.new_page(locale='ja-JP',timezone_id='Asia/Tokyo',user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1')
        bonus=await collect_bonus(page); guide=await collect_guide(page); await browser.close()
    validation=validate_output(bonus,guide)
    bonus['validation']=validation; guide['validation']=validation
    (DATA/'bonus.json').write_text(json.dumps(bonus,ensure_ascii=False,indent=2),encoding='utf-8')
    (DATA/'campaigns.json').write_text(json.dumps(guide,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(validation,ensure_ascii=False))
    if not validation['ok']: raise SystemExit(2)

if __name__=='__main__': asyncio.run(main())
