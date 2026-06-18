import json
import os
import sys
import socket
from pathlib import Path
from typing import Any

import httpx
import pyradios
import pyradios.radios as pyradios_radios
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
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


APP_NAME = "All Radio Python"
APP_DIR = Path.home() / ".all_radio_python"
FAVORITES_FILE = APP_DIR / "favorites.json"

RADIO_BROWSER_HTTPS_SERVERS = [
    "https://de1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://at1.api.radio-browser.info",
]

# HTTP нужен как запасной вариант. Иногда на Windows/у провайдера/через прокси
# HTTPS-узел Radio Browser отваливается ошибкой SSL EOF, как на at1.api.radio-browser.info.
# Для каталога радиостанций здесь нет логина/пароля, поэтому такой fallback допустимее,
# чем отключать проверку SSL-сертификатов через verify=False.
RADIO_BROWSER_HTTP_FALLBACK_SERVERS = [
    "http://all.api.radio-browser.info",
    "http://de1.api.radio-browser.info",
    "http://nl1.api.radio-browser.info",
    "http://at1.api.radio-browser.info",
]

LOCAL_HTTP_PROXY_PORTS = (7897, 7890, 10809, 8080)

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

FALLBACK_STATIONS = [
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


class PyRadiosClient:
    def __init__(self) -> None:
        self.browsers = self._build_browsers()
        self.warning_message = ""

    @staticmethod
    def _unique(items: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in items:
            item = item.strip().rstrip("/")
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @classmethod
    def _base_urls(cls) -> list[str]:
        return cls._unique(
            RADIO_BROWSER_HTTPS_SERVERS + RADIO_BROWSER_HTTP_FALLBACK_SERVERS
        )

    @staticmethod
    def _proxy_url(value: str) -> str | None:
        value = value.strip()
        if not value:
            return None
        if value.lower().startswith("socks"):
            return None
        if "://" not in value:
            return f"http://{value}"
        return value

    @classmethod
    def _windows_proxy_url(cls) -> str | None:
        if sys.platform != "win32":
            return None

        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            ) as key:
                proxy_enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
                proxy_server = winreg.QueryValueEx(key, "ProxyServer")[0]
        except OSError:
            return None

        if not proxy_enabled or not isinstance(proxy_server, str):
            return None

        proxy_server = proxy_server.strip()
        if not proxy_server:
            return None

        if "=" not in proxy_server:
            return cls._proxy_url(proxy_server)

        proxies: dict[str, str] = {}
        for part in proxy_server.split(";"):
            if "=" not in part:
                continue
            protocol, value = part.split("=", 1)
            protocol = protocol.strip().lower()
            if protocol not in {"http", "https"}:
                continue
            proxy_url = cls._proxy_url(value)
            if proxy_url:
                proxies[protocol] = proxy_url

        return proxies.get("https") or proxies.get("http")

    @staticmethod
    def _local_port_open(port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            return False

    @staticmethod
    def _create_httpx_client(
        trust_env: bool,
        proxy_url: str | None = None,
    ) -> httpx.Client:
        options: dict[str, Any] = {
            "timeout": httpx.Timeout(7.0, connect=2.0),
            "trust_env": trust_env,
        }
        if proxy_url:
            options["proxy"] = proxy_url
        return httpx.Client(**options)

    @staticmethod
    def _create_browser(
        base_url: str,
        session: httpx.Client,
    ) -> pyradios.RadioBrowser:
        normalized_url = base_url.rstrip("/") + "/"
        original_pick_base_url = pyradios_radios.pick_base_url
        pyradios_radios.pick_base_url = lambda: normalized_url
        try:
            return pyradios.RadioBrowser(session=session)
        finally:
            pyradios_radios.pick_base_url = original_pick_base_url

    @classmethod
    def _network_modes(cls) -> list[tuple[str, bool, str | None]]:
        modes: list[tuple[str, bool, str | None]] = [("напрямую", False, None)]

        proxy_vars = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")
        has_env_proxy = any(
            os.environ.get(name) or os.environ.get(name.lower())
            for name in proxy_vars
        )
        if has_env_proxy:
            modes.append(("через переменные прокси", True, None))

        windows_proxy_url = cls._windows_proxy_url()
        if windows_proxy_url:
            modes.append(("через прокси Windows", False, windows_proxy_url))

        for port in LOCAL_HTTP_PROXY_PORTS:
            if cls._local_port_open(port):
                proxy_url = f"http://127.0.0.1:{port}"
                modes.append(
                    (f"через локальный прокси 127.0.0.1:{port}", False, proxy_url)
                )

        return modes

    @classmethod
    def _build_browsers(cls) -> list[tuple[str, str, pyradios.RadioBrowser]]:
        browsers: list[tuple[str, str, pyradios.RadioBrowser]] = []
        for mode_name, trust_env, proxy_url in cls._network_modes():
            for base_url in cls._base_urls():
                session = cls._create_httpx_client(
                    trust_env=trust_env,
                    proxy_url=proxy_url,
                )
                browser = cls._create_browser(base_url, session)
                browsers.append((mode_name, base_url, browser))
        return browsers

    @staticmethod
    def _deduplicate_stations(
        stations: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()

        for station in stations:
            key = station.get("uuid") or station.get("url") or station.get("name", "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            result.append(station)
            if len(result) >= limit:
                break

        return result

    @staticmethod
    def _matches_text(station: dict[str, Any], value: str) -> bool:
        if not value:
            return True

        value = value.casefold()
        searchable = " ".join(
            str(station.get(key, ""))
            for key in ("name", "country", "language", "tags", "codec")
        ).casefold()
        return value in searchable

    @classmethod
    def _fallback_search(
        cls,
        query: str,
        country_code: str,
        tag_or_language: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        for station in FALLBACK_STATIONS:
            if country_code and station.get("countrycode") != country_code:
                continue
            if not cls._matches_text(station, query):
                continue
            if not cls._matches_text(station, tag_or_language):
                continue

            result.append(station.copy())
            if len(result) >= limit:
                break

        return result

    def search(
        self,
        query: str = "",
        country_code: str = "",
        tag_or_language: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "limit": limit,
            "hidebroken": True,
            "order": "clickcount",
            "reverse": True,
        }

        query = query.strip()
        tag_or_language = tag_or_language.strip()

        if query:
            params["name"] = query
        if country_code:
            params["countrycode"] = country_code

        search_variants = [params]
        if tag_or_language:
            search_variants = []
            for key in ("tag", "language"):
                variant = params.copy()
                variant[key] = tag_or_language
                search_variants.append(variant)

        last_error: Exception | None = None
        errors: list[str] = []

        for mode_name, base_url, browser in self.browsers:
            stations: list[dict[str, Any]] = []
            variant_errors: list[str] = []
            successful_requests = 0

            for variant in search_variants:
                if "language" in variant:
                    variant_name = "language"
                elif "tag" in variant:
                    variant_name = "tag"
                else:
                    variant_name = "search"

                try:
                    data = browser.search(**variant)
                    if not isinstance(data, list):
                        raise RuntimeError("pyradios вернул неожиданный формат данных")
                    stations.extend(
                        self._normalize_station(item)
                        for item in data
                        if isinstance(item, dict)
                    )
                    successful_requests += 1
                except Exception as exc:
                    last_error = exc
                    variant_errors.append(f"{variant_name}: {exc}")

            if successful_requests:
                return self._deduplicate_stations(stations, limit)

            if variant_errors:
                errors.append(
                    f"{mode_name}; {base_url}: {'; '.join(variant_errors)}"
                )

        details = "\n".join(errors[-6:])
        modes = ", ".join(
            self._unique([name for name, _url, _browser in self.browsers])
        )
        self.warning_message = (
            "pyradios сейчас недоступен, показан резервный список станций. "
            f"Последняя ошибка: {last_error}"
        )
        fallback_stations = self._fallback_search(
            query=query,
            country_code=country_code,
            tag_or_language=tag_or_language,
            limit=limit,
        )
        if fallback_stations:
            return fallback_stations

        self.warning_message = (
            "pyradios сейчас недоступен, под выбранные фильтры ничего не найдено, "
            "показан общий резервный список станций."
        )
        fallback_stations = [station.copy() for station in FALLBACK_STATIONS[:limit]]
        if fallback_stations:
            return fallback_stations

        raise RuntimeError(
            "Не удалось получить станции через pyradios, а в резервном списке "
            "нет станций под выбранные фильтры.\n\n"
            f"Проверенные режимы: {modes}\n\n"
            f"Последняя ошибка: {last_error}\n\n"
            f"Проверенные попытки:\n{details}"
        )

    def close(self) -> None:
        for _mode_name, _base_url, browser in self.browsers:
            session = getattr(browser.client, "_session", None)
            if hasattr(session, "close"):
                session.close()

    @staticmethod
    def _normalize_station(item: dict[str, Any]) -> dict[str, Any]:
        stream_url = item.get("url_resolved") or item.get("url") or ""
        return {
            "uuid": item.get("stationuuid") or "",
            "name": item.get("name") or "Без названия",
            "url": stream_url,
            "homepage": item.get("homepage") or "",
            "favicon": item.get("favicon") or "",
            "country": item.get("country") or "",
            "countrycode": item.get("countrycode") or "",
            "language": item.get("language") or "",
            "tags": item.get("tags") or "",
            "codec": item.get("codec") or "",
            "bitrate": item.get("bitrate") or 0,
            "votes": item.get("votes") or 0,
        }


class SearchWorker(QObject):
    finished = pyqtSignal(list, str)
    failed = pyqtSignal(str)

    def __init__(self, query: str, country_code: str, tag_or_language: str):
        super().__init__()
        self.query = query
        self.country_code = country_code
        self.tag_or_language = tag_or_language
        self.client = PyRadiosClient()

    def run(self) -> None:
        try:
            stations = self.client.search(
                query=self.query,
                country_code=self.country_code,
                tag_or_language=self.tag_or_language,
            )
            self.finished.emit(stations, self.client.warning_message)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.client.close()


class FavoritesStore:
    @staticmethod
    def load() -> list[dict[str, Any]]:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if not FAVORITES_FILE.exists():
            return []
        try:
            data = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @staticmethod
    def save(stations: list[dict[str, Any]]) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        FAVORITES_FILE.write_text(
            json.dumps(stations, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1120, 720)

        self.stations: list[dict[str, Any]] = []
        self.favorites: list[dict[str, Any]] = FavoritesStore.load()
        self.current_station: dict[str, Any] | None = None

        self.search_thread: QThread | None = None
        self.search_worker: SearchWorker | None = None

        self.vlc_instance = None
        self.player = None
        self._init_player()
        self._build_ui()
        self._build_menu()
        self.show_fallback_stations(
            "Показан резервный список. Нажми «Найти», чтобы загрузить станции через pyradios."
        )

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

            self.player.audio_set_volume(70)
        except Exception as exc:
            VLC_IMPORT_ERROR = exc
            self.vlc_instance = None
            self.player = None

    def _build_menu(self) -> None:
        menu = self.menuBar()
        app_menu = menu.addMenu("Приложение")

        reload_action = QAction("Обновить поиск", self)
        reload_action.triggered.connect(self.search_stations)
        app_menu.addAction(reload_action)

        fav_action = QAction("Показать избранное", self)
        fav_action.triggered.connect(self.show_favorites)
        app_menu.addAction(fav_action)

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
        self.tag_input.setPlaceholderText("Тег/жанр: rock, news, pop, dance")
        self.tag_input.returnPressed.connect(self.search_stations)

        self.search_button = QPushButton("Найти")
        self.search_button.clicked.connect(self.search_stations)

        self.favorites_button = QPushButton("Избранное")
        self.favorites_button.clicked.connect(self.show_favorites)

        search_row.addWidget(QLabel("Поиск:"))
        search_row.addWidget(self.search_input, 3)
        search_row.addWidget(QLabel("Страна:"))
        search_row.addWidget(self.country_box, 1)
        search_row.addWidget(QLabel("Жанр:"))
        search_row.addWidget(self.tag_input, 2)
        search_row.addWidget(self.search_button)
        search_row.addWidget(self.favorites_button)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Станция", "Страна", "Язык", "Codec", "Bitrate", "Votes", "URL"]
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

        self.status_label.setText("Ищу станции...")
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

    def on_search_finished(
        self,
        stations: list[dict[str, Any]],
        warning_message: str = "",
    ) -> None:
        self.set_ui_busy(False)
        self.stations = stations
        self.fill_table(stations)
        if warning_message:
            self.status_label.setText(
                f"Показан резервный список станций: {len(stations)}"
            )
        else:
            self.status_label.setText(f"Найдено станций: {len(stations)}")

    def on_search_failed(self, message: str) -> None:
        self.set_ui_busy(False)
        if self.show_fallback_stations(
            f"pyradios недоступен, показан резервный список: {len(FALLBACK_STATIONS)}"
        ):
            return

        self.status_label.setText(f"Ошибка поиска: {message}")

    def show_fallback_stations(self, status: str) -> bool:
        fallback_stations = [station.copy() for station in FALLBACK_STATIONS]
        if not fallback_stations:
            return False

        self.stations = fallback_stations
        self.fill_table(fallback_stations)
        self.status_label.setText(status)
        return True

    def fill_table(self, stations: list[dict[str, Any]]) -> None:
        self.table.setRowCount(0)
        for station in stations:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                station.get("name", ""),
                station.get("country", ""),
                station.get("language", ""),
                station.get("codec", ""),
                str(station.get("bitrate", "")),
                str(station.get("votes", "")),
                station.get("url", ""),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, station)
                self.table.setItem(row, col, item)

    def get_selected_station(self) -> dict[str, Any] | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        item = self.table.item(row, 0)
        if item is None:
            return None
        station = item.data(Qt.ItemDataRole.UserRole)
        return station if isinstance(station, dict) else None

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

    def play_station(self, station: dict[str, Any]) -> None:
        if vlc is None or self.player is None or self.vlc_instance is None:
            QMessageBox.critical(
                self,
                "VLC не найден",
                "Не удалось загрузить python-vlc/libVLC. Установи VLC Media Player x64 и перезапусти приложение.\n\n"
                f"Ошибка: {VLC_IMPORT_ERROR}",
            )
            return

        stream_url = station.get("url", "")
        if not stream_url:
            QMessageBox.warning(self, "Нет URL", "У этой станции нет адреса потока.")
            return

        self.stop_radio(silent=True)
        media = self.vlc_instance.media_new(stream_url)
        self.player.set_media(media)
        self.player.audio_set_volume(self.volume_slider.value())
        result = self.player.play()

        self.current_station = station
        self.now_label.setText(f"Сейчас играет: {station.get('name', 'Без названия')}")
        self.status_label.setText("Запуск потока...")
        self.update_favorite_button()

        if result == -1:
            QMessageBox.warning(self, "Ошибка", "VLC не смог запустить поток этой станции.")
            self.status_label.setText("Не удалось запустить поток")
        else:
            self.status_label.setText("Играет")

    def stop_radio(self, silent: bool = False) -> None:
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

        uuid = station.get("uuid", "")
        url = station.get("url", "")

        def same_station(item: dict[str, Any]) -> bool:
            return bool(uuid and item.get("uuid") == uuid) or bool(url and item.get("url") == url)

        if any(same_station(item) for item in self.favorites):
            self.favorites = [item for item in self.favorites if not same_station(item)]
            self.status_label.setText("Удалено из избранного")
        else:
            self.favorites.append(station)
            self.status_label.setText("Добавлено в избранное")

        FavoritesStore.save(self.favorites)
        self.update_favorite_button()

    def update_favorite_button(self) -> None:
        station = self.current_station or self.get_selected_station()
        if not station:
            self.favorite_button.setText("☆ В избранное")
            return

        uuid = station.get("uuid", "")
        url = station.get("url", "")
        is_favorite = any(
            (uuid and item.get("uuid") == uuid) or (url and item.get("url") == url)
            for item in self.favorites
        )
        self.favorite_button.setText(
            "★ Убрать из избранного" if is_favorite else "☆ В избранное"
        )

    def show_favorites(self) -> None:
        self.favorites = FavoritesStore.load()
        self.stations = self.favorites
        self.fill_table(self.favorites)
        self.status_label.setText(f"Избранных станций: {len(self.favorites)}")

    def closeEvent(self, event) -> None:  # noqa: N802 - метод Qt
        self.stop_radio(silent=True)
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
