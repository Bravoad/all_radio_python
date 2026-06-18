from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

from .models import COUNTRY_NAMES_BY_CODE, Station, is_valid_stream_url, safe_int, safe_str


EXTINF_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


def parse_m3u(
    content: str,
    *,
    default_countrycode: str = "",
    default_language: str = "",
    default_tags: str = "",
) -> list[Station]:
    stations: list[Station] = []
    pending_name = ""
    pending_attrs: dict[str, str] = {}

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            pending_attrs = _parse_extinf_attrs(line)
            pending_name = _parse_extinf_name(line)
            continue

        if line.startswith("#"):
            continue

        if not is_valid_stream_url(line):
            pending_name = ""
            pending_attrs = {}
            continue

        station = _station_from_m3u_entry(
            url=line,
            name=pending_name,
            attrs=pending_attrs,
            default_countrycode=default_countrycode,
            default_language=default_language,
            default_tags=default_tags,
        )
        stations.append(station)
        pending_name = ""
        pending_attrs = {}

    return stations


def _parse_extinf_attrs(line: str) -> dict[str, str]:
    return {
        key.lower(): value.strip()
        for key, value in EXTINF_ATTR_RE.findall(line)
        if value.strip()
    }


def _parse_extinf_name(line: str) -> str:
    if "," not in line:
        return ""
    return line.rsplit(",", 1)[1].strip()


def _station_from_m3u_entry(
    *,
    url: str,
    name: str,
    attrs: dict[str, str],
    default_countrycode: str,
    default_language: str,
    default_tags: str,
) -> Station:
    station_name = (
        safe_str(attrs.get("tvg-name"))
        or safe_str(attrs.get("name"))
        or safe_str(name)
        or _name_from_url(url)
        or "M3U Radio"
    )
    group_title = safe_str(attrs.get("group-title"))
    tags = ",".join(item for item in [default_tags, group_title] if item)
    countrycode = (
        safe_str(attrs.get("tvg-country"))
        or safe_str(attrs.get("countrycode"))
        or default_countrycode
    ).upper()
    country = COUNTRY_NAMES_BY_CODE.get(countrycode, "")
    language = safe_str(attrs.get("tvg-language")) or default_language
    uuid = safe_str(attrs.get("tvg-id")) or _uuid_from_url(url)

    return Station(
        uuid=f"m3u:{uuid}",
        name=station_name,
        url=url,
        favicon=safe_str(attrs.get("tvg-logo")),
        country=country,
        countrycode=countrycode,
        language=language,
        tags=tags,
        codec=_codec_from_url(url),
        bitrate=safe_int(attrs.get("bitrate")),
        votes=0,
    )


def _name_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return ""
    return path.rsplit("/", 1)[-1].replace("_", " ").replace("-", " ")


def _uuid_from_url(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def _codec_from_url(url: str) -> str:
    path = urlparse(url).path.casefold()
    if path.endswith(".mp3"):
        return "MP3"
    if path.endswith((".aac", ".aacp")):
        return "AAC"
    if path.endswith((".m3u8", ".m3u")):
        return "HLS"
    if path.endswith(".ogg"):
        return "OGG"
    return ""
