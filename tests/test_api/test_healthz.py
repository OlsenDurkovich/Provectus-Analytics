from fastapi.testclient import TestClient

from provectus_analytics.api import create_app


def test_healthz_returns_ok():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_frontend_index():
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text


def test_spa_deep_link_returns_index():
    """Deep links like /ratings/IFR must serve index.html so React Router can resolve client-side."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/ratings/IFR")
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text


def test_spa_fallback_does_not_swallow_api_404():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/this-does-not-exist")
    assert response.status_code == 404
