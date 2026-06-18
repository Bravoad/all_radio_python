import httpx
import pytest

from radio.models import Station
from radio.radio_browser import RadioBrowserClient


def test_build_search_variants_without_tag() -> None:
    variants = RadioBrowserClient._build_search_variants(
        query="rock",
        country_code="US",
        tag_or_language="",
        limit=100,
    )

    assert variants == [
        (
            "search",
            {
                "limit": 100,
                "hidebroken": "true",
                "order": "clickcount",
                "reverse": "true",
                "name": "rock",
                "countrycode": "US",
            },
        )
    ]


def test_build_search_variants_with_tag_or_language() -> None:
    variants = RadioBrowserClient._build_search_variants(
        query="",
        country_code="DE",
        tag_or_language="news",
        limit=50,
    )

    assert variants[0][0] == "tag"
    assert variants[0][1]["tag"] == "news"
    assert variants[1][0] == "language"
    assert variants[1][1]["language"] == "news"


def test_search_raises_when_all_online_sources_fail() -> None:
    client = RadioBrowserClient(https_servers=["https://bad.invalid"], http_fallback_servers=[])

    def failing_request(*args, **kwargs):
        raise httpx.ConnectError("boom")

    client._request_stations = failing_request  # type: ignore[method-assign]
    client._request_m3u_stations = failing_request  # type: ignore[method-assign]
    client.playlists.search = lambda *args, **kwargs: []  # type: ignore[method-assign]

    with pytest.raises(RuntimeError):
        client.search(query="record", country_code="RU", limit=10)

    assert client.warning_message


def test_search_combines_json_m3u_and_playlist_sources() -> None:
    client = RadioBrowserClient(
        https_servers=["https://example.test"],
        http_fallback_servers=[],
    )

    def json_request(*args, **kwargs):
        return [
            {
                "stationuuid": "json",
                "name": "JSON Radio",
                "url": "https://example.com/json.mp3",
            }
        ]

    def m3u_request(*args, **kwargs):
        return [Station(uuid="m3u", name="M3U Radio", url="https://example.com/m3u.mp3")]

    class PlaylistClient:
        warning_message = ""

        def search(self, *args, **kwargs):
            return [
                Station(
                    uuid="playlist",
                    name="Playlist Radio",
                    url="https://example.com/playlist.mp3",
                )
            ]

    client._request_stations = json_request  # type: ignore[method-assign]
    client._request_m3u_stations = m3u_request  # type: ignore[method-assign]
    client.playlists = PlaylistClient()  # type: ignore[assignment]

    stations = client.search(limit=10)

    assert [station.name for station in stations[:3]] == [
        "JSON Radio",
        "M3U Radio",
        "Playlist Radio",
    ]
