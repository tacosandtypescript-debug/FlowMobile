from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import re

from flow.domain.models import DownloadChoice
from flow.infrastructure.paths import AUDIO_BATCH_DIR, BATCH_DIR, QUEUE_DIR, VIDEO_BATCH_DIR
from flow.infrastructure.privacy import protect_private_path


@dataclass(slots=True)
class QueueItem:
    url: str
    status: str = "pending"
    title: str = ""
    error: str = ""
    file: str = ""


@dataclass(slots=True)
class DownloadQueue:
    queue_id: str
    created: str
    choice: DownloadChoice
    items: list[QueueItem] = field(default_factory=list)

    @property
    def folder(self) -> Path:
        legacy = BATCH_DIR / self.queue_id
        if legacy.exists():
            return legacy
        root = VIDEO_BATCH_DIR if self.choice.kind == "video" else AUDIO_BATCH_DIR
        return root / self.queue_id

    @property
    def pending(self) -> int:
        return sum(
            item.status in {"pending", "paused", "error", "downloading"}
            for item in self.items
        )

    @property
    def completed(self) -> int:
        return sum(item.status == "completed" for item in self.items)


def _queue_file(queue_id: str) -> Path:
    safe_id = re.sub(r"[^0-9A-Za-z_.-]", "-", queue_id)
    return QUEUE_DIR / f"{safe_id}.json"


def create_queue(urls: list[str], choice: DownloadChoice) -> DownloadQueue:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    queue_id = stamp
    suffix = 2
    while _queue_file(queue_id).exists() or (BATCH_DIR / queue_id).exists():
        queue_id = f"{stamp}-{suffix}"
        suffix += 1
    queue = DownloadQueue(
        queue_id=queue_id,
        created=datetime.now().isoformat(timespec="seconds"),
        choice=choice,
        items=[QueueItem(url=url) for url in dict.fromkeys(urls)],
    )
    queue.folder.mkdir(parents=True, exist_ok=True)
    save_queue(queue)
    return queue


def save_queue(queue: DownloadQueue) -> None:
    target = _queue_file(queue.queue_id)
    temporary = target.with_suffix(".tmp")
    payload = {
        "queue_id": queue.queue_id,
        "created": queue.created,
        "choice": asdict(queue.choice),
        "items": [asdict(item) for item in queue.items],
    }
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if not protect_private_path(temporary):
        temporary.unlink(missing_ok=True)
        raise OSError("No se pudo proteger la cola privada.")
    os.replace(temporary, target)


def load_queue(path: Path) -> DownloadQueue | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_choice = data.get("choice") or {}
        choice = DownloadChoice(
            str(raw_choice.get("kind") or "video"),
            raw_choice.get("height") if isinstance(raw_choice.get("height"), int) else None,
            str(raw_choice.get("audio_format") or "auto"),
        )
        items = [
            QueueItem(
                url=str(item.get("url") or ""),
                status=str(item.get("status") or "pending"),
                title=str(item.get("title") or ""),
                error=str(item.get("error") or ""),
                file=str(item.get("file") or ""),
            )
            for item in data.get("items") or []
            if isinstance(item, dict) and item.get("url")
        ]
        return DownloadQueue(
            queue_id=str(data.get("queue_id") or path.stem),
            created=str(data.get("created") or ""),
            choice=choice,
            items=items,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None


def list_queues(incomplete_only: bool = False) -> list[DownloadQueue]:
    queues = [queue for path in QUEUE_DIR.glob("*.json") if (queue := load_queue(path))]
    if incomplete_only:
        queues = [queue for queue in queues if queue.pending]
    return sorted(queues, key=lambda queue: queue.created, reverse=True)
