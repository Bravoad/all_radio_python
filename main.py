from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from radio.custom_stations import create_custom_station
from radio.favorites import FavoritesStore
from radio.m3u import parse_m3u
from radio.models import Station
from radio.radio_browser import RadioBrowserClient


APP_NAME = "All Radio Python"
APP_DIR = Path.home() / ".all_radio_python"
FAVORITES_FILE = APP_DIR / "favorites.json"
CUSTOM_STATIONS_FILE = APP_DIR / "custom_stations.json"
DEFAULT_SEARCH_LIMIT = 500

COUNTRIES = {
    "Любая": "",
    "Россия": "RU",
    "Германия": "DE",
    "США": "US",
    "Великобритания": "GB",
    "Франция": "FR",
    "Испания": "ES",
    "Италия": "IT",
    "Польша": "PL",
    "Украина": "UA",
    "Беларусь": "BY",
    "Казахстан": "KZ",
}


def prepare_vlc_path() -> None:
    """Помогает Windows найти libvlc.dll, если VLC установлен в стандартную папку."""
    if sys.platform != "win32":
        return

    possible_paths = [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
    ]

    for path in possible_paths:
        dll_path = Path(path) / "libvlc.dll"
        if dll_path.exists():
            os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(path)
            return


prepare_vlc_path()

try:
    import vlc
except Exception as exc:  # pragma: no cover - зависит от локальной установки VLC
    vlc = None
    VLC_IMPORT_ERROR = exc
else:
    VLC_IMPORT_ERROR = None


class SearchWorker(QObject):
    finished = pyqtSignal(list, str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        query: str,
        country_code: str,
        tag_or_language: str,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> None:
        super().__init__()
        self.query = query
        self.country_code = country_code
        self.tag_or_language = tag_or_language
        self.limit = limit
        self.client = RadioBrowserClient()

    def run(self) -> None:
        try:
            stations = self.client.search(
                query=self.query,
                country_code=self.country_code,
                tag_or_language=self.tag_or_language,
                limit=self.limit,
            )
            self.finished.emit(stations, self.client.warning_message)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.client.close()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1120, 720)

        self.favorites_store = FavoritesStore(FAVORITES_FILE)
        self.custom_stations_store = FavoritesStore(CUSTOM_STATIONS_FILE)
        self.stations: list[Station] = []
        self.favorites: list[Station] = self.favorites_store.load()
        self.custom_stations: list[Station] = self.custom_stations_store.load()
        self.current_station: Station | None = None

        self.search_thread: QThread | None = None
        self.search_worker: SearchWorker | None = None

        self.vlc_instance = None
        self.player = None
        self.media_list_player = None
        self._init_player()
        self._build_ui()
        self._build_menu()
        if self.custom_stations:
            self.show_custom_stations()
        self.search_stations()

    def _init_player(self) -> None:
        global VLC_IMPORT_ERROR

        if vlc is None:
            return

        try:
            self.vlc_instance = vlc.Instance("--no-video", "--quiet")
            if self.vlc_instance is None:
                raise RuntimeError("libVLC did not create an instance")

            self.player = self.vlc_instance.media_player_new()
            if self.player is None:
                raise RuntimeError("libVLC did not create a media player")

            self.media_list_player = self.vlc_instance.media_list_player_new()
            if self.media_list_player is None:
                raise RuntimeError("libVLC did not create a media list player")
            self.media_list_player.set_media_player(self.player)

            self.player.audio_set_volume(70)
        except Exception as exc:
            VLC_IMPORT_ERROR = exc
            self.vlc_instance = None
            self.player = None
            self.media_list_player = None

    def _build_menu(self) -> None:
        menu = self.menuBar()
        app_menu = menu.addMenu("Приложение")

        reload_action = QAction("Обновить поиск", self)
        reload_action.triggered.connect(self.search_stations)
        app_menu.addAction(reload_action)

        fav_action = QAction("Показать избранное", self)
        fav_action.triggered.connect(self.show_favorites)
        app_menu.addAction(fav_action)

        custom_action = QAction("Добавить свою станцию", self)
        custom_action.triggered.connect(self.add_custom_station)
        app_menu.addAction(custom_action)

        show_custom_action = QAction("Показать мои станции", self)
        show_custom_action.triggered.connect(self.show_custom_stations)
        app_menu.addAction(show_custom_action)

        stop_action = QAction("Остановить", self)
        stop_action.triggered.connect(self.stop_radio)
        app_menu.addAction(stop_action)

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)

        search_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Название станции, например: relax, rock, europa plus")
        self.search_input.returnPressed.connect(self.search_stations)

        self.country_box = QComboBox()
        self.country_box.addItems(COUNTRIES.keys())

        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Тег/жанр или язык: rock, news, pop, dance, english")
        self.tag_input.returnPressed.connect(self.search_stations)

        self.search_button = QPushButton("Найти")
        self.search_button.clicked.connect(self.search_stations)

        self.favorites_button = QPushButton("Избранное")
        self.favorites_button.clicked.connect(self.show_favorites)

        self.custom_button = QPushButton("Своя станция")
        self.custom_button.clicked.connect(self.add_custom_station)

        search_row.addWidget(QLabel("Поиск:"))
        search_row.addWidget(self.search_input, 3)
        search_row.addWidget(QLabel("Страна:"))
        search_row.addWidget(self.country_box, 1)
        search_row.addWidget(QLabel("Жанр/язык:"))
        search_row.addWidget(self.tag_input, 2)
        search_row.addWidget(self.search_button)
        search_row.addWidget(self.favorites_button)
        search_row.addWidget(self.custom_button)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Станция", "Страна вещания", "Язык", "Codec", "Bitrate", "Votes", "URL"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.play_selected_station)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        controls = QHBoxLayout()
        self.play_button = QPushButton("▶ Играть")
        self.play_button.clicked.connect(self.play_selected_station)

        self.stop_button = QPushButton("■ Стоп")
        self.stop_button.clicked.connect(self.stop_radio)

        self.favorite_button = QPushButton("☆ В избранное")
        self.favorite_button.clicked.connect(self.toggle_favorite)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.set_volume)

        controls.addWidget(self.play_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.favorite_button)
        controls.addWidget(QLabel("Громкость:"))
        controls.addWidget(self.volume_slider, 1)

        self.now_label = QLabel("Сейчас ничего не играет")
        self.status_label = QLabel("Готово")

        root.addLayout(search_row)
        root.addWidget(self.table)
        root.addLayout(controls)
        root.addWidget(self.now_label)
        root.addWidget(self.status_label)

        self.setCentralWidget(central)

    def set_ui_busy(self, busy: bool) -> None:
        self.search_button.setDisabled(busy)
        self.favorites_button.setDisabled(busy)
        self.search_input.setDisabled(busy)
        self.tag_input.setDisabled(busy)
        self.country_box.setDisabled(busy)

    def search_stations(self) -> None:
        if self.search_thread is not None and self.search_thread.isRunning():
            self.status_label.setText("Поиск уже выполняется...")
            return

        query = self.search_input.text().strip()
        tag = self.tag_input.text().strip()
        country_code = COUNTRIES.get(self.country_box.currentText(), "")

        self.status_label.setText("Ищу станции в онлайн-каталогах и плейлистах...")
        self.set_ui_busy(True)

        self.search_thread = QThread()
        self.search_worker = SearchWorker(query, country_code, tag)
        self.search_worker.moveToThread(self.search_thread)

        self.search_thread.started.connect(self.search_worker.run)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.failed.connect(self.on_search_failed)

        self.search_worker.finished.connect(self.search_thread.quit)
        self.search_worker.finished.connect(self.search_worker.deleteLater)
        self.search_worker.failed.connect(self.search_thread.quit)
        self.search_worker.failed.connect(self.search_worker.deleteLater)
        self.search_thread.finished.connect(self.search_thread.deleteLater)
        self.search_thread.finished.connect(self.on_search_thread_finished)

        self.search_thread.start()

    def on_search_thread_finished(self) -> None:
        self.search_thread = None
        self.search_worker = None

    def on_search_finished(self, stations: list[Station], warning_message: str = "") -> None:
        self.set_ui_busy(False)
        self.stations = self._with_custom_stations(stations)
        self.fill_table(self.stations)
        if warning_message:
            self.status_label.setText(
                f"Найдено станций: {len(self.stations)}. Часть источников недоступна."
            )
        else:
            self.status_label.setText(f"Найдено станций: {len(self.stations)}")

    def on_search_failed(self, message: str) -> None:
        self.set_ui_busy(False)
        self.stations = self.custom_stations.copy()
        self.fill_table(self.stations)
        if self.stations:
            self.status_label.setText(
                f"Онлайн-поиск недоступен, показаны мои станции: {len(self.stations)}"
            )
            return
        self.status_label.setText(f"Ошибка поиска: {message}")

    def add_custom_station(self) -> None:
        playlist_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Выбери плейлист своей станции",
            str(Path.home()),
            "Плейлисты (*.m3u *.m3u8 *.pls *.xspf);;Все файлы (*.*)",
        )
        if not playlist_path:
            return

        default_name = Path(playlist_path).stem
        station_name, accepted = QInputDialog.getText(
            self,
            "Своя станция",
            "Название станции:",
            QLineEdit.EchoMode.Normal,
            default_name,
        )
        if not accepted:
            return

        try:
            station = create_custom_station(station_name, playlist_path)
        except ValueError as exc:
            QMessageBox.warning(self, "Не удалось добавить станцию", str(exc))
            return

        self.custom_stations = [
            item
            for item in self.custom_stations
            if not self._same_station(item, station)
        ]
        self.custom_stations.append(station)
        self.custom_stations_store.save(self.custom_stations)
        self.stations = self._with_custom_stations(self.stations)
        self.fill_table(self.stations)
        self.status_label.setText(f"Добавлена своя станция: {station.name}")

    def show_custom_stations(self) -> None:
        self.custom_stations = self.custom_stations_store.load()
        self.stations = self.custom_stations.copy()
        self.fill_table(self.stations)
        self.status_label.setText(f"Мои станции: {len(self.custom_stations)}")

    def _with_custom_stations(self, stations: list[Station]) -> list[Station]:
        result = self.custom_stations.copy()
        for station in stations:
            if not any(self._same_station(custom, station) for custom in result):
                result.append(station)
        return result

    def fill_table(self, stations: list[Station]) -> None:
        self.table.setRowCount(0)
        for station in stations:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                station.name,
                self._broadcast_country(station),
                station.language,
                station.codec,
                str(station.bitrate),
                str(station.votes),
                station.url,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, station)
                self.table.setItem(row, col, item)

    def get_selected_station(self) -> Station | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        item = self.table.item(row, 0)
        if item is None:
            return None
        station = item.data(Qt.ItemDataRole.UserRole)
        return station if isinstance(station, Station) else None

    def on_selection_changed(self) -> None:
        station = self.get_selected_station()
        if not station:
            return
        self.current_station = station
        self.update_favorite_button()

    def play_selected_station(self) -> None:
        station = self.get_selected_station()
        if station is None:
            QMessageBox.information(self, "Станция не выбрана", "Выбери станцию из списка.")
            return
        self.play_station(station)

    def play_station(self, station: Station) -> None:
        if vlc is None or self.player is None or self.vlc_instance is None:
            QMessageBox.critical(
                self,
                "VLC не найден",
                "Не удалось загрузить python-vlc/libVLC. Установи VLC Media Player x64 и перезапусти приложение.\n\n"
                f"Ошибка: {VLC_IMPORT_ERROR}",
            )
            return

        if not station.url:
            QMessageBox.warning(self, "Нет URL", "У этой станции нет адреса потока.")
            return

        self.stop_radio(silent=True)

        playlist_items = self._playlist_items(station.url)
        if playlist_items:
            result = self._play_playlist_items(playlist_items)
        else:
            playable_url = self._playable_url(station.url)
            media = self.vlc_instance.media_new(playable_url)
            self.player.set_media(media)
            self.player.audio_set_volume(self.volume_slider.value())
            result = self.player.play()

        self.current_station = station
        self.now_label.setText(f"Сейчас играет: {station.name}")
        self.status_label.setText("Запуск потока...")
        self.update_favorite_button()

        if result == -1:
            QMessageBox.warning(
                self,
                "Ошибка",
                "VLC не смог запустить поток этой станции.",
            )
            self.status_label.setText("Не удалось запустить поток")
        else:
            self.status_label.setText("Играет")

    def stop_radio(self, silent: bool = False) -> None:
        if self.media_list_player is not None:
            self.media_list_player.stop()
        if self.player is not None:
            self.player.stop()
        if not silent:
            self.now_label.setText("Сейчас ничего не играет")
            self.status_label.setText("Остановлено")

    def set_volume(self, value: int) -> None:
        if self.player is not None:
            self.player.audio_set_volume(value)

    def toggle_favorite(self) -> None:
        station = self.current_station or self.get_selected_station()
        if not station:
            QMessageBox.information(self, "Нет станции", "Сначала выбери станцию.")
            return

        if self._is_favorite(station):
            self.favorites = [
                item
                for item in self.favorites
                if not self._same_station(item, station)
            ]
            self.status_label.setText("Удалено из избранного")
        else:
            self.favorites.append(station)
            self.status_label.setText("Добавлено в избранное")

        self.favorites_store.save(self.favorites)
        self.update_favorite_button()

    def update_favorite_button(self) -> None:
        station = self.current_station or self.get_selected_station()
        if not station:
            self.favorite_button.setText("☆ В избранное")
            return

        self.favorite_button.setText(
            "★ Убрать из избранного" if self._is_favorite(station) else "☆ В избранное"
        )

    def show_favorites(self) -> None:
        self.favorites = self.favorites_store.load()
        self.stations = self.favorites
        self.fill_table(self.favorites)
        self.status_label.setText(f"Избранных станций: {len(self.favorites)}")

    def closeEvent(self, event) -> None:  # noqa: N802 - метод Qt
        self.stop_radio(silent=True)
        event.accept()

    def _is_favorite(self, station: Station) -> bool:
        return any(self._same_station(item, station) for item in self.favorites)

    @staticmethod
    def _same_station(first: Station, second: Station) -> bool:
        return bool(first.uuid and first.uuid == second.uuid) or bool(first.url and first.url == second.url)

    @staticmethod
    def _broadcast_country(station: Station) -> str:
        return station.country or station.countrycode or "Не указана"

    @staticmethod
    def _playable_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme != "file":
            return url

        local_path = unquote(parsed.path)
        if os.name == "nt" and local_path.startswith("/") and len(local_path) > 2:
            local_path = local_path[1:]
        local_path = local_path.replace("/", os.sep)
        return local_path

    @staticmethod
    def _playlist_items(url: str) -> list[str]:
        path = MainWindow._local_file_path(url)
        if path is None or path.suffix.casefold() not in {".m3u", ".m3u8"}:
            return []

        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = path.read_text(encoding="cp1251")
        except OSError:
            return []

        return [MainWindow._playable_url(station.url) for station in parse_m3u(content)]

    @staticmethod
    def _local_file_path(url: str) -> Path | None:
        parsed = urlparse(url)
        if parsed.scheme != "file":
            return None

        local_path = unquote(parsed.path)
        if os.name == "nt" and local_path.startswith("/") and len(local_path) > 2:
            local_path = local_path[1:]
        return Path(local_path.replace("/", os.sep))

    def _play_playlist_items(self, items: list[str]) -> int:
        if (
            self.vlc_instance is None
            or self.player is None
            or self.media_list_player is None
        ):
            return -1

        media_list = self.vlc_instance.media_list_new()
        for item in items:
            media_list.add_media(self.vlc_instance.media_new(item))

        self.media_list_player.set_media_list(media_list)
        self.media_list_player.set_media_player(self.player)
        self.player.audio_set_volume(self.volume_slider.value())
        return self.media_list_player.play()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
