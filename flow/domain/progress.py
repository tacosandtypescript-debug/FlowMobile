from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any


@dataclass(frozen=True, slots=True)
class ProgressSnapshot:
    percent: float
    speed: float | None
    eta: float | None


class DownloadProgress:
    """Normaliza y suaviza el progreso que entregan distintos sitios."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._filename = ""
        self._last_bytes = 0
        self._sample_time = 0.0
        self._draw_time = 0.0
        self._draw_percent = -1.0
        self._speed: float | None = None

    def update(
        self,
        data: dict[str, Any],
        now: float | None = None,
    ) -> ProgressSnapshot | None:
        current_time = time.monotonic() if now is None else now
        filename = str(data.get("filename") or data.get("tmpfilename") or "")
        downloaded = max(0, int(data.get("downloaded_bytes") or 0))
        total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
        total = max(0, int(total or 0))

        stage_changed = bool(filename and filename != self._filename)
        counter_restarted = bool(self._sample_time and downloaded < self._last_bytes)
        if stage_changed or counter_restarted:
            if filename:
                self._filename = filename
            self._last_bytes = 0
            self._sample_time = current_time
            self._draw_percent = -1.0
            self._speed = None

        supplied_speed = data.get("speed")
        measured_speed: float | None = None
        if isinstance(supplied_speed, (int, float)) and supplied_speed > 0:
            measured_speed = float(supplied_speed)
        elif self._sample_time and current_time > self._sample_time:
            byte_delta = downloaded - self._last_bytes
            if byte_delta >= 0:
                measured_speed = byte_delta / (current_time - self._sample_time)

        if measured_speed is not None:
            self._speed = (
                measured_speed
                if self._speed is None
                else self._speed * 0.70 + measured_speed * 0.30
            )

        percent = min(100.0, downloaded / total * 100) if total else 0.0
        supplied_eta = data.get("eta")
        if isinstance(supplied_eta, (int, float)) and supplied_eta >= 0:
            eta: float | None = float(supplied_eta)
        elif total and self._speed:
            eta = max(0.0, (total - downloaded) / self._speed)
        else:
            eta = None

        self._last_bytes = downloaded
        self._sample_time = current_time
        if (
            abs(percent - self._draw_percent) < 0.3
            and current_time - self._draw_time < 0.5
        ):
            return None
        self._draw_percent = percent
        self._draw_time = current_time
        return ProgressSnapshot(percent, self._speed, eta)
