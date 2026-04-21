from __future__ import annotations

import sys
from pathlib import Path

from config import BIND_IP, BLACKLIST_PATH, PORT
from server.proxy_server import ProxyServer


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    blacklist_path = str(base_dir / BLACKLIST_PATH)

    port = PORT
    bind_ip = BIND_IP

    if len(sys.argv) >= 2:
        bind_ip = sys.argv[1]
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])

    try:
        proxy_server = ProxyServer(port=port, blacklist_path=blacklist_path, bind_ip=bind_ip)
        proxy_server.start()
    except OSError as exc:
        print(f"Ошибка при запуске прокси-сервера: {exc}")


if __name__ == "__main__":
    main()
