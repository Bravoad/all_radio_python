from radio.m3u import parse_m3u
from radio.playlists import M3UPlaylistClient


def test_parse_m3u_extinf_station() -> None:
    content = """#EXTM3U
#EXTINF:-1 tvg-id="station.one" tvg-name="Station One" tvg-logo="https://example.com/logo.png" group-title="Rock",Ignored Name
https://example.com/stream.mp3
"""

    stations = parse_m3u(content, default_countrycode="US", default_tags="playlist")

    assert len(stations) == 1
    assert stations[0].uuid == "m3u:station.one"
    assert stations[0].name == "Station One"
    assert stations[0].countrycode == "US"
    assert stations[0].tags == "playlist,Rock"
    assert stations[0].codec == "MP3"


def test_parse_m3u_plain_url_station() -> None:
    stations = parse_m3u("https://example.com/live/aacstream.aac\n")

    assert len(stations) == 1
    assert stations[0].name == "aacstream.aac"
    assert stations[0].codec == "AAC"


def test_playlist_client_searches_local_m3u(tmp_path) -> None:
    playlist_dir = tmp_path / "playlists"
    playlist_dir.mkdir()
    (playlist_dir / "local.m3u").write_text(
        """#EXTM3U
#EXTINF:-1 group-title="Jazz",Local Jazz
https://example.com/jazz.mp3
""",
        encoding="utf-8",
    )
    client = M3UPlaylistClient(playlist_urls=[], local_dirs=[playlist_dir])

    stations = client.search(tag_or_language="jazz", limit=10)

    assert len(stations) == 1
    assert stations[0].name == "Local Jazz"
