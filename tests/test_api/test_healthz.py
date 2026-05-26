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
