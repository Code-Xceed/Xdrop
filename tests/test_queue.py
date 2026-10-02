import pytest
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "desktop-service")))

import xdrop.config as config
from xdrop.database import init_db
from xdrop.download_queue import DownloadQueueManager, CreateDownloadRequest

@pytest.fixture(autouse=True)
def setup_queue_test(tmp_path, monkeypatch):
    test_db = tmp_path / "queue_test.db"
    monkeypatch.setattr(config, "DB_PATH", test_db)
    init_db()

def test_queue_add_and_cancel():
    async def run_test():
        qm = DownloadQueueManager()
        events = []
        
        def on_event(ev):
            events.append(ev)

        qm.subscribe(on_event)

        req = CreateDownloadRequest(
            source_url="https://example.com/test.mp4",
            asset_id="test_video",
            format="mp4",
            quality_label="1080p",
            title="Test Download Video"
        )

        job = await qm.add_download(req)
        assert job["id"] is not None
        assert job["status"] == "queued"
        assert len(events) == 1
        assert events[0]["type"] == "JOB_CREATED"

        # Cancel job
        cancelled = await qm.cancel_job(job["id"])
        assert cancelled is True

        # Remove job
        removed = await qm.remove_job(job["id"])
        assert removed is True

    asyncio.run(run_test())
