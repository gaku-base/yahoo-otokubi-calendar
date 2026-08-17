from __future__ import annotations
import json,re,unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'data'/'bonus.json').read_text(encoding='utf-8'))
cat=d.get('store_catalog',[])

def norm(s):
    s=unicodedata.normalize('NFKC',s or '').lower()
    return re.sub(r'[\s\-_・･/／]+','',s)

def row(i):
    r=cat[i]
    if isinstance(r,list):
        return {'id':i,'name':r[0] if len(r)>0 else '', 'slug':r[1] if len(r)>1 else '', 'aliases':r[2] if len(r)>2 and isinstance(r[2],list) else []}
    return {'id':i,'name':r.get('name',''),'slug':r.get('slug',''),'aliases':r.get('aliases',[])}

queries=['Joshin','ジョーシン','上新','joshin','ヤマダ','ヤマダデンキ','ヤマダ電機','YAMADA']
print('VERSION',d.get('version'),'FORMAT',d.get('format'),'CATALOG',len(cat),'DAYS',len(d.get('days',[])))
for q in queries:
    nq=norm(q); found=[]
    for i in range(len(cat)):
        r=row(i); vals=[r['name'],r['slug'],*r['aliases']]
        if any(nq in norm(v) or norm(v) in nq for v in vals if v):
            dates=[]
            for day in d.get('days',[]):
                for offer in day.get('offers',[]):
                    if offer[0]==i:
                        dates.append([day.get('date'),offer[1]])
            found.append({**r,'offers':dates[:20],'offer_count':len(dates)})
    print('\nQUERY',q,'MATCHES',len(found))
    for x in found[:30]: print(json.dumps(x,ensure_ascii=False))
