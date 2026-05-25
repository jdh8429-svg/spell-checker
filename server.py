"""
한글 맞춤법 교정기 서버
- 정적 파일(index.html) 서빙
- 네이버 맞춤법 검사기 프록시 (/api/check?q=TEXT)
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import os
from pathlib import Path

PORT = int(os.environ.get("PORT", 8765))

NAVER_URL = "https://m.search.naver.com/p/csearch/ocontent/spellchecker.nhn"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://search.naver.com/",
    "Origin": "https://search.naver.com",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/check"):
            self._handle_check()
        else:
            super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors()
        self.end_headers()

    # ------------------------------------------------------------------ #

    def _handle_check(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        text = params.get("q", [""])[0]

        if not text.strip():
            return self._json_response(400, {"error": "텍스트가 없습니다."})

        try:
            body = urllib.parse.urlencode({"q": text, "_callback": "nc"}).encode("utf-8")
            req = urllib.request.Request(NAVER_URL, data=body, headers=HEADERS)

            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")

            # 응답 형식: nc({...}) — JSONP 래퍼 제거
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                return self._json_response(502, {"error": "응답 파싱 실패"})

            data = json.loads(m.group(0))
            self._json_response(200, data)

        except urllib.error.HTTPError as e:
            self._json_response(502, {"error": f"네이버 HTTP 오류: {e.code}"})
        except urllib.error.URLError as e:
            self._json_response(502, {"error": f"네이버 연결 실패: {e.reason}"})
        except Exception as e:
            self._json_response(500, {"error": str(e)})

    def _json_response(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors()
        self.end_headers()
        self.wfile.write(body)

    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        pass  # 콘솔 로그 억제


# ------------------------------------------------------------------ #

def main():
    os.chdir(Path(__file__).parent)
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)

    print(f"맞춤법 교정기 서버 실행 중 (port {PORT})")
    print("종료하려면 Ctrl+C 를 누르세요.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버가 종료됐습니다.")
        httpd.server_close()


if __name__ == "__main__":
    main()
