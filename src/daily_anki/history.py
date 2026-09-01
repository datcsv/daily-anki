import json
from datetime import datetime, timezone
from pathlib import Path

from .anki import SyncResult


def append_sync_event(
    path: Path, deck: str, note_type: str, result: SyncResult, missing: list[str], dry_run: bool
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deck": deck,
        "note_type": note_type,
        "dry_run": dry_run,
        "created": list(result.created),
        "skipped": list(result.skipped),
        "existing": list(result.existing),
        "failed": list(result.failed),
        "missing": missing,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
