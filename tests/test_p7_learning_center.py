"""P7 training page static acceptance and guardrail smoke. No company data."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_p7_server_routed_and_nocache():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"/learning/center":"learning"' in app
    assert '@app.get("/learning/center",response_class=HTMLResponse,include_in_schema=False)' in app
    assert 'if request.url.path in PAGE_ROUTES' in app

def test_p7_role_bounded_and_no_persisted_quiz():
    ui = (ROOT / "rich_ui.py").read_text(encoding="utf-8")
    segment = ui.split("function trainingCenter(){", 1)[1].split("async function users(){", 1)[0]
    assert 'admin:' in segment and 'sales:' in segment
    assert 'technical:' in segment and 'manager:' in segment and 'gudang:' in segment
    assert 'p7quiz' in segment and 'new FormData(form)' in segment
    assert 'Skor latihan di browser' in segment
    assert 'UAT otomatis menjadi gold label' in segment
    assert 'AI-02 online BM25' in segment
    assert 'api(' not in segment  # no network call to persist quiz answers
