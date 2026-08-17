from __future__ import annotations
import json,subprocess,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';DIAG=ROOT/'diagnostics';STATUS=DATA/'status.json';JST=timezone(timedelta(hours=9));SCHEMA=1;VERSION='0.8.0'
DEFAULT_COMMAND=[sys.executable,str(ROOT/'scripts'/'scrape_v086.py')]

def now_iso():return datetime.now(JST).isoformat()
def read_json(path,default=None):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:return default

def write_json_atomic(path:Path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)

def backup_bytes(path:Path):return path.read_bytes() if path.exists() else None

def restore_bytes(path:Path,data:bytes|None):
    if data is None:
        if path.exists():path.unlink()
    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

def status_from_attempt(ok:bool,attempt_bonus:dict|None,previous_bonus:dict|None,message:str='',exit_code:int=0):
    attempt_bonus=attempt_bonus or {};previous_bonus=previous_bonus or {};v=attempt_bonus.get('validation') or {};counts=v.get('counts') or {};issues=v.get('issues') or []
    return {'schema':SCHEMA,'version':VERSION,'last_attempt_at':now_iso(),'last_attempt_ok':bool(ok),'last_attempt_exit_code':int(exit_code),'message':message or ('更新成功' if ok else '最新更新に失敗したため前回正常データを使用'),'issues':issues[:20],'attempt_counts':counts,'attempt_source_updated_at':attempt_bonus.get('updated_at'),'last_good_updated_at':attempt_bonus.get('updated_at') if ok else previous_bonus.get('updated_at')}

def run(command=None):
    DATA.mkdir(exist_ok=True);DIAG.mkdir(exist_ok=True)
    bonus_path=DATA/'bonus.json';campaign_path=DATA/'campaigns.json';old_bonus_bytes=backup_bytes(bonus_path);old_campaign_bytes=backup_bytes(campaign_path);previous_bonus=read_json(bonus_path,{}) or {}
    proc=subprocess.run(command or DEFAULT_COMMAND,cwd=ROOT,text=True,capture_output=True)
    if proc.stdout:print(proc.stdout,end='')
    if proc.stderr:print(proc.stderr,end='',file=sys.stderr)
    attempt_bonus=read_json(bonus_path,{}) or {};attempt_campaign=read_json(campaign_path,{}) or {}
    valid=proc.returncode==0 and (attempt_bonus.get('validation') or {}).get('ok') is True and (attempt_campaign.get('validation') or {}).get('ok') is True
    if valid:
        st=status_from_attempt(True,attempt_bonus,previous_bonus,exit_code=proc.returncode);write_json_atomic(STATUS,st);return st
    stamp=datetime.now(JST).strftime('%Y%m%dT%H%M%S')
    if attempt_bonus:write_json_atomic(DIAG/f'{stamp}_failed_bonus.json',attempt_bonus)
    if attempt_campaign:write_json_atomic(DIAG/f'{stamp}_failed_campaigns.json',attempt_campaign)
    restore_bytes(bonus_path,old_bonus_bytes);restore_bytes(campaign_path,old_campaign_bytes)
    reason='; '.join((attempt_bonus.get('validation') or {}).get('issues') or []) or f'scraper exit {proc.returncode}'
    st=status_from_attempt(False,attempt_bonus,previous_bonus,message=f'最新更新失敗: {reason}',exit_code=proc.returncode);write_json_atomic(STATUS,st);return st

def main():
    st=run();print('REFRESH_STATUS='+json.dumps(st,ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
