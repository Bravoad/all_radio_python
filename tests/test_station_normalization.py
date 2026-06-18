from radio.models import Station, is_valid_stream_url, normalize_station


def test_normalize_radio_browser_station() -> None:
    raw = {
        "stationuuid": "abc",
        "name": "Test Radio",
        "url_resolved": "https://example.com/stream.mp3",
        "homepage": "https://example.com",
        "favicon": "https://example.com/favicon.ico",
        "country": "Germany",
        "countrycode": "de",
        "language": "german",
        "tags": "news,talk",
        "codec": "mp3",
        "bitrate": "128",
        "votes": "42",
    }

    station = normalize_station(raw)

    assert isinstance(station, Station)
    assert station.uuid == "abc"
    assert station.name == "Test Radio"
    assert station.url == "https://example.com/stream.mp3"
    assert station.countrycode == "DE"
    assert station.codec == "MP3"
    assert station.bitrate == 128
    assert station.votes == 42


def test_normalize_fills_country_from_countrycode() -> None:
    station = normalize_station(
        {
            "name": "US Radio",
            "url": "https://example.com/stream.mp3",
            "countrycode": "us",
        }
    )

    assert station is not None
    assert station.country == "США"
    assert station.countrycode == "US"


def test_invalid_stream_url_is_rejected() -> None:
    assert not is_valid_stream_url("file:///etc/passwd")
    assert not is_valid_stream_url("http://127.0.0.1:8000/private")
    assert not is_valid_stream_url("https://localhost/stream")
    assert not is_valid_stream_url("ftp://example.com/stream")


def test_normalize_rejects_station_without_valid_url() -> None:
    station = normalize_station({"name": "Bad", "url": "file:///tmp/stream"})

    assert station is None
