from __future__ import annotations

import os
import socket
import sys
from dataclasses import dataclass
from typing import Any

import httpx

from .m3u import parse_m3u
from .models import Station, normalize_station
from .playlists import M3UPlaylistClient
from .utils import deduplicate_stations


RADIO_BROWSER_HTTPS_SERVERS = [
    "https://de1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://at1.api.radio-browser.info",
]

RADIO_BROWSER_HTTP_FALLBACK_SERVERS = [
    "http://all.api.radio-browser.info",
    "http://de1.api.radio-browser.info",
    "http://nl1.api.radio-browser.info",
    "http://at1.api.radio-browser.info",
]

LOCAL_HTTP_PROXY_PORTS = (7897, 7890, 10809, 8080)
DEFAULT_USER_AGENT = "All Radio Python/1.0"


@dataclass(frozen=True, slots=True)
class NetworkMode:
    name: str
    trust_env: bool
    proxy_url: str | None = None


class RadioBrowserClient:
    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        https_servers: list[str] | None = None,
        http_fallback_servers: list[str] | None = None,
        timeout_seconds: float = 7.0,
        connect_timeout_seconds: float = 2.0,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = httpx.Timeout(timeout_seconds, connect=connect_timeout_seconds)
        self.base_urls = self._unique(
            (https_servers or RADIO_BROWSER_HTTPS_SERVERS)
            + (http_fallback_servers or RADIO_BROWSER_HTTP_FALLBACK_SERVERS)
        )
        self.network_modes = self._network_modes()
        self.warning_message = ""
        self._clients: list[httpx.Client] = []
        self.playlists = M3UPlaylistClient(
            timeout=self.timeout,
            user_agent=self.user_agent,
        )

    def search(
        self,
        query: str = "",
        country_code: str = "",
        tag_or_language: str = "",
        limit: int = 100,
    ) -> list[Station]:
        self.warning_message = ""
        query = query.strip()
        country_code = country_code.strip().upper()
        tag_or_language = tag_or_language.strip()
        limit = max(1, min(limit, 1000))

        search_variants = self._build_search_variants(
            query=query,
            country_code=country_code,
            tag_or_language=tag_or_language,
            limit=limit,
        )

        source_results: list[list[Station]] = []
        errors: list[str] = []
        last_error: Exception | None = None

        json_stations, json_errors, json_last_error = self._search_radio_browser_json(
            search_variants
        )
        source_results.append(json_stations)
        errors.extend(json_errors)
        last_error = json_last_error or last_error

        m3u_stations, m3u_errors, m3u_last_error = self._search_radio_browser_m3u(
            search_variants
        )
        source_results.append(m3u_stations)
        errors.extend(m3u_errors)
        last_error = m3u_last_error or last_error

        try:
            playlist_stations = self.playlists.search(
                query=query,
                country_code=country_code,
                tag_or_language=tag_or_language,
                limit=limit,
            )
        except Exception as exc:
            playlist_stations = []
            last_error = exc
            errors.append(f"M3U playlists: {exc}")
        source_results.append(playlist_stations)

        stations = deduplicate_stations(
            self._interleave_station_sources(source_results),
            limit,
        )
        if stations:
            if errors:
                self.warning_message = self._build_partial_warning(errors)
            return stations

        self.warning_message = self._build_search_failure_warning(last_error, errors)
        raise RuntimeError(self.warning_message)

    def _search_radio_browser_json(
        self,
        search_variants: list[tuple[str, dict[str, Any]]],
    ) -> tuple[list[Station], list[str], Exception | None]:
        stations: list[Station] = []
        errors: list[str] = []
        last_error: Exception | None = None

        for mode in self.network_modes:
            for base_url in self.base_urls:
                successful_requests = 0
                variant_errors: list[str] = []

                with self._create_client(mode) as client:
                    for variant_name, params in search_variants:
                        try:
                            data = self._request_stations(client, base_url, params)
                        except Exception as exc:
                            last_error = exc
                            variant_errors.append(f"{variant_name}: {exc}")
                            continue

                        successful_requests += 1
                        stations.extend(self._normalize_items(data))

                if successful_requests:
                    return stations, errors, last_error

                if variant_errors:
                    errors.append(
                        f"JSON; {mode.name}; {base_url}: {'; '.join(variant_errors)}"
                    )

        return stations, errors, last_error

    def _search_radio_browser_m3u(
        self,
        search_variants: list[tuple[str, dict[str, Any]]],
    ) -> tuple[list[Station], list[str], Exception | None]:
        stations: list[Station] = []
        errors: list[str] = []
        last_error: Exception | None = None

        for mode in self.network_modes:
            for base_url in self.base_urls:
                successful_requests = 0
                variant_errors: list[str] = []

                with self._create_client(mode) as client:
                    for variant_name, params in search_variants:
                        try:
                            stations.extend(
                                self._request_m3u_stations(client, base_url, params)
                            )
                        except Exception as exc:
                            last_error = exc
                            variant_errors.append(f"{variant_name}: {exc}")
                            continue

                        successful_requests += 1

                if successful_requests:
                    return stations, errors, last_error

                if variant_errors:
                    errors.append(
                        f"M3U; {mode.name}; {base_url}: {'; '.join(variant_errors)}"
                    )

        return stations, errors, last_error

    def close(self) -> None:
        for client in self._clients:
            client.close()
        self._clients.clear()

    @staticmethod
    def _build_search_variants(
        *,
        query: str,
        country_code: str,
        tag_or_language: str,
        limit: int,
    ) -> list[tuple[str, dict[str, Any]]]:
        base_params: dict[str, Any] = {
            "limit": limit,
            "hidebroken": "true",
            "order": "clickcount",
            "reverse": "true",
        }

        if query:
            base_params["name"] = query
        if country_code:
            base_params["countrycode"] = country_code

        if not tag_or_language:
            return [("search", base_params)]

        tag_params = base_params.copy()
        tag_params["tag"] = tag_or_language

        language_params = base_params.copy()
        language_params["language"] = tag_or_language

        return [("tag", tag_params), ("language", language_params)]

    def _request_stations(
        self,
        client: httpx.Client,
        base_url: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._request_json_stations(client, base_url, params)

    def _request_json_stations(
        self,
        client: httpx.Client,
        base_url: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        url = base_url.rstrip("/") + "/json/stations/search"
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError("Radio Browser вернул неожиданный формат данных")
        return [item for item in data if isinstance(item, dict)]

    def _request_m3u_stations(
        self,
        client: httpx.Client,
        base_url: str,
        params: dict[str, Any],
    ) -> list[Station]:
        url = base_url.rstrip("/") + "/m3u/stations/search"
        response = client.get(url, params=params)
        response.raise_for_status()
        return parse_m3u(
            response.text,
            default_countrycode=str(params.get("countrycode", "")),
            default_tags=str(params.get("tag", "")),
        )

    @staticmethod
    def _normalize_items(items: list[dict[str, Any]]) -> list[Station]:
        stations: list[Station] = []
        for item in items:
            station = normalize_station(item)
            if station is not None:
                stations.append(station)
        return stations

    @staticmethod
    def _interleave_station_sources(source_results: list[list[Station]]) -> list[Station]:
        merged: list[Station] = []
        max_length = max((len(stations) for stations in source_results), default=0)

        for index in range(max_length):
            for stations in source_results:
                if index < len(stations):
                    merged.append(stations[index])

        return merged

    def _create_client(self, mode: NetworkMode) -> httpx.Client:
        options: dict[str, Any] = {
            "timeout": self.timeout,
            "trust_env": mode.trust_env,
            "headers": {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        }
        if mode.proxy_url:
            options["proxy"] = mode.proxy_url

        client = httpx.Client(**options)
        self._clients.append(client)
        return client

    @classmethod
    def _network_modes(cls) -> list[NetworkMode]:
        modes: list[NetworkMode] = [NetworkMode("напрямую", False)]

        proxy_vars = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")
        has_env_proxy = any(
            os.environ.get(name) or os.environ.get(name.lower())
            for name in proxy_vars
        )
        if has_env_proxy:
            modes.append(NetworkMode("через переменные прокси", True))

        windows_proxy_url = cls._windows_proxy_url()
        if windows_proxy_url:
            modes.append(NetworkMode("через прокси Windows", False, windows_proxy_url))

        for port in LOCAL_HTTP_PROXY_PORTS:
            if cls._local_port_open(port):
                proxy_url = f"http://127.0.0.1:{port}"
                modes.append(NetworkMode(f"через локальный прокси 127.0.0.1:{port}", False, proxy_url))

        return modes

    @staticmethod
    def _proxy_url(value: str) -> str | None:
        value = value.strip()
        if not value:
            return None
        if value.lower().startswith("socks"):
            return None
        if "://" not in value:
            return f"http://{value}"
        return value

    @classmethod
    def _windows_proxy_url(cls) -> str | None:
        if sys.platform != "win32":
            return None

        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            ) as key:
                proxy_enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
                proxy_server = winreg.QueryValueEx(key, "ProxyServer")[0]
        except OSError:
            return None

        if not proxy_enabled or not isinstance(proxy_server, str):
            return None

        proxy_server = proxy_server.strip()
        if not proxy_server:
            return None

        if "=" not in proxy_server:
            return cls._proxy_url(proxy_server)

        proxies: dict[str, str] = {}
        for part in proxy_server.split(";"):
            if "=" not in part:
                continue
            protocol, value = part.split("=", 1)
            protocol = protocol.strip().lower()
            if protocol not in {"http", "https"}:
                continue
            proxy_url = cls._proxy_url(value)
            if proxy_url:
                proxies[protocol] = proxy_url

        return proxies.get("https") or proxies.get("http")

    @staticmethod
    def _local_port_open(port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            return False

    @staticmethod
    def _unique(items: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in items:
            normalized = item.strip().rstrip("/")
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    def _build_search_failure_warning(
        self,
        last_error: Exception | None,
        errors: list[str],
    ) -> str:
        details = "\n".join(errors[-6:])
        modes = ", ".join(self._unique([mode.name for mode in self.network_modes]))
        return (
            "Не удалось найти станции в онлайн-каталогах и плейлистах. "
            f"Проверенные режимы: {modes}. "
            f"Последняя ошибка: {last_error}. "
            f"Детали: {details}"
        )

    @staticmethod
    def _build_partial_warning(errors: list[str]) -> str:
        details = "; ".join(errors[-3:])
        return f"Часть источников недоступна: {details}"
