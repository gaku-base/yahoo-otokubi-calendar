from __future__ import annotations
import re, unicodedata
from datetime import date, datetime, timedelta, timezone

CALENDAR_URL='https://shopping.yahoo.co.jp/promotion/campaign/dailybonus/calendar/'
JST=timezone(timedelta(hours=9))
WEEKDAYS={'月','火','水','木','金','土','日','月曜','火曜','水曜','木曜','金曜','土曜','日曜'}
FINAL_STOP='※付与されるPayPayポイントは'
DETAIL_PREFIXES=('注文','要エントリー','対象','付与上限','先着順','利用下限','指定支払い','条件')
SOURCE_URLS={
 '5のつく日':'https://shopping.yahoo.co.jp/promotion/campaign/5day/',
 'プレミアムな日曜日':'https://shopping.yahoo.co.jp/promotion/campaign/lypsunday/',
 'ヤフショ感謝デー':'https://shopping.yahoo.co.jp/promotion/campaign/pointrank/',
 'ボーナスストアPlus':'https://shopping.yahoo.co.jp/promotion/campaign/bsplus/',
}

def clean(s:str)->str:return re.sub(r'\s+',' ',s or '').strip()
def norm(s:str)->str:return re.sub(r'[\s\-_・･/／]+','',unicodedata.normalize('NFKC',s or '').lower())

def infer_year(month:int,day:int,reference:date|None=None)->int:
    ref=reference or datetime.now(JST).date();choices=[]
    for y in (ref.year-1,ref.year,ref.year+1):
        try:d=date(y,month,day)
        except ValueError:continue
        choices.append((abs((d-ref).days),d<ref-timedelta(days=200),y))
    if not choices:raise ValueError(f'invalid month/day {month}/{day}')
    choices.sort(key=lambda x:(x[1],x[0]));return choices[0][2]

def parse_range(line:str,reference:date|None=None):
    m=re.search(r'(?<!\d)(\d{1,2})/(\d{1,2})\s*[~〜～\-]\s*(\d{1,2})/(\d{1,2})(?!\d)',clean(line))
    if not m:return None
    m1,d1,m2,d2=map(int,m.groups());y=infer_year(m1,d1,reference);start=date(y,m1,d1);end=date(y,m2,d2)
    if end<start:end=date(y+1,m2,d2)
    return (start,end) if (end-start).days<=45 else None

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
    return {'rate':float(m.group(2)),'is_max':bool(m.group(1)),'rate_label':s.replace(' ',''),'is_total':False,'informational':False}

def parse_total_rate(line:str):
    s=unicodedata.normalize('NFKC',clean(line)).replace('％','%')
    m=re.fullmatch(r'最大\s*(\d{1,2}(?:\.\d+)?)\s*%',s,re.I)
    if not m:return None
    return {'rate':None,'is_max':True,'rate_label':s.replace(' ',''),'is_total':True,'informational':False}

def parse_info_value(line:str):
    s=unicodedata.normalize('NFKC',clean(line)).replace('％','%')
    if s=='先着順':return {'rate':None,'is_max':False,'rate_label':'先着順','is_total':False,'informational':True}
    if re.fullmatch(r'最大\s*[0-9,.]+\s*(?:万)?円相当',s):return {'rate':None,'is_max':True,'rate_label':s.replace(' ',''),'is_total':False,'informational':True}
    if re.fullmatch(r'最大\s*\d+(?:\.\d+)?\s*%OFF',s,re.I):return {'rate':None,'is_max':True,'rate_label':s.replace(' ',''),'is_total':False,'informational':True}
    return None

def event_value(line:str):return parse_rate(line) or parse_total_rate(line) or parse_info_value(line)

def looks_like_title(line:str)->bool:
    s=clean(line)
    if not s or s in WEEKDAYS or s.isdigit() or len(s)>90:return False
    if any(s.startswith(x) for x in DETAIL_PREFIXES):return False
    if event_value(s):return False
    if re.fullmatch(r'\d{1,2}/\d{1,2}',s) or parse_range(s):return False
    return True

def next_occurrence(n:int,base:date,max_days=45):
    for delta in range(max_days+1):
        d=base+timedelta(days=delta)
        if d.day==n:return d
    return None

def day_from_number(n:int,active_range,cursor:date|None,reference:date):
    if active_range:
        start,end=active_range;d=max(start,cursor or start)
        while d<=end:
            if d.day==n:return d
            d+=timedelta(days=1)
        return None
    return next_occurrence(n,cursor or reference)

def source_url_for(title:str):
    for k,u in SOURCE_URLS.items():
        if k in title:return u
    return CALENDAR_URL

def eligibility_rule_for(title:str,target_store_limited:bool):
    if 'ボーナスストアPlusでさらに+2%' in title:return 'bonus_plus_member'
    if '優良ストア' in title and 'ボーナスストアPlus' in title:return 'preferred_bonus_store'
    if target_store_limited:return 'campaign_target_store'
    return 'all'

def add_group(groups,title,value,current,detail=''):
    key=(norm(title),value.get('rate'),value.get('rate_label'))
    if key not in groups:
        groups[key]={'title':title,'rate':value.get('rate'),'rate_label':value.get('rate_label'),'is_max':value.get('is_max',False),'is_total':value.get('is_total',False),'informational':value.get('informational',False),'dates':[],'conditions':[],'source':CALENDAR_URL,'source_url':source_url_for(title)}
    iso=current.isoformat()
    if iso not in groups[key]['dates']:groups[key]['dates'].append(iso)
    if detail and detail not in groups[key]['conditions']:groups[key]['conditions'].append(detail)

def parse_period_campaigns(lines,start_index:int,reference:date,groups):
    i=start_index;base=reference
    while i+4<len(lines):
        if lines[i].startswith(FINAL_STOP):break
        m1=re.fullmatch(r'(\d{1,2})\s*[（(][月火水木金土日](?:曜)?[）)]',lines[i])
        if not m1:i+=1;continue
        if lines[i+1] not in ('〜','～','~','-'):i+=1;continue
        m2=re.fullmatch(r'(\d{1,2})\s*[（(][月火水木金土日](?:曜)?[）)]',lines[i+2])
        if not m2:i+=1;continue
        start=next_occurrence(int(m1.group(1)),base);end=next_occurrence(int(m2.group(1)),start or base);title=lines[i+3];v=event_value(lines[i+4])
        if start and end and end>=start and (end-start).days<=31 and v and looks_like_title(title):
            detail=lines[i+5] if i+5<len(lines) and not lines[i+5].startswith(FINAL_STOP) and not re.match(r'^\d+\s*[（(]',lines[i+5]) else ''
            d=start
            while d<=end:add_group(groups,title,v,d,detail);d+=timedelta(days=1)
            base=start
        i+=5

def parse_calendar_text(text:str,reference:date|None=None):
    ref=reference or datetime.now(JST).date();lines=[clean(x) for x in (text or '').splitlines() if clean(x)]
    groups={};active=None;cursor=ref;current=None;started=False;period_index=None
    for i,line in enumerate(lines):
        if line=='期間開催の予定':period_index=i+1;break
        if line.startswith(FINAL_STOP):break
        rg=parse_range(line,ref)
        if rg:active=rg;cursor=rg[0];current=None;started=True;continue
        if line=='まもなく開催' or 'イベントをタップすると' in line:started=True;continue
        if not started:continue
        explicit=parse_explicit_day(line,ref,active)
        if explicit:current=explicit;cursor=explicit;continue
        if re.fullmatch(r'\d{1,2}',line):
            n=int(line)
            if 1<=n<=31:
                d=day_from_number(n,active,cursor,ref)
                if d:current=d;cursor=d;continue
        v=event_value(line)
        if not current or not v or i==0:continue
        title=lines[i-1]
        if not looks_like_title(title):continue
        detail=''
        if i+1<len(lines):
            nxt=lines[i+1]
            if not event_value(nxt) and not parse_range(nxt,ref) and not re.fullmatch(r'\d{1,2}(?:/\d{1,2})?',nxt) and nxt not in WEEKDAYS:detail=nxt
        add_group(groups,title,v,current,detail)
    if period_index is not None:parse_period_campaigns(lines,period_index,ref,groups)
    out=list(groups.values())
    for c in out:
        c['dates'].sort();joined=' '.join(c.get('conditions',[]));c['entry_required']='要エントリー' in joined;c['target_store_limited']='対象ストア限定' in joined or '対象ストア・商品限定' in joined;c['eligibility_rule']=eligibility_rule_for(c['title'],c['target_store_limited']);c['rankable']=not c.get('informational') and not c.get('is_total')
    out.sort(key=lambda c:(c['dates'][0] if c['dates'] else '9999',c['title']));return out

def merge_safe_guide(calendar_campaigns:list[dict],guide:dict):
    out=[dict(c) for c in calendar_campaigns];index={(norm(c['title']),c.get('rate'),c.get('rate_label')):c for c in out}
    for c in guide.get('campaigns',[]):
        title=clean(c.get('title',''));rate=None;is_max=False;rate_label=None
        if 'プレミアムな日曜日' in title:rate=5.0;rate_label='+5%'
        elif 'ヤフショ感謝デー' in title:rate=5.0;is_max=True;rate_label='最大+5%'
        else:continue
        key=(norm(title),rate,rate_label);row=index.get(key)
        if row is None:
            row={'title':title,'rate':rate,'rate_label':rate_label,'is_max':is_max,'is_total':False,'informational':False,'dates':[],'conditions':[],'source':guide.get('source'),'source_url':source_url_for(title),'period':c.get('period',''),'target_store_limited':True,'eligibility_rule':'campaign_target_store','rankable':True};out.append(row);index[key]=row
        for iso in c.get('dates',[]):
            if iso not in row['dates']:row['dates'].append(iso)
        row['dates'].sort()
    out=[c for c in out if c.get('dates')];out.sort(key=lambda c:(c['dates'][0],c['title']));return out

async def collect_calendar(page,reference:date|None=None):
    result={'source':CALENDAR_URL,'campaigns':[],'errors':[]}
    try:
        resp=await page.goto(CALENDAR_URL,wait_until='domcontentloaded',timeout=45000)
        if resp and resp.status>=400:raise RuntimeError(f'HTTP {resp.status}')
        await page.wait_for_timeout(400);body=await page.locator('body').inner_text(timeout=15000);result['campaigns']=parse_calendar_text(body,reference)
        if not result['campaigns']:raise RuntimeError('No campaigns parsed from official bonus calendar')
    except Exception as e:result['errors'].append({'message':clean(repr(e))[:500]})
    return result
