from pathlib import Path

from radio.favorites import FavoritesStore
from radio.models import Station


def test_favorites_save_and_load(tmp_path: Path) -> None:
    store = FavoritesStore(tmp_path / "favorites.json")
    stations = [Station(uuid="1", name="Radio", url="https://example.com/stream")]

    store.save(stations)
    loaded = store.load()

    assert loaded == stations


def test_favorites_invalid_json_returns_empty_list(tmp_path: Path) -> None:
    file = tmp_path / "favorites.json"
    file.write_text("not json", encoding="utf-8")
    store = FavoritesStore(file)

    assert store.load() == []
