from radio.models import Station
from radio.utils import deduplicate_stations


def test_deduplicate_by_uuid() -> None:
    stations = [
        Station(uuid="same", name="A", url="https://example.com/a"),
        Station(uuid="same", name="B", url="https://example.com/b"),
    ]

    result = deduplicate_stations(stations, limit=10)

    assert len(result) == 1
    assert result[0].name == "A"


def test_deduplicate_by_url_when_uuid_is_empty() -> None:
    stations = [
        Station(uuid="", name="A", url="https://example.com/same"),
        Station(uuid="", name="B", url="https://example.com/same"),
    ]

    result = deduplicate_stations(stations, limit=10)

    assert len(result) == 1
    assert result[0].name == "A"


def test_deduplicate_respects_limit() -> None:
    stations = [
        Station(uuid=str(index), name=f"Radio {index}", url=f"https://example.com/{index}")
        for index in range(5)
    ]

    result = deduplicate_stations(stations, limit=3)

    assert len(result) == 3
