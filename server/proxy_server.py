from __future__ import annotations

import socket
import threading

from blacklist.blacklist import Blacklist
from server.client_handler import ClientHandler


class ProxyServer:
    def __init__(self, port: int, blacklist_path: str, bind_ip: str) -> None:
        self.port = port
        self.blacklist = Blacklist(blacklist_path)
        self.bind_ip = bind_ip

    def start(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.bind_ip, self.port))
            server_socket.listen(50)

            print(f"HTTP-прокси запущен на {self.bind_ip}:{self.port}")

            while True:
                client_socket, _ = server_socket.accept()
                handler = ClientHandler(client_socket, self.blacklist)
                thread = threading.Thread(target=handler.run, daemon=True)
                thread.start()
