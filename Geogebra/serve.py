import http.server, socketserver, os

PORT = 8138
DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIR)


class Handler(http.server.SimpleHTTPRequestHandler):
    # 关键：禁止浏览器缓存，确保每次都拿到最新的 index.html / 资源
    # （否则旧的 index.html 会被缓存，导致修复后页面仍显示“混乱”旧版）
    def end_headers(self):
        self.send_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        url = f"http://127.0.0.1:{PORT}/"
        print(f"GeoGebra 离线镜像已启动 -> {url}")
        print("按 Ctrl+C 停止。")
        httpd.serve_forever()
