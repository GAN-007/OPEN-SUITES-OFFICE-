from fastapi.testclient import TestClient

from nexus_workspace.api import app


def test_health_route_and_native_catalog() -> None:
    client = TestClient(app)

    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["storage_model"] == "vendored-source-tree"
    assert root.json()["engine_count"] == 10

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["storage_model"] == "vendored-source-tree"
    assert len(health.json()["engines"]) == 10

    native = client.get("/v1/native/engines")
    assert native.status_code == 200
    assert len(native.json()) == 10
    assert {item["engine"] for item in native.json()} == {
        "genoffice",
        "openmaic",
        "weknora",
        "graphiti",
        "cognee",
        "browser-use",
        "open-webui",
        "pageindex",
        "agent-reach",
        "qwen-audio-agent",
    }

    response = client.post("/v1/route", json={"intent": "read appendix D in this long report"})
    assert response.status_code == 200
    assert response.json()["engine"] == "pageindex"
