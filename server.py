from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
from pathlib import Path

PORT = int(os.environ.get("PORT", 8765))


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def main():
    os.chdir(Path(__file__).parent)
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"서버 실행 중 (port {PORT})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    main()
