(()=>{
  const STATUS_URL='data/status.json';
  const WORKFLOW_URL='https://github.com/gaku-base/yahoo-otokubi-calendar/actions/workflows/refresh.yml';
  const POLL_MS=10000;
  const MAX_WAIT_MS=20*60*1000;
  let pollTimer=null;
  let startedAt=0;
  let baselineAttempt='';

  const button=document.querySelector('#manualRefreshBtn');
  const meta=document.querySelector('#refreshMeta');
  if(!button||!meta)return;

  function fmtDuration(value){
    const sec=Math.max(0,Math.round(Number(value)||0));
    if(!sec)return '未計測';
    if(sec<60)return `${sec}秒`;
    const min=Math.floor(sec/60),rest=sec%60;
    return `${min}分${String(rest).padStart(2,'0')}秒`;
  }

  function fmtTime(iso){
    if(!iso)return '未取得';
    const d=new Date(iso);
    if(Number.isNaN(d.getTime()))return '未取得';
    return d.toLocaleString('ja-JP',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'});
  }

  function setMeta(text,state=''){
    meta.textContent=text;
    meta.className=`refreshMeta${state?` ${state}`:''}`;
  }

  function publishedSummary(status,prefix=''){
    const seconds=status?.attempt_counts?.elapsed_seconds;
    const result=status?.last_attempt_ok===true?'正常':status?.last_attempt_ok===false?'失敗':'状態不明';
    const base=`最終取得: ${fmtTime(status?.last_attempt_at)} / 取得時間: ${fmtDuration(seconds)} / ${result}`;
    setMeta(prefix?`${prefix} / ${base}`:base,status?.last_attempt_ok===false?'error':'');
  }

  async function fetchStatus(){
    const r=await fetch(`${STATUS_URL}?manual=${Date.now()}`,{cache:'no-store'});
    if(!r.ok)throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  async function refreshPublishedSummary(){
    try{publishedSummary(await fetchStatus())}
    catch(e){setMeta('取得状態を確認できません','error')}
  }

  function stopPolling(){
    if(pollTimer){clearInterval(pollTimer);pollTimer=null}
    button.disabled=false;
    button.textContent='最新情報を取得';
  }

  async function pollOnce(){
    if(!startedAt)return;
    const elapsed=Math.max(0,(Date.now()-startedAt)/1000);
    if(Date.now()-startedAt>MAX_WAIT_MS){
      stopPolling();
      setMeta('更新を確認できませんでした。GitHubで「Run workflow」を実行したか確認してください。','error');
      return;
    }
    try{
      const status=await fetchStatus();
      const attempt=status?.last_attempt_at||'';
      const attemptMs=attempt?new Date(attempt).getTime():0;
      const isNew=attempt&&attempt!==baselineAttempt&&attemptMs>=startedAt-60000;
      if(isNew){
        stopPolling();
        if(status.last_attempt_ok===true){
          publishedSummary(status,'更新完了');
          if(typeof load==='function')await load();
        }else{
          publishedSummary(status,'更新失敗・前回正常データを継続');
        }
        return;
      }
      setMeta(`更新待ち… 経過 ${fmtDuration(elapsed)} / GitHub側で「Run workflow」を押すと開始します。`,'running');
    }catch(e){
      setMeta(`更新確認中… 経過 ${fmtDuration(elapsed)} / 通信状態を確認しています。`,'running');
    }
  }

  function startPolling(){
    if(pollTimer)clearInterval(pollTimer);
    pollTimer=setInterval(pollOnce,POLL_MS);
    pollOnce();
  }

  button.addEventListener('click',()=>{
    baselineAttempt=(typeof refreshStatus!=='undefined'&&refreshStatus?.last_attempt_at)||'';
    startedAt=Date.now();
    button.disabled=true;
    button.textContent='更新手順を開きました';
    setMeta('GitHub画面で「Run workflow」→「Run workflow」を押してください。戻ると完了を自動確認します。','running');
    const w=window.open(WORKFLOW_URL,'_blank');
    if(w)w.opener=null;else window.location.href=WORKFLOW_URL;
    startPolling();
  });

  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&startedAt)pollOnce()});
  document.querySelector('#refreshBtn')?.addEventListener('click',()=>setTimeout(refreshPublishedSummary,500));
  refreshPublishedSummary();
})();
