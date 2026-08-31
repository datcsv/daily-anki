import json

from daily_anki.anki import SyncResult
from daily_anki.history import append_sync_event


def test_append_sync_event_writes_jsonl(tmp_path):
    path = tmp_path / "history.jsonl"
    append_sync_event(path, "Daily Life", "Japanese", SyncResult(("猫",), ("犬",)), ["鳥"], False)
    event = json.loads(path.read_text(encoding="utf-8"))
    assert event["deck"] == "Daily Life"
    assert event["created"] == ["猫"]
    assert event["skipped"] == ["犬"]
    assert event["missing"] == ["鳥"]
    assert event["dry_run"] is False