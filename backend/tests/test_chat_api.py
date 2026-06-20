"""Tests for the chat / adopt / style-memo API (tasks group 7).

Runs against the real FastAPI app via TestClient. The autouse ``_no_real_llm``
fixture blanks the LLM key, so the chat endpoint exercises the graceful no-LLM
path; the adopt and style-memo endpoints are fully deterministic and tested
end-to-end (idempotency, append-to-end, archive-not-delete).
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app  # noqa: E402

API = "/api/v1"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def project_id(client):
    resp = client.post(f"{API}/projects", json={"name": "Chat API Test"})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_chat_no_llm_returns_contract(client, project_id):
    """Without an LLM key, /chat still returns the full contract, no key leak."""
    resp = client.post(f"{API}/projects/{project_id}/chat", json={"message": "你好"})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == {"reply", "message_id", "intent", "extraction_status"}
    assert data["intent"] == "ignore"
    assert data["extraction_status"] == "skipped_no_llm"
    # No evidence fields, no key.
    assert "evidence" not in data
    assert "api_key" not in str(data).lower()


def test_chat_unknown_project_404(client):
    resp = client.post(f"{API}/projects/nope/chat", json={"message": "hi"})
    assert resp.status_code == 404


def test_adopt_appends_to_end_and_is_idempotent(client, project_id):
    # First save some manuscript content via the documents endpoint.
    client.post(
        f"{API}/projects/{project_id}/documents",
        json={"content": "第一段。", "document_id": "main"},
    )
    body = {
        "content": "采纳进来的第二段。",
        "adopt_request_id": "adopt_req_1",
        "adopted_from_message_id": "msg_abc",
    }
    r1 = client.post(f"{API}/projects/{project_id}/manuscript/adopt", json=body)
    assert r1.status_code == 200
    assert r1.json()["duplicate"] is False

    # Double-click: same adopt_request_id -> recognized duplicate, no re-append.
    r2 = client.post(f"{API}/projects/{project_id}/manuscript/adopt", json=body)
    assert r2.status_code == 200
    assert r2.json()["duplicate"] is True

    # Manuscript should contain both segments, appended once.
    export = client.get(
        f"{API}/projects/{project_id}/documents/export", params={"format": "text"}
    )
    text = export.text
    assert "第一段。" in text
    assert text.count("采纳进来的第二段。") == 1


def test_adopt_records_manuscript_adopted_event(client, project_id):
    body = {
        "content": "唯一一段。",
        "adopt_request_id": "adopt_req_evt",
        "adopted_from_message_id": "msg_xyz",
    }
    client.post(f"{API}/projects/{project_id}/manuscript/adopt", json=body)
    events = client.get(f"{API}/projects/{project_id}/events").json()
    types = [e["type"] for e in events["events"]]
    assert "manuscript.adopted" in types
    adopted = next(e for e in events["events"] if e["type"] == "manuscript.adopted")
    assert adopted["payload"]["adopted_from_message_id"] == "msg_xyz"


def test_style_memo_add_list_archive(client, project_id):
    # Add (no kind -> defaults to 未分类).
    add = client.post(
        f"{API}/projects/{project_id}/style-memos",
        json={"text": "动画+collage 拼贴感"},
    )
    assert add.status_code == 201
    memo = add.json()
    assert memo["kind"] == "未分类"
    assert memo["status"] == "active"
    memo_id = memo["id"]

    # List shows it.
    listed = client.get(f"{API}/projects/{project_id}/style-memos").json()
    assert any(m["id"] == memo_id for m in listed["memos"])

    # Archive -> status archived, still present (not deleted).
    arch = client.post(f"{API}/projects/{project_id}/style-memos/{memo_id}/archive")
    assert arch.status_code == 200
    assert arch.json()["status"] == "archived"
    listed2 = client.get(f"{API}/projects/{project_id}/style-memos").json()
    found = next(m for m in listed2["memos"] if m["id"] == memo_id)
    assert found["status"] == "archived"
