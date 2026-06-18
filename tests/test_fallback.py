from radio.fallback import fallback_stations, search_fallback


def test_fallback_has_stations() -> None:
    stations = fallback_stations()

    assert stations
    assert all(station.url for station in stations)


def test_search_fallback_by_country() -> None:
    stations = search_fallback(country_code="RU")

    assert stations
    assert all(station.countrycode == "RU" for station in stations)


def test_search_fallback_by_tag() -> None:
    stations = search_fallback(tag_or_language="news")

    assert stations
    assert all("news" in station.tags.casefold() for station in stations)
