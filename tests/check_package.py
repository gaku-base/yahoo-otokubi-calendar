from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1]
required=['docs/index.html','docs/styles.css','docs/core.js','docs/app.js','docs/sw.js','docs/manifest.webmanifest','docs/icon.svg','scripts/scrape.py','scripts/scrape_v066.py','scripts/scrape_v071.py','scripts/scrape_v072.py','scripts/scrape_v073.py','scripts/scrape_v074.py','scripts/scrape_v075.py','scripts/calendar_campaigns.py','scripts/compact_client_data.py','scripts/run_refresh_safe.py','data/status.json','.github/workflows/pages.yml','.github/workflows/refresh.yml','.github/workflows/smoke.yml','tests/smoke_pwa.py','tests/test_calendar_campaigns.py','tests/test_v073.py','tests/test_v074.py','tests/test_v075.py','tests/test_refresh_status.py']
for f in required: assert (root/f).exists(),f
html=(root/'docs/index.html').read_text(); assert html.index('core.js') < html.index('app.js'); assert 'class="workspace"' in html and 'class="sidePane"' in html; assert 'v0.8.1' in html and 'shopSuggestions' in html
css=(root/'docs/styles.css').read_text(); assert '@media(min-width:980px)' in css and 'grid-template-columns:minmax(0,1fr) 360px' in css; assert '.selected{' in css and '.suggestion{' in css
manifest=json.loads((root/'docs/manifest.webmanifest').read_text()); assert manifest.get('display') in ('standalone','fullscreen','minimal-ui')
sw=(root/'docs/sw.js').read_text(); assert "SHELL_CACHE='otokubi-v081'" in sw and "DATA_CACHE='otokubi-data-v1'" in sw; assert 'core.js' in sw and 'app.js' in sw; assert "u.search=''" in sw and 'cache.put(key,res.clone())' in sw and 'cache.match(key)' in sw; assert "fetch(req,{cache:'no-store'})" in sw; assert 'self.skipWaiting()' in sw and 'self.clients.claim()' in sw
app=(root/'docs/app.js').read_text(); assert 'Promise.allSettled' in app and "fetchJson('data/status.json')" in app; assert '最新取得失敗' in app and '前回正常データを使用' in app; assert 'BONUS+更新失敗（前回データを表示）' in app and 'キャンペーン更新失敗（前回データを表示）' in app; assert 'rate_label' in app and '単純加算しません' in app; assert 'searchCatalog' in app and 'shopSuggestions' in app and 'selectCandidate' in app
core=(root/'docs/core.js').read_text(); assert 'rate_label' in core and 'is_total' in core and 'safeCampaignTitle' in core; assert 'searchCatalog' in core and "'joshin'" in core and "'yamada-denki'" in core and 'ジョーシン' in core and 'ヤマダ電機' in core
status=json.loads((root/'data/status.json').read_text()); assert status.get('version')=='0.8.0' and 'last_attempt_ok' in status
refresh=(root/'.github/workflows/refresh.yml').read_text(); assert 'run_refresh_safe.py' in refresh and 'data/status.json' in refresh and 'Mark failed live refresh after status is saved' in refresh and "d.get('format')=='indexed-v1'" in refresh
pages=(root/'.github/workflows/pages.yml').read_text(); assert "d.get('version')=='0.8.0'" in pages and 'cp data/status.json docs/data/status.json' in pages
smoke=(root/'.github/workflows/smoke.yml').read_text(); assert 'cp data/status.json docs/data/status.json' in smoke
print('package integrity: PASS')
