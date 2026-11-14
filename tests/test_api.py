from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from aulalocale.app import create_app

TOKEN = "local-test-token-" * 3
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def test_subject_persists_across_restart(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post("/api/v1/subjects", headers=HEADERS,
                               json={"title": " Farmacologia ", "description": "Corso"})
        assert response.status_code == 201
        subject = response.json()
        assert subject["title"] == "Farmacologia"
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        assert client.get("/api/v1/subjects", headers=HEADERS).json() == [subject]
        assert client.get(f"/api/v1/subjects/{subject['id']}", headers=HEADERS).json() == subject
        assert client.get(f"/api/v1/subjects/{uuid4()}", headers=HEADERS).status_code == 404


def test_rejects_unauthenticated_read_and_write(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        for headers in [{}, {"Authorization": "Bearer incorrect"}]:
            assert client.get("/api/v1/subjects", headers=headers).status_code == 401
            assert client.post("/api/v1/subjects", headers=headers, json={"title": "Private"}).status_code == 401
        assert client.get("/api/v1/subjects", headers=HEADERS).json() == []


@pytest.mark.parametrize("payload", [{"title": "  "}, {"title": "x" * 201},
                                     {"title": "Valid", "unexpected": True}])
def test_invalid_input_not_persisted(tmp_path, payload):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        assert client.post("/api/v1/subjects", headers=HEADERS, json=payload).status_code == 422
        assert client.get("/api/v1/subjects", headers=HEADERS).json() == []


def test_pagination(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        for title in ["One", "Two"]:
            client.post("/api/v1/subjects", headers=HEADERS, json={"title": title})
        response = client.get("/api/v1/subjects?limit=1&offset=1", headers=HEADERS)
        assert [item["title"] for item in response.json()] == ["Two"]
        assert client.get("/api/v1/subjects?limit=0", headers=HEADERS).status_code == 422


def test_missing_token_fails_startup(tmp_path):
    with pytest.raises(RuntimeError):
        with TestClient(create_app(tmp_path, "")):
            pass
