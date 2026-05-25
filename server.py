"""
한글 맞춤법 교정기 서버
- 정적 파일(index.html) 서빙
- 부산대 맞춤법 검사기 프록시 (/api/check?q=TEXT)
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.parse
import urllib.error
import json
import os
from pathlib import Path

PORT = int(os.environ.get("PORT", 8765))

PNU_URL = "http://speller.cs.pusan.ac.kr/results"
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "http://speller.cs.pusan.ac.kr/",
}

TYPE_LABELS = {1: "맞춤법", 2: "띄어쓰기", 3: "표준어 의심", 4: "통계적 교정"}


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

    def _handle_check(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        text = params.get("q", [""])[0]

        if not text.strip():
            return self._json_response(400, {"error": "텍스트가 없습니다."})

        try:
            body = urllib.parse.urlencode({"text1": text, "changes": "1"}).encode("utf-8")
            req = urllib.request.Request(PNU_URL, data=body, headers=HEADERS)

            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")

            results = json.loads(raw)

            if not results or not isinstance(results, list):
                return self._json_response(200, {
                    "corrected": text, "errors": [], "errorCount": 0
                })

            result = results[0]
            errors = []

            for err in result.get("errInfo", []):
                cands = err.get("candWord", "").split("|")
                suggestion = cands[0].strip() if cands else ""
                try:
                    error_type = TYPE_LABELS.get(int(err.get("type", 1)), "맞춤법")
                except (ValueError, TypeError):
                    error_type = "맞춤법"
                errors.append({
                    "token":      err.get("token", ""),
                    "suggestion": suggestion,
                    "help":       err.get("help", ""),
                    "type":       error_type,
                    "start":      int(err.get("start", 0)),
                    "end":        int(err.get("end", 0)),
                })

            self._json_response(200, {
                "corrected":  result.get("str", text),
                "errors":     errors,
                "errorCount": len(errors),
            })

        except urllib.error.HTTPError as e:
            self._json_response(502, {"error": f"맞춤법 서버 오류: {e.code}"})
        except urllib.error.URLError as e:
            self._json_response(502, {"error": f"맞춤법 서버 연결 실패: {e.reason}"})
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
        pass


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
