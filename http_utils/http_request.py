from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlsplit


@dataclass
class HttpRequest:
    method: str
    full_url: str
    path: str
    http_version: str
    headers: List[str]
    host: str
    port: int
    content_length: int

    @staticmethod
    def parse(request_line: str, headers: List[str]) -> Optional["HttpRequest"]:
        parts = request_line.split(" ")
        if len(parts) < 3:
            return None

        method = parts[0]
        uri = parts[1]
        http_version = parts[2]

        host: Optional[str] = None
        port = 80
        content_length = 0
        new_headers = list(headers)

        for header in headers:
            lower = header.lower()
            if lower.startswith("host:"):
                value = header[5:].strip()
                host = value
                if ":" in value:
                    hp = value.rsplit(":", 1)
                    host = hp[0].strip()
                    try:
                        port = int(hp[1].strip())
                    except ValueError:
                        pass
            elif lower.startswith("content-length:"):
                value = header[len("content-length:") :].strip()
                try:
                    content_length = int(value)
                except ValueError:
                    pass

        if uri.startswith("http://") or uri.startswith("https://"):
            try:
                parsed = urlsplit(uri)
            except ValueError:
                return None

            full_url = uri
            path = parsed.path or "/"
            if parsed.query:
                path += f"?{parsed.query}"

            if host is None:
                host = parsed.hostname
            if parsed.port is not None:
                port = parsed.port
            elif parsed.scheme == "https":
                port = 443
            else:
                port = 80 if port == 80 else port

            has_host_header = any(h.lower().startswith("host:") for h in new_headers)
            if not has_host_header and host is not None:
                host_header = f"Host: {host}"
                if parsed.port is not None:
                    host_header += f":{parsed.port}"
                new_headers.append(host_header)
        else:
            if host is None:
                return None
            full_url = f"http://{host}{uri}"
            path = uri

        if host is None:
            return None

        return HttpRequest(
            method=method,
            full_url=full_url,
            path=path,
            http_version=http_version,
            headers=new_headers,
            host=host,
            port=port,
            content_length=content_length,
        )
