from __future__ import annotations
import re,unicodedata
from datetime import date

GUIDE_URL='https://shopping.yahoo.co.jp/promotion/campaign/guide/'
BSPLUS_URL='https://shopping.yahoo.co.jp/promotion/campaign/bsplus/'

def clean(s:str)->str:return re.sub(r'\s+',' ',s or '').strip()
def norm(s:str)->str:return re.sub(r'[\s\-_・･/／【】\[\]〖〗]+','',unicodedata.normalize('NFKC',s or '').lower())

def _target_kind(title:str):
    n=norm(title)
    if 'ボーナスストアplus' in n and 'さらに+2%' in n:return 'plus2'
    if 'ボーナスストアplus' in n and '優良ストア' in n and ('+3%' in n or 'さらに3%' in n):return 'plus3'
    return None

def _dates(lines:list[str]):
    out=[]
    for line in lines:
        for y,m,d in re.findall(r'(20\d{2})\s*[/年]\s*(\d{1,2})\s*[/月]\s*(\d{1,2})\s*日?',unicodedata.normalize('NFKC',line)):
            try:x=date(int(y),int(m),int(d))
            except ValueError:continue
            if x not in out:out.append(x)
    return sorted(out)

def _number_after(label:str,lines:list[str]):
    for line in lines:
        if not line.startswith(label):continue
        m=re.search(r'([0-9,]+(?:\.\d+)?)\s*(?:円相当|円|%|％)',unicodedata.normalize('NFKC',line))
        if m:return float(m.group(1).replace(',',''))
    return None

def _rate(lines:list[str],fallback:float):
    for line in lines:
        if not line.startswith('付与率'):continue
        m=re.search(r'(\d{1,2}(?:\.\d+)?)\s*[%％]',unicodedata.normalize('NFKC',line))
        if m:return float(m.group(1))
    return fallback

def _minimum(lines:list[str]):
    for line in lines:
        if '円以上' not in line or '決済' not in line:continue
        m=re.search(r'([0-9,]+)\s*円以上',unicodedata.normalize('NFKC',line))
        if m:return int(m.group(1).replace(',',''))
    return 0

def parse_target_guide(text:str):
    lines=[clean(x) for x in (text or '').splitlines() if clean(x)];groups={}
    for i,title in enumerate(lines):
        kind=_target_kind(title)
        if not kind:continue
        block=[]
        for j in range(i+1,min(i+32,len(lines))):
            if j>i+2 and _target_kind(lines[j]):break
            block.append(lines[j])
            if len(block)>8 and lines[j].startswith('※日程'):break
        dates=[d.isoformat() for d in _dates(block)]
        if not dates:continue
        fallback=2.0 if kind=='plus2' else 3.0;rate=_rate(block,fallback);cap=_number_after('付与上限',block);minimum=_minimum(block)
        conditions=[]
        if minimum:conditions.append(f'注文{minimum:,}円～')
        if cap is not None:conditions.append(f'付与上限{int(cap):,}円相当')
        if any('エントリー' in x for x in block):conditions.append('要エントリー')
        target=any(x.startswith('対象ストア') and ('指定あり' in x or '対象' in x) for x in block)
        if target:conditions.append('対象ストア限定')
        canonical='ボーナスストアPlusでさらに+2%' if kind=='plus2' else 'ボーナスストアPlus 優良ストアでさらに+3%'
        row=groups.get(kind)
        if row is None:
            row={'title':canonical,'rate':rate,'rate_label':f'+{rate:g}%','is_max':False,'is_total':False,'informational':False,'rankable':True,'dates':[],'conditions':[],'source':GUIDE_URL,'source_url':BSPLUS_URL,'entry_required':False,'target_store_limited':False,'eligibility_rule':'bonus_plus_member' if kind=='plus2' else 'preferred_bonus_store'};groups[kind]=row
        if float(row.get('rate'))!=float(rate):continue
        row['dates']=sorted(set(row['dates']+dates));row['conditions']=list(dict.fromkeys(row['conditions']+conditions));row['entry_required']=bool(row['entry_required'] or ('要エントリー' in conditions));row['target_store_limited']=bool(row['target_store_limited'] or target)
    return sorted(groups.values(),key=lambda r:((r.get('dates') or ['9999'])[0],r['title']))

def _kind_row(row:dict):return _target_kind(str(row.get('title') or ''))

def merge_target_guide(rows:list[dict],guide_rows:list[dict]):
    out=[dict(r) for r in rows]
    for g in guide_rows:
        kind=_kind_row(g)
        if not kind:continue
        target=next((r for r in out if _kind_row(r)==kind),None)
        if target is None:
            target=dict(g);out.append(target)
        else:
            tr=target.get('rate');gr=g.get('rate')
            if tr is not None and gr is not None and float(tr)!=float(gr):continue
            target['dates']=sorted(set((target.get('dates') or [])+(g.get('dates') or [])));target['conditions']=list(dict.fromkeys((target.get('conditions') or [])+(g.get('conditions') or [])));target['entry_required']=bool(target.get('entry_required') or g.get('entry_required'));target['target_store_limited']=bool(target.get('target_store_limited') or g.get('target_store_limited'))
            if target.get('rate') is None:target['rate']=g.get('rate')
            if not target.get('rate_label'):target['rate_label']=g.get('rate_label')
            target['schedule_source']=GUIDE_URL;target['informational']=False;target['rankable']=True;target['eligibility_rule']='bonus_plus_member' if kind=='plus2' else 'preferred_bonus_store';target.setdefault('source_url',BSPLUS_URL)
    out.sort(key=lambda r:((r.get('dates') or ['9999'])[0],str(r.get('title') or '')))
    return out

async def collect_target_guide(page):
    result={'source':GUIDE_URL,'campaigns':[],'errors':[]}
    try:
        resp=await page.goto(GUIDE_URL,wait_until='domcontentloaded',timeout=45000)
        if resp and resp.status>=400:raise RuntimeError(f'HTTP {resp.status}')
        await page.wait_for_timeout(300);text=await page.locator('body').inner_text(timeout=15000);rows=parse_target_guide(text);expected={_target_kind(x) for x in text.splitlines() if _target_kind(x)};actual={_kind_row(x) for x in rows}
        if expected-actual:raise RuntimeError(f'guide parser missed BONUS+ schedule sections: {sorted(expected-actual)}')
        result['campaigns']=rows
    except Exception as e:result['errors'].append({'message':clean(repr(e))[:500]})
    return result
