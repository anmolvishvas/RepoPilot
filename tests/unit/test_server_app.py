"""Unit tests for the FastAPI Gateway and streaming routes."""

from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from repopilot.agents.state import DiffHunk, MigrationPhase
from repopilot.server.app import create_app
from repopilot.server.event_broadcaster import EventBroadcaster


def test_health_check() -> None:
    app = create_app()
    client = TestClient(app)

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "uptime_seconds" in data


def test_create_migration_nonexistent_repo() -> None:
    app = create_app()
    client = TestClient(app)

    payload = {
        "repo_path": "/path/does/not/exist",
        "recipe": "sync-to-async",
    }
    resp = client.post("/api/v1/migrations", json=payload)
    assert resp.status_code == 400
    assert "does not exist" in resp.json()["detail"]


def test_create_and_get_migration(tmp_path: Path) -> None:
    mock_broadcaster = MagicMock(spec=EventBroadcaster)
    mock_graph = MagicMock()
    mock_compiled = MagicMock()
    mock_compiled.invoke.return_value = {
        "task_id": "test_t1",
        "repo_path": str(tmp_path),
        "recipe": "sync-to-async",
        "phase": MigrationPhase.VERIFIED.value,
        "is_terminal": True,
        "retry_count": 0,
        "patches": [],
        "tool_traces": [],
    }
    mock_graph.return_value = mock_compiled

    app = create_app(broadcaster=mock_broadcaster, graph_factory=mock_graph)
    client = TestClient(app)

    payload = {
        "repo_path": str(tmp_path),
        "recipe": "sync-to-async",
        "max_retries": 2,
    }
    resp = client.post("/api/v1/migrations", json=payload)
    assert resp.status_code == 202
    summary = resp.json()
    task_id = summary["task_id"]
    assert summary["phase"] == MigrationPhase.INITIALIZE.value

    # Query snapshot
    get_resp = client.get(f"/api/v1/migrations/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["task_id"] == task_id


def test_get_migration_404() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/v1/migrations/missing_task_id")
    assert resp.status_code == 404


def test_approve_migration_rejection(tmp_path: Path) -> None:
    app = create_app()
    client = TestClient(app)

    payload_create = {"repo_path": str(tmp_path), "recipe": "test"}
    resp = client.post("/api/v1/migrations", json=payload_create)
    task_id = resp.json()["task_id"]

    reject_resp = client.post(
        f"/api/v1/migrations/{task_id}/approve",
        json={"approved": False, "comment": "Not approved"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"


def test_approve_migration_landing(tmp_path: Path) -> None:
    target_file = tmp_path / "hello.py"
    target_file.write_text("def run():\n    return 1\n", encoding="utf-8")

    app = create_app()
    client = TestClient(app)

    # Create task
    payload = {"repo_path": str(tmp_path), "recipe": "sync-to-async"}
    resp = client.post("/api/v1/migrations", json=payload)
    task_id = resp.json()["task_id"]

    # Inject patch to state
    patch_str = "--- a/hello.py\n+++ b/hello.py\n@@ -1,2 +1,2 @@\n def run():\n-    return 1\n+    return 2\n"
    patch_hunk = DiffHunk(file_path="hello.py", diff_text=patch_str)
    app.state.tasks[task_id] = app.state.tasks[task_id].model_copy(update={"patches": [patch_hunk]})

    # Verify landing via approve endpoint
    approve_resp = client.post(
        f"/api/v1/migrations/{task_id}/approve",
        json={"approved": True, "operator": "lead_architect"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "landed"
    assert "hello.py" in approve_resp.json()["applied_files"]
    assert "return 2" in target_file.read_text(encoding="utf-8")
