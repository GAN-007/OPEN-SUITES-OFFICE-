from fastapi.testclient import TestClient

from nexus_workspace.api import app


def test_health_and_route() -> None:
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    response = client.post("/v1/route", json={"intent": "read appendix D in this long report"})
    assert response.status_code == 200
    assert response.json()["engine"] == "pageindex"
