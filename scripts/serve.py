"""Serve the dashboard locally (project root)."""

from __future__ import annotations

import argparse
import http.server
import socket
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _pick_port(preferred: int) -> int:
    port = preferred
    for _ in range(50):
        if _port_available(port):
            return port
        port += 1
    raise RuntimeError("No free port found in preferred+50 range")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    port = _pick_port(args.port)
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"Dashboard: http://127.0.0.1:{port}/public/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
