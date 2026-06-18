from __future__ import annotations

from typing import Any

from .models import Station, normalize_station


FALLBACK_STATIONS: list[dict[str, Any]] = [
    {
        "uuid": "fallback-record",
        "name": "Radio Record",
        "url": "https://radiorecord.hostingradio.ru/rr_main96.aacp",
        "homepage": "https://radiorecord.ru/",
        "favicon": "",
        "country": "Россия",
        "countrycode": "RU",
        "language": "russian",
        "tags": "dance,pop,electronic",
        "codec": "AAC",
        "bitrate": 96,
        "votes": 0,
    },
    {
        "uuid": "fallback-mayak",
        "name": "Радио Маяк",
        "url": "https://icecast-vgtrk.cdnvideo.ru/mayakfm_mp3_192kbps",
        "homepage": "https://smotrim.ru/radiomayak",
        "favicon": "",
        "country": "Россия",
        "countrycode": "RU",
        "language": "russian",
        "tags": "news,talk",
        "codec": "MP3",
        "bitrate": 192,
        "votes": 0,
    },
    {
        "uuid": "fallback-vesti-fm",
        "name": "Вести FM",
        "url": "https://icecast-vgtrk.cdnvideo.ru/vestifm_mp3_192kbps",
        "homepage": "https://smotrim.ru/radio/vestifm",
        "favicon": "",
        "country": "Россия",
        "countrycode": "RU",
        "language": "russian",
        "tags": "news,talk",
        "codec": "MP3",
        "bitrate": 192,
        "votes": 0,
    },
    {
        "uuid": "fallback-bbc-world-service",
        "name": "BBC World Service",
        "url": "https://stream.live.vc.bbcmedia.co.uk/bbc_world_service",
        "homepage": "https://www.bbc.co.uk/worldserviceradio",
        "favicon": "",
        "country": "Великобритания",
        "countrycode": "GB",
        "language": "english",
        "tags": "news,talk,world",
        "codec": "MP3",
        "bitrate": 128,
        "votes": 0,
    },
    {
        "uuid": "fallback-france-inter",
        "name": "France Inter",
        "url": "https://icecast.radiofrance.fr/franceinter-midfi.mp3",
        "homepage": "https://www.radiofrance.fr/franceinter",
        "favicon": "",
        "country": "Франция",
        "countrycode": "FR",
        "language": "french",
        "tags": "news,talk,culture",
        "codec": "MP3",
        "bitrate": 128,
        "votes": 0,
    },
    {
        "uuid": "fallback-fip",
        "name": "FIP",
        "url": "https://icecast.radiofrance.fr/fip-midfi.mp3",
        "homepage": "https://www.radiofrance.fr/fip",
        "favicon": "",
        "country": "Франция",
        "countrycode": "FR",
        "language": "french",
        "tags": "jazz,rock,world,music",
        "codec": "MP3",
        "bitrate": 128,
        "votes": 0,
    },
    {
        "uuid": "fallback-deutschlandfunk",
        "name": "Deutschlandfunk",
        "url": "https://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3",
        "homepage": "https://www.deutschlandfunk.de/",
        "favicon": "",
        "country": "Германия",
        "countrycode": "DE",
        "language": "german",
        "tags": "news,talk,culture",
        "codec": "MP3",
        "bitrate": 128,
        "votes": 0,
    },
    {
        "uuid": "fallback-somafm-groove-salad",
        "name": "SomaFM Groove Salad",
        "url": "https://ice2.somafm.com/groovesalad-128-mp3",
        "homepage": "https://somafm.com/groovesalad/",
        "favicon": "",
        "country": "США",
        "countrycode": "US",
        "language": "english",
        "tags": "ambient,electronic,chillout",
        "codec": "MP3",
        "bitrate": 128,
        "votes": 0,
    },
    {
        "uuid": "fallback-somafm-indie-pop-rocks",
        "name": "SomaFM Indie Pop Rocks",
        "url": "https://ice2.somafm.com/indiepop-128-mp3",
        "homepage": "https://somafm.com/indiepop/",
        "favicon": "",
        "country": "США",
        "countrycode": "US",
        "language": "english",
        "tags": "indie,rock,pop",
        "codec": "MP3",
        "bitrate": 128,
        "votes": 0,
    },
]


def fallback_stations() -> list[Station]:
    stations: list[Station] = []
    for item in FALLBACK_STATIONS:
        station = normalize_station(item)
        if station is not None:
            stations.append(station)
    return stations


def search_fallback(
    query: str = "",
    country_code: str = "",
    tag_or_language: str = "",
    limit: int = 100,
) -> list[Station]:
    query = query.strip().casefold()
    country_code = country_code.strip().upper()
    tag_or_language = tag_or_language.strip().casefold()

    result: list[Station] = []
    for station in fallback_stations():
        if country_code and station.countrycode != country_code:
            continue
        if query and query not in _searchable_text(station):
            continue
        if tag_or_language and tag_or_language not in _searchable_text(station):
            continue
        result.append(station)
        if len(result) >= limit:
            break

    return result


def _searchable_text(station: Station) -> str:
    return " ".join(
        [station.name, station.country, station.language, station.tags, station.codec]
    ).casefold()
