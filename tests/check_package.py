from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1]
required=['docs/index.html','docs/styles.css','docs/core.js','docs/app.js','docs/sw.js','docs/manifest.webmanifest','docs/icon.svg','scripts/scrape.py','scripts/scrape_v066.py','scripts/scrape_v071.py','scripts/scrape_v072.py','scripts/scrape_v073.py','scripts/calendar_campaigns.py','scripts/compact_client_data.py','.github/workflows/pages.yml','.github/workflows/refresh.yml','.github/workflows/smoke.yml','tests/smoke_pwa.py','tests/test_calendar_campaigns.py','tests/test_v073.py']
for f in required: assert (root/f).exists(),f
html=(root/'docs/index.html').read_text(); assert html.index('core.js') < html.index('app.js'); assert 'class="workspace"' in html and 'class="sidePane"' in html; assert 'v0.7.3' in html
css=(root/'docs/styles.css').read_text(); assert '@media(min-width:980px)' in css and 'grid-template-columns:minmax(0,1fr) 360px' in css; assert '.selected{' in css
manifest=json.loads((root/'docs/manifest.webmanifest').read_text()); assert manifest.get('display') in ('standalone','fullscreen','minimal-ui')
sw=(root/'docs/sw.js').read_text(); assert "SHELL_CACHE='otokubi-v073'" in sw and "DATA_CACHE='otokubi-data-v1'" in sw; assert 'core.js' in sw and 'app.js' in sw; assert "u.search=''" in sw and 'cache.put(key,res.clone())' in sw and 'cache.match(key)' in sw; assert "fetch(req,{cache:'no-store'})" in sw; assert 'self.skipWaiting()' in sw and 'self.clients.claim()' in sw
app=(root/'docs/app.js').read_text(); assert 'Promise.allSettled' in app; assert 'BONUS+更新失敗（前回データを表示）' in app; assert 'キャンペーン更新失敗（前回データを表示）' in app; assert 'rate_label' in app and '単純加算しません' in app
core=(root/'docs/core.js').read_text(); assert 'rate_label' in core and 'is_total' in core and 'safeCampaignTitle' in core
refresh=(root/'.github/workflows/refresh.yml').read_text(); assert 'scrape_v073.py' in refresh and "d.get('version')=='0.7.3'" in refresh and "counts.get('count_warnings')==0" in refresh
pages=(root/'.github/workflows/pages.yml').read_text(); assert "d.get('version')=='0.7.3'" in pages and "counts.get('count_warnings')==0" in pages
print('package integrity: PASS')
