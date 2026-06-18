from __future__ import annotations

from .models import Station


def deduplicate_stations(stations: list[Station], limit: int) -> list[Station]:
    result: list[Station] = []
    seen: set[str] = set()

    for station in stations:
        keys = [station.url]
        if station.uuid:
            keys.append(station.uuid)
        if station.name:
            keys.append(station.name)

        if any(key in seen for key in keys if key):
            continue

        for key in keys:
            if key:
                seen.add(key)

        result.append(station)
        if len(result) >= limit:
            break

    return result


def station_matches(
    station: Station,
    query: str = "",
    country_code: str = "",
    tag_or_language: str = "",
) -> bool:
    query = query.strip().casefold()
    country_code = country_code.strip().upper()
    tag_or_language = tag_or_language.strip().casefold()

    if country_code and station.countrycode != country_code:
        return False

    searchable_text = " ".join(
        [
            station.name,
            station.country,
            station.countrycode,
            station.language,
            station.tags,
            station.codec,
            station.url,
        ]
    ).casefold()

    if query and query not in searchable_text:
        return False
    if tag_or_language and tag_or_language not in searchable_text:
        return False

    return True
