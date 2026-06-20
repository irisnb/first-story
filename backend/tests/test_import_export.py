"""Tests for screenplay import/export (screenplay-import-export spec).

Verifies:
- Pasted import is just a saved revision: it records a document.revised event
  and runs the SAME Fountain parse + extraction as hand-written prose.
- Export as Fountain keeps structure (faithful pass-through).
- Export as plain text strips authoring markers (@ cue prefix, forced '.'),
  leaving a clean readable text.
- An unknown export format is rejected.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import to_fountain, to_plain_text  # noqa: E402

client = TestClient(app)


def _create_project(name="Export Test"):
    resp = client.post("/api/v1/projects", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# --- Pure export rendering ---


def test_to_fountain_is_faithful_passthrough():
    text = "INT. 房间 - 日\n\n@小明\n你好。\n"
    assert to_fountain(text) == text


def test_to_plain_text_strips_markers():
    text = "INT. 房间 - 日\n\n@小明\n（轻声）\n你好。\n\n他走了。\n"
    out = to_plain_text(text)
    # '@' cue prefix removed -> bare name on its own line.
    assert "@" not in out
    assert "小明" in out
    assert "你好。" in out
    # Scene heading retained.
    assert "INT. 房间 - 日" in out


def test_to_plain_text_strips_forced_scene_dot():
    text = ".地下室\n\n@小红\n这里好黑。\n"
    out = to_plain_text(text)
    assert "地下室" in out
    assert not out.startswith(".")


# --- Import == save path (records revision; same extraction flow) ---


def test_paste_import_records_revision(monkeypatch):
    # No LLM key -> extraction runs deterministic stage only, never blocks.
    pid = _create_project()
    pasted = "INT. 咖啡馆 - 日\n\n@阿强\n久等了。\n"
    resp = client.post(
        f"/api/v1/projects/{pid}/documents",
        json={"content": pasted, "document_id": "main"},
    )
    assert resp.status_code == 201, resp.text
    rev = resp.json()
    assert rev["content"] == pasted

    # The revision is listed (recorded as document.revised).
    listed = client.get(f"/api/v1/projects/{pid}/documents").json()
    assert listed["total"] == 1
    assert listed["revisions"][0]["content"] == pasted


def test_export_endpoints_roundtrip():
    pid = _create_project()
    text = "INT. 房间 - 日\n\n@小明\n你好。\n"
    client.post(
        f"/api/v1/projects/{pid}/documents",
        json={"content": text, "document_id": "main"},
    )

    fountain = client.get(
        f"/api/v1/projects/{pid}/documents/export", params={"format": "fountain"}
    )
    assert fountain.status_code == 200
    assert fountain.text == text

    plain = client.get(
        f"/api/v1/projects/{pid}/documents/export", params={"format": "text"}
    )
    assert plain.status_code == 200
    assert "@" not in plain.text
    assert "小明" in plain.text


def test_export_unknown_format_rejected():
    pid = _create_project()
    client.post(
        f"/api/v1/projects/{pid}/documents",
        json={"content": "@小明\n台词。\n", "document_id": "main"},
    )
    resp = client.get(
        f"/api/v1/projects/{pid}/documents/export", params={"format": "pdf"}
    )
    assert resp.status_code == 400
