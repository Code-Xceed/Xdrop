"""Regression tests for the cross-NLE import path.

The bug these cover: an import was reported as successful as soon as Xdrop had
*broadcast* the request, whether or not anything was listening. Premiere Pro sitting
open with the Xdrop panel closed (or Resolve simply not running) therefore produced a
green "Imported" badge and a `premiere_imported = 1` row while no clip ever reached the
project. A download finishing with the editor closed was also dropped outright, even
though the service promises to import it once the editor is opened.

Everything here goes through the same interface the CEP panel and the companion UI use:
the HTTP API plus the queue manager's event stream.
"""

import asyncio
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Runs the real FastAPI app (lifespan included) against the throwaway database.

    Module scoped on purpose: the queue manager is a process-wide singleton whose
    asyncio.Queue binds to the event loop of the first run, so every request must go
    through a single app instance.
    """
    from xdrop.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def fresh_editor_state(client):
    """Each test starts with no panel attached, no backlog and no leftover bookkeeping."""
    from xdrop.aftereffects import get_aftereffects_bridge
    from xdrop.audition import get_audition_bridge
    from xdrop.database import get_db_connection
    from xdrop.download_queue import get_queue_manager
    from xdrop.premiere import get_premiere_bridge

    for bridge in (get_premiere_bridge(), get_aftereffects_bridge(), get_audition_bridge()):
        bridge._last_heartbeat = None
        bridge._last_heartbeat_time = None
        bridge._pending_requests.clear()

    qm = get_queue_manager()
    qm._flush_attempted.clear()

    with get_db_connection() as conn:
        conn.execute("DELETE FROM downloads")
        conn.execute("DELETE FROM assets")

    yield


@pytest.fixture(autouse=True)
def no_resolve_or_ffmpeg(monkeypatch):
    """Pins the two environment-dependent inputs so assertions mean the same thing everywhere.

    - DaVinci Resolve availability shells out to the OS process list, so a developer with
      Resolve open would otherwise change the outcome.
    - `ensure_nle_compatible` may invoke ffprobe; the codec pass is orthogonal to the
      import bookkeeping under test, so it is stubbed to a no-op.
    """
    from xdrop.processor import ffmpeg as ffmpeg_module
    from xdrop.resolve import get_resolve_bridge

    monkeypatch.setattr(get_resolve_bridge(), "is_running", lambda: False)

    class _PassthroughFfmpeg:
        def ensure_nle_compatible(self, file_path, target_format="mp4"):
            return True, file_path, None

    monkeypatch.setattr(
        ffmpeg_module, "get_ffmpeg_processor", lambda *a, **k: _PassthroughFfmpeg()
    )


@pytest.fixture()
def panel_events():
    """Captures the queue manager's broadcast stream the way the WebSocket service does."""
    from xdrop.download_queue import get_queue_manager

    captured = []

    async def spy(message):
        captured.append(message)

    qm = get_queue_manager()
    qm.subscribe(spy)
    try:
        yield captured
    finally:
        qm.unsubscribe(spy)


@pytest.fixture()
def saved_job(client, tmp_path):
    """A completed download with a real file on disk, as the queue would have left it."""
    from xdrop.database import insert_download

    media = tmp_path / "clip.mp4"
    media.write_bytes(b"\x00" * 64)

    job_id = f"dl_{uuid.uuid4().hex[:8]}"
    insert_download({
        "id": job_id,
        "source_url": "https://example.com/watch?v=1",
        "platform": "youtube",
        "title": "Test Clip",
        "media_type": "video",
        "format": "mp4",
        "quality_label": "1080p",
        "status": "completed",
        "output_file_path": str(media),
    })
    return job_id, str(media)


def run(coro):
    return asyncio.run(coro)


def request_id_for(events, event_type):
    payloads = [e["payload"] for e in events if e["type"] == event_type]
    assert payloads, f"no {event_type} was broadcast"
    return payloads[-1]["requestId"]


def job_json(client, job_id):
    response = client.get(f"/api/downloads/{job_id}")
    assert response.status_code == 200
    return response.json()


# ----------------------------------------------------------------- status reporting ---


def test_premiere_status_is_honest_about_a_closed_panel(client):
    """The host process alone must not be presented as a usable import target."""
    status = client.get("/api/premiere/status").json()

    assert status["panelAttached"] is False
    if status["isAvailable"]:
        # Premiere is running but the panel was never opened: say so.
        assert "Extensions" in (status["error"] or "")


def test_heartbeat_attaches_the_panel(client):
    client.post("/api/premiere/heartbeat", json={"currentProject": "My Project"})

    status = client.get("/api/premiere/status").json()
    assert status["panelAttached"] is True
    assert status["currentProject"] == "My Project"


def test_aftereffects_heartbeat_is_tracked_separately(client):
    client.post("/api/aftereffects/heartbeat", json={"currentProject": "My Comp"})

    assert client.get("/api/aftereffects/status").json()["panelAttached"] is True
    assert client.get("/api/premiere/status").json()["panelAttached"] is False
    assert client.get("/api/audition/status").json()["panelAttached"] is False


def test_audition_heartbeat_is_tracked_separately(client):
    client.post("/api/audition/heartbeat", json={"currentProject": "Audio Session"})

    assert client.get("/api/audition/status").json()["panelAttached"] is True
    assert client.get("/api/premiere/status").json()["panelAttached"] is False
    assert client.get("/api/aftereffects/status").json()["panelAttached"] is False


# ----------------------------------------------------------- refusing false success ---


def test_manual_import_refuses_when_panel_is_closed(client, saved_job, panel_events):
    """The old code returned `success: true` here and marked the job imported."""
    job_id, _ = saved_job

    response = client.post(f"/api/downloads/{job_id}/import-premiere").json()

    assert response["success"] is False
    assert "Extensions" in response["error"]

    job = job_json(client, job_id)
    assert job["premiere_imported"] is False
    assert job["premiereImportPending"] is False

    assert not [e for e in panel_events if e["type"] == "PREMIERE_IMPORT_REQUEST"]


def test_manual_import_audition_refuses_when_panel_is_closed(client, saved_job, panel_events):
    job_id, _ = saved_job

    response = client.post(f"/api/downloads/{job_id}/import-audition").json()

    assert response["success"] is False
    assert "Extensions" in response["error"]

    job = job_json(client, job_id)
    assert job["audition_imported"] is False
    assert job["auditionImportPending"] is False

    assert not [e for e in panel_events if e["type"] == "AUDITION_IMPORT_REQUEST"]


def test_bridge_declines_to_hand_work_to_an_absent_panel(saved_job, panel_events):
    from xdrop.premiere import get_premiere_bridge

    job_id, media = saved_job
    result = run(get_premiere_bridge().import_media([media], "Xdrop", [job_id]))

    assert result["success"] is False
    assert result["confirmed"] is False
    assert result["requestId"] is None
    assert panel_events == []


# ------------------------------------------------------- delivery vs. confirmation ---


def test_delivered_import_is_not_reported_as_imported_until_the_panel_confirms(
    client, saved_job, panel_events
):
    job_id, _ = saved_job
    client.post("/api/premiere/heartbeat", json={"currentProject": "My Project"})

    delivered = client.post(f"/api/downloads/{job_id}/import-premiere").json()

    assert delivered["success"] is True
    assert delivered["confirmed"] is False, "a delivered request is not a landed clip"

    # Handed to the panel, but nothing has landed in the project yet.
    job = job_json(client, job_id)
    assert job["premiere_imported"] is False
    assert job["premiereImportPending"] is True

    request_id = request_id_for(panel_events, "PREMIERE_IMPORT_REQUEST")
    confirmed = client.post(
        "/api/premiere/import-result",
        json={"requestId": request_id, "success": True, "clipName": "clip.mp4", "binName": "Xdrop"},
    ).json()

    assert confirmed["success"] is True
    assert confirmed["confirmed"] is True

    job = job_json(client, job_id)
    assert job["premiere_imported"] is True
    assert job["premiereImportPending"] is False
    assert job["premiereImportError"] is None
    assert job["premiereBin"] == "Xdrop"


def test_panel_failure_keeps_the_job_pending_and_records_the_reason(
    client, saved_job, panel_events
):
    job_id, _ = saved_job
    client.post("/api/premiere/heartbeat", json={"currentProject": "My Project"})
    client.post(f"/api/downloads/{job_id}/import-premiere")

    request_id = request_id_for(panel_events, "PREMIERE_IMPORT_REQUEST")
    client.post(
        "/api/premiere/import-result",
        json={"requestId": request_id, "success": False, "error": "No project is open in Premiere Pro."},
    )

    job = job_json(client, job_id)
    assert job["premiere_imported"] is False
    assert job["premiereImportPending"] is True, "a failed import must stay retryable"
    assert "No project is open" in job["premiereImportError"]


def test_import_result_for_an_unknown_request_is_rejected(client):
    result = client.post(
        "/api/premiere/import-result",
        json={"requestId": "imp_does_not_exist", "success": True},
    ).json()

    assert result["success"] is False
    assert "Unknown" in result["error"]


# -------------------------------------------------------- deferral while closed off ---


def test_import_is_deferred_to_the_preferred_editor_when_nothing_is_open(client, saved_job):
    """The documented promise: with every editor closed the clip waits instead of vanishing."""
    from xdrop.config import AppSettingsModel
    from xdrop.database import get_settings_from_db
    from xdrop.download_queue import CreateDownloadRequest, get_queue_manager

    job_id, media = saved_job
    settings = AppSettingsModel(**get_settings_from_db())
    request = CreateDownloadRequest(
        source_url="https://example.com/watch?v=1",
        asset_id="video_1080p",
        format="mp4",
        quality_label="1080p",
        media_type="video",
        title="Test Clip",
    )

    summary = run(get_queue_manager().run_editor_imports(job_id, media, request, settings))

    assert len(summary) == 1
    assert summary[0]["deferred"] is True
    # Resolve leads the preference order, so it is the editor the clip waits for.
    assert summary[0]["editor"] == "resolve"

    job = job_json(client, job_id)
    assert job["resolve_imported"] is False
    assert job["resolveImportPending"] is True
    assert "DaVinci Resolve" in job["resolveImportError"]


def test_flush_does_nothing_while_the_editor_is_still_closed(client, saved_job):
    from xdrop.database import update_download_import_state
    from xdrop.download_queue import get_queue_manager

    job_id, _ = saved_job
    update_download_import_state(job_id, "premiere", pending=True, error="panel closed")

    assert run(get_queue_manager().flush_pending_imports()) == []

    assert job_json(client, job_id)["premiereImportPending"] is True


def test_flush_imports_the_backlog_once_the_editor_opens(client, saved_job, panel_events):
    from xdrop.database import update_download_import_state
    from xdrop.download_queue import get_queue_manager

    job_id, media = saved_job
    update_download_import_state(job_id, "premiere", pending=True, error="panel closed")

    qm = get_queue_manager()
    assert run(qm.flush_pending_imports()) == []

    # The user opens the Xdrop panel in Premiere Pro.
    client.post("/api/premiere/heartbeat", json={"currentProject": "My Project"})

    results = run(qm.flush_pending_imports())
    assert len(results) == 1
    assert results[0]["jobId"] == job_id
    assert results[0]["editor"] == "premiere"

    # The file the panel was asked to import is the one on disk.
    request = [e["payload"] for e in panel_events if e["type"] == "PREMIERE_IMPORT_REQUEST"][-1]
    assert request["filePaths"] == [media]
    assert job_id in request["jobIds"]

    client.post(
        "/api/premiere/import-result",
        json={"requestId": request["requestId"], "success": True, "clipName": "clip.mp4", "binName": "Xdrop"},
    )

    job = job_json(client, job_id)
    assert job["premiere_imported"] is True
    assert job["premiereImportPending"] is False


def test_a_failing_import_is_not_retried_forever_in_the_background(client, saved_job, panel_events):
    from xdrop.database import update_download_import_state
    from xdrop.download_queue import get_queue_manager

    job_id, _ = saved_job
    update_download_import_state(job_id, "aftereffects", pending=True, error="panel closed")
    client.post("/api/aftereffects/heartbeat", json={"currentProject": "My Comp"})

    qm = get_queue_manager()
    first = run(qm.flush_pending_imports())
    assert [r["jobId"] for r in first] == [job_id]

    # The panel never answers, so the job stays pending — but it is not re-sent in a loop.
    before = len(panel_events)
    assert run(qm.flush_pending_imports()) == []
    assert len(panel_events) == before

    # An explicit user retry is still allowed through.
    assert [r["jobId"] for r in run(qm.flush_pending_imports(force=True))] == [job_id]


def test_pending_imports_endpoint_lists_the_backlog(client, saved_job):
    from xdrop.database import update_download_import_state

    job_id, _ = saved_job
    update_download_import_state(job_id, "resolve", pending=True, error="Resolve closed")

    pending = client.get("/api/editors/pending-imports").json()

    assert [j["id"] for j in pending["resolve"]] == [job_id]
    assert pending["premiere"] == []
    assert pending["aftereffects"] == []
    assert pending["audition"] == []


# ------------------------------------------------------------------ target selection ---


def test_explicit_per_job_target_beats_the_auto_setting(client):
    from xdrop.config import AppSettingsModel
    from xdrop.database import get_settings_from_db
    from xdrop.download_queue import CreateDownloadRequest, get_queue_manager

    settings = AppSettingsModel(**get_settings_from_db())
    qm = get_queue_manager()

    def request(**overrides):
        base = {
            "source_url": "https://example.com/v",
            "asset_id": "video_1080p",
            "format": "mp4",
            "quality_label": "1080p",
            "media_type": "video",
            "title": "t",
        }
        base.update(overrides)
        return CreateDownloadRequest(**base)

    assert qm.requested_editors(request(target_editor="premiere"), settings) == ["premiere"]
    # 'auto' considers every enabled editor; only the ones open actually receive the file.
    assert qm.requested_editors(request(), settings) == [
        "resolve",
        "premiere",
        "aftereffects",
        "audition",
    ]
    assert qm.requested_editors(
        request(auto_import_to_premiere=False, auto_import_to_aftereffects=False, auto_import_to_audition=False), settings
    ) == ["resolve"]
