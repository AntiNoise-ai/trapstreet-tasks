#!/usr/bin/env python3
"""Serve this directory over plain HTTP so the site's fetch()-based pages
(bundle tiers, catalog) work correctly -- file:// URLs hit CORS restrictions
on fetch() in most browsers, http:// does not.

This server also gates the underlying data files (games.json,
bundle-data*.json, regions.json, flash-sale.json) behind a per-run session
token: HTML pages get a fresh, random token injected into a <script> tag at
serve time, and the page's own JS sends it back as an X-Nk-Token header on
every fetch to those files. A request without the correct header gets a
403, not the data. This is a deliberately realistic (not theoretically
unbeatable) barrier -- it mirrors how real sites gate their internal APIs
with a CSRF/session token: a bare `curl <known-filename>` fails outright,
while a solution that actually reads/executes the page's JS (a real
browser, or a scraper that bothers to replicate the token flow) gets
through, same as it would on a real site.

Usage: python3 serve.py [port]   (default port 8000)
Then open http://localhost:<port>/index.html
"""
from __future__ import annotations

import http.server
import os
import secrets
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
os.chdir(os.path.dirname(os.path.abspath(__file__)))

SESSION_TOKEN = secrets.token_hex(16)

PROTECTED_PATHS = {"/games.json", "/bundle-data.json", "/bundle-data2.json",
                    "/regions.json", "/flash-sale.json"}


class NebulaKeyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]

        if path in PROTECTED_PATHS:
            sent_token = self.headers.get("X-Nk-Token", "")
            if sent_token != SESSION_TOKEN:
                body = b'{"error": "missing or invalid X-Nk-Token header"}'
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()
            return

        if path.endswith(".html"):
            file_path = self.translate_path(path)
            if not os.path.isfile(file_path):
                self.send_error(404)
                return
            with open(file_path, "rb") as f:
                content = f.read()
            injected = f'<script>window.NK_TOKEN="{SESSION_TOKEN}";</script>'.encode()
            content = content.replace(b"</head>", injected + b"</head>", 1)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        super().do_GET()

    def log_message(self, format: str, *args) -> None:  # quieter test output
        pass


with socketserver.TCPServer(("", PORT), NebulaKeyHandler) as httpd:
    print(f"Serving NebulaKey Store at http://localhost:{PORT}/index.html")
    print(f"(session token: {SESSION_TOKEN})")
    httpd.serve_forever()
