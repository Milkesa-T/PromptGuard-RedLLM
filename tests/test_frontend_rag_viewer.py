from pathlib import Path


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def test_rag_viewer_markup_is_registered():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    assert 'data-tab="rag-kb"' in html
    assert 'id="tab-rag-kb"' in html
    assert 'id="rag-doc-grid"' in html
    assert 'id="rag-chunk-modal"' in html
    assert 'id="rag-search-input"' in html
    assert 'id="rag-search-btn"' in html
    assert 'id="rag-search-clear"' in html
    assert 'id="rag-search-results"' in html
    assert '<script src="rag_viewer.js"></script>' in html


def test_rag_viewer_script_exists_and_uses_safe_dom_rendering():
    script_path = FRONTEND_DIR / "rag_viewer.js"

    assert script_path.is_file()
    script = script_path.read_text(encoding="utf-8")
    assert "/api/rag/search" in script
    assert "innerHTML" not in script
