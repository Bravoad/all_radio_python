from __future__ import annotations

import hashlib
from pathlib import Path

from .models import LOCAL_PLAYLIST_EXTENSIONS, Station


def create_custom_station(name: str, playlist_path: str | Path) -> Station:
    path = Path(playlist_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError("Файл плейлиста не найден.")

    if path.suffix.casefold() not in LOCAL_PLAYLIST_EXTENSIONS:
        extensions = ", ".join(sorted(LOCAL_PLAYLIST_EXTENSIONS))
        raise ValueError(f"Поддерживаются только плейлисты: {extensions}.")

    station_name = name.strip() or path.stem
    playlist_uri = path.as_uri()
    station_id = hashlib.sha1(playlist_uri.encode("utf-8")).hexdigest()

    return Station(
        uuid=f"custom:{station_id}",
        name=station_name,
        url=playlist_uri,
        homepage=str(path.parent),
        country="Локальная",
        language="local",
        tags="custom,playlist,local",
        codec=path.suffix.lstrip(".").upper(),
        votes=0,
    )
