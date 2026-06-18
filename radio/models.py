from __future__ import annotations

import ipaddress
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse
from typing import Any


COUNTRY_NAMES_BY_CODE = {
    "RU": "Россия",
    "US": "США",
    "GB": "Великобритания",
    "DE": "Германия",
    "FR": "Франция",
    "ES": "Испания",
    "IT": "Италия",
    "PL": "Польша",
    "UA": "Украина",
    "BY": "Беларусь",
    "KZ": "Казахстан",
}

LOCAL_PLAYLIST_EXTENSIONS = {".m3u", ".m3u8", ".pls", ".xspf"}
LOCAL_AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".aac", ".m4a", ".wma", ".opus"}


@dataclass(frozen=True, slots=True)
class Station:
    uuid: str
    name: str
    url: str
    homepage: str = ""
    favicon: str = ""
    country: str = ""
    countrycode: str = ""
    language: str = ""
    tags: str = ""
    codec: str = ""
    bitrate: int = 0
    votes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_private_or_local_host(hostname: str) -> bool:
    host = hostname.strip().lower()
    if host in {"localhost", "localhost.localdomain"}:
        return True

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def is_valid_stream_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    if parsed.scheme == "file":
        return _is_local_media_file(parsed.path)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.hostname:
        return False
    if _is_private_or_local_host(parsed.hostname):
        return False
    return True


def _is_local_playlist_file(path: str) -> bool:
    if not path:
        return False
    suffix = Path(path).suffix.casefold()
    return suffix in LOCAL_PLAYLIST_EXTENSIONS


def _is_local_media_file(path: str) -> bool:
    if not path:
        return False
    suffix = Path(path).suffix.casefold()
    return suffix in LOCAL_PLAYLIST_EXTENSIONS or suffix in LOCAL_AUDIO_EXTENSIONS


def normalize_station(raw: dict[str, Any]) -> Station | None:
    stream_url = safe_str(raw.get("url_resolved") or raw.get("url"))
    name = safe_str(raw.get("name"), "Без названия") or "Без названия"

    if not stream_url or not is_valid_stream_url(stream_url):
        return None

    uuid = safe_str(raw.get("stationuuid") or raw.get("uuid"))
    countrycode = safe_str(raw.get("countrycode")).upper()
    country = safe_str(raw.get("country")) or COUNTRY_NAMES_BY_CODE.get(countrycode, "")

    return Station(
        uuid=uuid,
        name=name,
        url=stream_url,
        homepage=safe_str(raw.get("homepage")),
        favicon=safe_str(raw.get("favicon")),
        country=country,
        countrycode=countrycode,
        language=safe_str(raw.get("language")),
        tags=safe_str(raw.get("tags")),
        codec=safe_str(raw.get("codec")).upper(),
        bitrate=safe_int(raw.get("bitrate")),
        votes=safe_int(raw.get("votes")),
    )


def station_from_dict(raw: dict[str, Any]) -> Station | None:
    return normalize_station(raw)
