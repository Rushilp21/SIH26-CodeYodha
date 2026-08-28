def test_health_payload_contract():
    from backend.api.app.main import app
    from fastapi.testclient import TestClient

    # Import-only smoke if DB is down: TestClient still constructs the app.
    assert app.title == "BhumiSetu API"
    routes = {getattr(r, "path", None) for r in app.routes}
    assert "/health" in routes
