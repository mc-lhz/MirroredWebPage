#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serve.py — 让真·draw.io 在本地跑起来（离线镜像）。

为什么需要它：draw.io 用 XHR 加载 resources/*.txt、mxgraph 等本地资源，
而 Chrome 在 file:// 下会拦截 file 协议的 XHR（CORS），导致编辑器无法初始化。
用本服务以 http:// 同源提供镜像目录即可绕开该限制——核心绘图完全本地、不依赖云端。

启动：
    python serve.py            # 默认 127.0.0.1:8080
    python serve.py 9000       # 自定义端口
然后浏览器打开 http://127.0.0.1:8080/index.html

说明：
- 仅绑定 127.0.0.1（本机）。
- 禁缓存（Cache-Control: no-store），便于改完镜像即时看到效果。
- /save、/import、/proxy、/open、/notifications、/rt 是 draw.io 的「服务端端点」
  （保存/打开/云集成等），离线本就不支持，统一返回 200 空响应避免 JS 报错。
- 其他所有**无扩展名**的路径（/microsoft?getState=1、/google、/dropbox、/github、
  /gitlab、/rt …）都是 draw.io 的服务端 API 端点，统一返回合法空 JSON `{}`，
  让云客户端判定为「未登录」，使「保存」弹窗默认落到 Device（本地下载）。
- 云端集成（Google Drive / Dropbox / OneDrive / GitHub）在此离线环境下不可用，
  属预期；其余核心绘图、导出 PNG/SVG、本地 .drawio 文件导入导出均可离线使用。
"""

import os
import sys
import http.server
import socketserver
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
MIRROR_DIR = os.path.join(ROOT, "mirror")

# draw.io 会把请求发往这些「服务端端点」，离线返回 200 空即可。
DRAWIO_ENDPOINTS = {"/save", "/import", "/proxy", "/open", "/notifications", "/rt"}

MIME = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".gif": "image/gif",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".map": "application/json; charset=utf-8",
    ".wasm": "application/wasm",
}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=MIRROR_DIR, **kwargs)

    def end_headers(self):
        # 禁缓存，方便迭代镜像后即时生效
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        # draw.io 服务端端点：离线环境返回空 200，避免前端报错
        if path in DRAWIO_ENDPOINTS:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        # 其他“无扩展名”的路径都是 draw.io 的服务端 API 端点
        # （如 /microsoft?getState=1、/google、/dropbox、/github、/rt …）。
        # 返回合法空 JSON {}，让云客户端判定为“未登录”，
        # 从而“保存”弹窗默认落到 Device（本地下载），而非卡在云存储 404。
        last_seg = path.rsplit("/", 1)[-1]
        if "." not in last_seg:
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        # 目录请求 → index.html
        if path.endswith("/"):
            self.path = path + "index.html"
        return super().do_POST() if False else super().do_GET()

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIME.get(ext, super().guess_type(path))

    def log_message(self, fmt, *args):
        # 精简日志，避免刷屏
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def main():
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    os.chdir(MIRROR_DIR)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = "http://127.0.0.1:%d/index.html" % port
    print("draw.io 本地镜像已启动：")
    print("  打开 -> %s" % url)
    print("  根目录 -> %s" % MIRROR_DIR)
    print("  按 Ctrl+C 停止。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
        httpd.shutdown()


if __name__ == "__main__":
    main()
