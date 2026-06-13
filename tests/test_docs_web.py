from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docs_web.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient instance for FastAPI app."""
    return TestClient(app)


def test_root_redirect(client: TestClient) -> None:
    """Test that root route redirects to quickstart guide."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs/quickstart"


def test_docs_page_rendering(client: TestClient) -> None:
    """Test rendering a valid documentation page."""
    response = client.get("/docs/quickstart")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Quickstart" in response.text
    assert "Installation" in response.text


def test_docs_page_not_found(client: TestClient) -> None:
    """Test 404 error rendering for a non-existent page."""
    response = client.get("/docs/non-existent-page")
    assert response.status_code == 404
    assert "page not found" in response.text.lower()


def test_docs_search_empty(client: TestClient) -> None:
    """Test search endpoint with empty query."""
    response = client.get("/docs/search?q=")
    assert response.status_code == 200
    assert response.json() == []


def test_docs_search_results(client: TestClient) -> None:
    """Test search endpoint returns matches with snippets."""
    response = client.get("/docs/search?q=config")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)

    # We expect some results since docs contain 'config'
    if results:
        for item in results:
            assert "title" in item
            assert "url" in item
            assert "snippets" in item
            assert item["url"].startswith("/docs/")
            for snippet in item["snippets"]:
                assert "<mark>" in snippet.lower()
                assert "config" in snippet.lower()


def test_static_files_serving(client: TestClient) -> None:
    """Test serving static files (CSS, JS)."""
    response_css = client.get("/static/css/style.css")
    assert response_css.status_code == 200
    assert "text/css" in response_css.headers["content-type"]

    response_js = client.get("/static/js/main.js")
    assert response_js.status_code == 200
    assert "javascript" in response_js.headers["content-type"]


def test_rewrite_md_links() -> None:
    """Test rewrite_md_links helper function."""
    from docs_web.main import rewrite_md_links

    # Double quote
    html = '<p>See <a href="user-guide.md">User Guide</a> for details.</p>'
    expected = '<p>See <a href="/docs/user-guide">User Guide</a> for details.</p>'
    assert rewrite_md_links(html) == expected

    # Single quote
    html = "<p>See <a href='user-guide.md'>User Guide</a> for details.</p>"
    expected = "<p>See <a href='/docs/user-guide'>User Guide</a> for details.</p>"
    assert rewrite_md_links(html) == expected

    # Link with anchor
    html = '<p>See <a href="configuration.md#naming_pattern">Naming Pattern</a>.</p>'
    expected = (
        '<p>See <a href="/docs/configuration#naming_pattern">Naming Pattern</a>.</p>'
    )
    assert rewrite_md_links(html) == expected

    # Link to parent README
    html = '<p>See <a href="../README.md">Readme</a>.</p>'
    expected = '<p>See <a href="/docs/readme">Readme</a>.</p>'
    assert rewrite_md_links(html) == expected

    # External link (should NOT be rewritten)
    html = '<p>Visit <a href="https://example.com/user-guide.md">External</a>.</p>'
    assert rewrite_md_links(html) == html
