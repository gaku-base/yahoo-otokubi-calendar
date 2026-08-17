import importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'scripts'
if str(S) not in sys.path:sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('scrape_v074',S/'scrape_v074.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def opt(text,index=1,disabled=False):return {'text':text,'index':index,'value':str(index),'disabled':disabled}

def test_counted_options_are_not_unparsed():
    assert not m.meaningful_unparsed_option(opt('家電（123）'))
    assert not m.meaningful_unparsed_option(opt('食品 (0)'))

def test_placeholders_without_counts_are_ignored():
    for s in ('すべて','全て','全カテゴリ','すべてのカテゴリ','カテゴリーを選択','カテゴリを選択','選択してください'):
        assert not m.meaningful_unparsed_option(opt(s))

def test_real_category_without_count_is_audit_issue_candidate():
    assert m.meaningful_unparsed_option(opt('家電・AV機器'))
    assert m.meaningful_unparsed_option(opt('ファッション'))

def test_disabled_option_is_ignored():
    assert not m.meaningful_unparsed_option(opt('家電・AV機器',disabled=True))

def test_source_fails_closed_when_audit_issue_exists():
    src=(S/'scrape_v074.py').read_text(encoding='utf-8')
    assert "rec['status']='partial'" in src
    assert 'could not be audited' in src
    assert "'category_audit_issues':audit_issues" in src
