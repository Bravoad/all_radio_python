from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Station, station_from_dict


class FavoritesStore:
    def __init__(self, favorites_file: Path) -> None:
        self.favorites_file = favorites_file

    def load(self) -> list[Station]:
        self.favorites_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.favorites_file.exists():
            return []

        try:
            raw = json.loads(self.favorites_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(raw, list):
            return []

        stations: list[Station] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            station = station_from_dict(item)
            if station is not None:
                stations.append(station)
        return stations

    def save(self, stations: list[Station]) -> None:
        self.favorites_file.parent.mkdir(parents=True, exist_ok=True)
        data: list[dict[str, Any]] = [station.to_dict() for station in stations]
        self.favorites_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
