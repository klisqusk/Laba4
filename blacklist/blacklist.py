from __future__ import annotations

from pathlib import Path
from typing import List


class Blacklist:
    def __init__(self, path: str | Path) -> None:
        self.entries: List[str] = []
        file_path = Path(path)

        if not file_path.exists():
            print(f"Файл чёрного списка не найден: {file_path}")
            return

        try:
            for raw_line in file_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if line and not line.startswith("#"):
                    self.entries.append(line.lower())
            print(f"Загружено {len(self.entries)} записей чёрного списка.")
        except OSError as exc:
            print(f"Ошибка чтения чёрного списка: {exc}")

    def is_blocked(self, url: str, host: str) -> bool:
        url_lower = url.lower()
        host_lower = host.lower()

        for entry in self.entries:
            if entry.startswith("http://") or entry.startswith("https://"):
                if url_lower.startswith(entry):
                    return True
            else:
                if host_lower == entry or host_lower.endswith("." + entry):
                    return True
        return False
