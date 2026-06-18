from radio.custom_stations import create_custom_station
from radio.favorites import FavoritesStore


def test_create_custom_station_from_local_playlist(tmp_path) -> None:
    playlist = tmp_path / "my-radio.m3u"
    playlist.write_text("#EXTM3U\nhttps://example.com/stream.mp3\n", encoding="utf-8")

    station = create_custom_station("My Radio", playlist)

    assert station.uuid.startswith("custom:")
    assert station.name == "My Radio"
    assert station.url == playlist.resolve().as_uri()
    assert station.country == "Локальная"
    assert station.codec == "M3U"


def test_create_custom_station_uses_filename_when_name_is_empty(tmp_path) -> None:
    playlist = tmp_path / "ambient.pls"
    playlist.write_text("[playlist]\nFile1=https://example.com/stream.mp3\n", encoding="utf-8")

    station = create_custom_station("", playlist)

    assert station.name == "ambient"
    assert station.codec == "PLS"


def test_custom_station_survives_json_store(tmp_path) -> None:
    playlist = tmp_path / "local.m3u8"
    playlist.write_text("#EXTM3U\nhttps://example.com/live.m3u8\n", encoding="utf-8")
    station = create_custom_station("Local", playlist)
    store = FavoritesStore(tmp_path / "custom_stations.json")

    store.save([station])
    loaded = store.load()

    assert loaded == [station]
