from __future__ import annotations

from pathlib import Path

import httpx

from .m3u import parse_m3u
from .models import Station
from .utils import deduplicate_stations, station_matches


GLOBAL_M3U_PLAYLISTS = [
    (
        "Pulham Internet Radio",
        "https://raw.githubusercontent.com/Pulham/Internet-Radio-HQ-URL-playlists/main/Radio%20Stations.m3u",
        "",
        "public-radio",
    ),
]


class M3UPlaylistClient:
    def __init__(
        self,
        *,
        playlist_urls: list[tuple[str, str, str, str]] | None = None,
        local_dirs: list[Path] | None = None,
        timeout: httpx.Timeout | None = None,
        user_agent: str = "All Radio Python/1.0",
    ) -> None:
        self.playlist_urls = (
            GLOBAL_M3U_PLAYLISTS if playlist_urls is None else playlist_urls
        )
        self.local_dirs = local_dirs or [
            Path.cwd() / "playlists",
            Path.home() / ".all_radio_python" / "playlists",
        ]
        self.timeout = timeout or httpx.Timeout(7.0, connect=2.0)
        self.user_agent = user_agent
        self.warning_message = ""

    def search(
        self,
        query: str = "",
        country_code: str = "",
        tag_or_language: str = "",
        limit: int = 100,
    ) -> list[Station]:
        self.warning_message = ""
        country_code = country_code.strip().upper()
        limit = max(1, min(limit, 1000))
        stations: list[Station] = []
        errors: list[str] = []

        for source_name, content, source_countrycode, source_tags in self._iter_sources(
            country_code
        ):
            try:
                parsed = parse_m3u(
                    content,
                    default_countrycode=source_countrycode,
                    default_tags=source_tags,
                )
            except Exception as exc:
                errors.append(f"{source_name}: {exc}")
                continue

            for station in parsed:
                if station_matches(station, query, country_code, tag_or_language):
                    stations.append(station)
                if len(stations) >= limit:
                    break

            if len(stations) >= limit:
                break

        if errors:
            self.warning_message = "; ".join(errors[-3:])

        return deduplicate_stations(stations, limit)

    def _iter_sources(
        self,
        country_code: str,
    ) -> list[tuple[str, str, str, str]]:
        sources: list[tuple[str, str, str, str]] = []

        for path in self._local_playlist_files():
            try:
                sources.append((str(path), path.read_text(encoding="utf-8"), "", "local"))
            except UnicodeDecodeError:
                sources.append((str(path), path.read_text(encoding="cp1251"), "", "local"))
            except OSError:
                continue

        urls = self._remote_playlist_urls(country_code)
        if urls:
            with httpx.Client(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
                trust_env=True,
            ) as client:
                for name, url, source_countrycode, source_tags in urls:
                    try:
                        response = client.get(url)
                        response.raise_for_status()
                    except Exception:
                        continue
                    sources.append((name, response.text, source_countrycode, source_tags))

        return sources

    def _remote_playlist_urls(
        self,
        country_code: str,
    ) -> list[tuple[str, str, str, str]]:
        return self.playlist_urls

    def _local_playlist_files(self) -> list[Path]:
        files: list[Path] = []
        for directory in self.local_dirs:
            if not directory.exists():
                continue
            for pattern in ("*.m3u", "*.m3u8"):
                files.extend(sorted(directory.glob(pattern)))
        return files
