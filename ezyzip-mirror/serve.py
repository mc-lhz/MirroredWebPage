#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ezyzip 离线镜像本地服务（127.0.0.1）。
用法：python serve.py [port]，默认 8080。浏览器开 http://127.0.0.1:8080/
"""
import os, sys, mimetypes
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mirror")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

MIME = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".html": "text/html; charset=utf-8",
}

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIME.get(ext, mimetypes.guess_type(path)[0] or "application/octet-stream")

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    os.chdir(ROOT)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print("ezyzip offline mirror serving at http://127.0.0.1:%d/  (Ctrl+C to stop)" % PORT)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
