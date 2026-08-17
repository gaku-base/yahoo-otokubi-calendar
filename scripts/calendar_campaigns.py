from __future__ import annotations
import re, unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

CALENDAR_URL='https://shopping.yahoo.co.jp/promotion/campaign/dailybonus/calendar/'
JST=timezone(timedelta(hours=9))
WEEKDAYS={'月','火','水','木','金','土','日','月曜','火曜','水曜','木曜','金曜','土曜','日曜'}
STOP_MARKERS=('期間開催の予定','※付与されるPayPayポイントは')
TITLE_EXCLUDES=('クーポン','くじ','抽選','OFF','値引','ギフトで贈る')
DETAIL_PREFIXES=('注文','要エントリー','対象','付与上限','先着順','利用下限','指定支払い','条件')

def clean(s:str)->str:
    return re.sub(r'\s+',' ',s or '').strip()

def norm(s:str)->str:
    return re.sub(r'[\s\-_・･/／]+','',unicodedata.normalize('NFKC',s or '').lower())

def infer_year(month:int,day:int,reference:date|None=None)->int:
    ref=reference or datetime.now(JST).date(); choices=[]
    for y in (ref.year-1,ref.year,ref.year+1):
        try: d=date(y,month,day)
        except ValueError: continue
        choices.append((abs((d-ref).days),d<ref-timedelta(days=200),y))
    if not choices: raise ValueError(f'invalid month/day {month}/{day}')
    choices.sort(key=lambda x:(x[1],x[0]));return choices[0][2]

def parse_range(line:str,reference:date|None=None):
    m=re.fullmatch(r'(\d{1,2})/(\d{1,2})\s*[~〜～\-]\s*(\d{1,2})/(\d{1,2})',clean(line))
    if not m:return None
    m1,d1,m2,d2=map(int,m.groups());y=infer_year(m1,d1,reference)
    start=date(y,m1,d1);end=date(y,m2,d2)
    if end<start:end=date(y+1,m2,d2)
    if (end-start).days>45:return None
    return start,end

def parse_explicit_day(line:str,reference:date|None=None,active_range=None):
    m=re.fullmatch(r'(\d{1,2})/(\d{1,2})',clean(line))
    if not m:return None
    month,day=map(int,m.groups())
    if active_range:
        start,end=active_range
        for y in {start.year,end.year}:
            try:d=date(y,month,day)
            except ValueError:continue
            if start<=d<=end:return d
    return date(infer_year(month,day,reference),month,day)

def parse_rate(line:str):
    s=unicodedata.normalize('NFKC',clean(line)).replace('％','%')
    m=re.fullmatch(r'(最大\s*)?\+\s*(\d{1,2}(?:\.\d+)?)\s*%',s,re.I)
    if not m:return None
    return {'rate':float(m.group(2)),'is_max':bool(m.group(1)),'rate_label':s.replace(' ','')}

def looks_like_title(line:str)->bool:
    s=clean(line)
    if not s or s in WEEKDAYS or s.isdigit() or len(s)>90:return False
    if any(x.lower() in s.lower() for x in TITLE_EXCLUDES):return False
    if any(s.startswith(x) for x in DETAIL_PREFIXES):return False
    if parse_rate(s):return False
    if re.fullmatch(r'\d{1,2}/\d{1,2}',s) or parse_range(s):return False
    return True

def day_from_number(n:int,active_range,cursor:date|None):
    if not active_range:return None
    start,end=active_range;d=max(start,cursor or start)
    while d<=end:
        if d.day==n:return d
        d+=timedelta(days=1)
    return None

def parse_calendar_text(text:str,reference:date|None=None):
    lines=[clean(x) for x in (text or '').splitlines() if clean(x)]
    groups={};active=None;cursor=None;current=None;started=False
    for i,line in enumerate(lines):
        rg=parse_range(line,reference)
        if rg:
            active=rg;cursor=rg[0];current=None;started=True;continue
        if not started:continue
        if any(line.startswith(x) for x in STOP_MARKERS):break
        explicit=parse_explicit_day(line,reference,active)
        if explicit:
            current=explicit;cursor=explicit;continue
        if re.fullmatch(r'\d{1,2}',line):
            n=int(line)
            if 1<=n<=31:
                d=day_from_number(n,active,cursor)
                if d:current=d;cursor=d;continue
        rate=parse_rate(line)
        if not current or not rate or i==0:continue
        title=lines[i-1]
        if not looks_like_title(title):continue
        detail=''
        if i+1<len(lines):
            nxt=lines[i+1]
            if not parse_rate(nxt) and not parse_range(nxt,reference) and not re.fullmatch(r'\d{1,2}(?:/\d{1,2})?',nxt) and nxt not in WEEKDAYS:
                detail=nxt
        key=(norm(title),rate['rate'],rate['is_max'])
        if key not in groups:
            groups[key]={'title':title,'rate':rate['rate'],'rate_label':rate['rate_label'],'is_max':rate['is_max'],'dates':[],'conditions':[],'source':CALENDAR_URL}
        iso=current.isoformat()
        if iso not in groups[key]['dates']:groups[key]['dates'].append(iso)
        if detail and detail not in groups[key]['conditions']:groups[key]['conditions'].append(detail)
    out=list(groups.values())
    for c in out:
        c['dates'].sort()
        joined=' '.join(c.get('conditions',[]))
        c['entry_required']='要エントリー' in joined
        c['target_store_limited']='対象ストア限定' in joined
    out.sort(key=lambda c:(c['dates'][0] if c['dates'] else '9999',c['title']))
    return out

def merge_safe_guide(calendar_campaigns:list[dict],guide:dict):
    out=[dict(c) for c in calendar_campaigns];index={(norm(c['title']),c.get('rate')):c for c in out}
    for c in guide.get('campaigns',[]):
        title=clean(c.get('title',''));n=norm(title)
        rate=None;is_max=False
        if 'プレミアムな日曜日' in title:rate=5.0
        elif 'ヤフショ感謝デー' in title:rate=5.0;is_max=True
        elif '爆買WEEK' in title or 'Brand Week' in title or 'ブランドウィーク' in title:
            m=re.search(r'(最大\s*)?[+＋]\s*(\d+(?:\.\d+)?)\s*[%％]',title)
            if m:rate=float(m.group(2));is_max=bool(m.group(1))
        else:continue
        key=(n,rate)
        row=index.get(key)
        if row is None:
            row={'title':title,'rate':rate,'rate_label':(('最大' if is_max else '')+f'+{rate:g}%') if rate is not None else None,'is_max':is_max,'dates':[],'conditions':[],'source':c.get('source') or guide.get('source'),'period':c.get('period','')}
            out.append(row);index[key]=row
        for iso in c.get('dates',[]):
            if iso not in row['dates']:row['dates'].append(iso)
        row['dates'].sort()
    out=[c for c in out if c.get('dates')]
    out.sort(key=lambda c:(c['dates'][0],c['title']))
    return out

async def collect_calendar(page,reference:date|None=None):
    result={'source':CALENDAR_URL,'campaigns':[],'errors':[]}
    try:
        resp=await page.goto(CALENDAR_URL,wait_until='domcontentloaded',timeout=45000)
        if resp and resp.status>=400:raise RuntimeError(f'HTTP {resp.status}')
        await page.wait_for_timeout(400)
        body=await page.locator('body').inner_text(timeout=15000)
        result['campaigns']=parse_calendar_text(body,reference)
        if not result['campaigns']:raise RuntimeError('No point campaigns parsed from official bonus calendar')
    except Exception as e:result['errors'].append({'message':clean(repr(e))[:500]})
    return result
