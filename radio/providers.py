from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import Station


class StationProvider(Protocol):
    def search(
        self,
        query: str = "",
        country_code: str = "",
        tag_or_language: str = "",
        limit: int = 100,
    ) -> list[Station]:
        ...

    def close(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class SearchResult:
    stations: list[Station]
    warning_message: str = ""
