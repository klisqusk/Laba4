from __future__ import annotations

import html
import socket
from typing import List, Optional

from blacklist.blacklist import Blacklist
from http_utils.http_request import HttpRequest


class ClientHandler:
    SERVER_SOCKET_TIMEOUT_MS = 30_000
    BUFFER_SIZE = 8 * 1024

    def __init__(self, client_socket: socket.socket, blacklist: Blacklist) -> None:
        self.client_socket = client_socket
        self.blacklist = blacklist

    def run(self) -> None:
        try:
            self.client_socket.settimeout(self.SERVER_SOCKET_TIMEOUT_MS / 1000)

            client_reader = self.client_socket.makefile("rb")
            client_out = self.client_socket.makefile("wb")

            request_line_bytes = client_reader.readline()
            if not request_line_bytes:
                return

            request_line = request_line_bytes.decode("iso-8859-1").rstrip("\r\n")
            if not request_line:
                return

            headers = self._read_headers(client_reader)
            http_request = HttpRequest.parse(request_line, headers)
            if http_request is None:
                return

            full_url = http_request.full_url
            host = http_request.host
            port = http_request.port

            if self.blacklist.is_blocked(full_url, host):
                self._send_blocked_response(client_out, full_url)
                self._log(full_url, 403)
                return

            with socket.create_connection((host, port), timeout=self.SERVER_SOCKET_TIMEOUT_MS / 1000) as server_socket:
                server_socket.settimeout(self.SERVER_SOCKET_TIMEOUT_MS / 1000)

                server_reader = server_socket.makefile("rb")
                server_writer = server_socket.makefile("wb")

                self._send_request_to_server(http_request, server_writer, client_reader)
                self._forward_response(server_reader, client_out, full_url)

        except OSError as exc:
            print(f"Ошибка при обработке клиента: {exc}")
        finally:
            try:
                self.client_socket.close()
            except OSError:
                pass

    def _read_headers(self, reader) -> List[str]:
        headers: List[str] = []
        while True:
            line_bytes = reader.readline()
            if not line_bytes:
                break
            if line_bytes in (b"\r\n", b"\n"):
                break
            headers.append(line_bytes.decode("iso-8859-1").rstrip("\r\n"))
        return headers

    def _send_request_to_server(self, request: HttpRequest, server_writer, client_reader) -> None:
        first_line = f"{request.method} {request.path} {request.http_version}\r\n"
        server_writer.write(first_line.encode("iso-8859-1"))
        for header in request.headers:
            server_writer.write(f"{header}\r\n".encode("iso-8859-1"))
        server_writer.write(b"\r\n")
        server_writer.flush()

        content_length = request.content_length
        if content_length > 0:
            body = client_reader.read(content_length)
            if body:
                server_writer.write(body)
                server_writer.flush()

    def _forward_response(self, server_reader, client_out, url: str) -> None:
        header_buffer = bytearray()
        prev: Optional[int] = None
        headers_ended = False

        while True:
            current = server_reader.read(1)
            if not current:
                break

            cur_value = current[0]
            header_buffer.append(cur_value)

            if prev == 13 and cur_value == 10:
                if len(header_buffer) >= 4 and header_buffer[-4:] == b"\r\n\r\n":
                    headers_ended = True
                    break
            prev = cur_value

        if not headers_ended:
            return

        header_bytes = bytes(header_buffer)
        header_text = header_bytes.decode("iso-8859-1", errors="replace")
        header_lines = header_text.split("\r\n")

        status_code = self._parse_status_code(header_lines)
        self._log(url, status_code)

        client_out.write(header_bytes)
        client_out.flush()

        while True:
            chunk = server_reader.read(self.BUFFER_SIZE)
            if not chunk:
                break
            client_out.write(chunk)
            client_out.flush()

    def _parse_status_code(self, header_lines: List[str]) -> int:
        if not header_lines:
            return 0
        status_line = header_lines[0]
        parts = status_line.split(" ")
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                pass
        return 0

    def _send_blocked_response(self, client_out, url: str) -> None:
        escaped_url = html.escape(url, quote=True)
        body = (
            "<html><body><h2>Доступ к ресурсу заблокирован</h2>"
            f"<p>URL: {escaped_url}</p>"
            "</body></html>"
        )
        body_bytes = body.encode("utf-8")

        response_headers = (
            "HTTP/1.1 403 Forbidden\r\n"
            "Content-Type: text/html; charset=UTF-8\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("iso-8859-1")

        client_out.write(response_headers)
        client_out.write(body_bytes)
        client_out.flush()

    def _log(self, url: str, status_code: int) -> None:
        print(f"URL: {url} | Response: {status_code}")
