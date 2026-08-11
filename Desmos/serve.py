import http.server, socketserver, os, webbrowser

PORT = 8137
DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIR)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass  # 静默日志

if __name__ == "__main__":
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        url = f"http://127.0.0.1:{PORT}/"
        print(f"Desmos 离线镜像已启动 -> {url}")
        print("按 Ctrl+C 停止。")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        httpd.serve_forever()
