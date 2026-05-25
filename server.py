from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.error
import urllib.parse
import json
import re
import os
from pathlib import Path

PORT    = int(os.environ.get("PORT", 8765))
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

CLAUDE_URL = "https://api.anthropic.com/v1/messages"

SPELL_PROMPT = """한국어 맞춤법 검사기입니다. 아래 텍스트의 맞춤법·띄어쓰기를 검사하고 JSON으로만 응답하세요.

텍스트: {text}

아래 JSON 형식 외에 다른 텍스트는 절대 출력하지 마세요:
{{
  "corrected": "교정된 전체 텍스트",
  "errors": [
    {{"token": "틀린 단어/표현", "suggestion": "올바른 단어/표현", "help": "오류 이유"}}
  ],
  "errorCount": 오류_개수
}}"""

KOREAN_PROMPT = """외래어·영어·한자어를 순우리말로 바꾸는 작업입니다. 아래 텍스트에서 외래어나 외국어 표현을 자연스러운 순우리말로 바꿔주세요.

텍스트: {text}

아래 JSON 형식 외에 다른 텍스트는 절대 출력하지 마세요:
{{
  "converted": "변환된 전체 텍스트",
  "changes": [
    {{"original": "외래어/외국어", "korean": "순우리말", "note": "간단한 설명"}}
  ],
  "changeCount": 변환_개수
}}"""


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/check"):
            self._handle(SPELL_PROMPT)
        elif self.path.startswith("/api/korean"):
            self._handle(KOREAN_PROMPT)
        else:
            super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _handle(self, prompt_template):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        text   = params.get("q", [""])[0]

        if not text.strip():
            return self._json(400, {"error": "텍스트가 없습니다."})
        if not API_KEY:
            return self._json(500, {"error": "서버에 ANTHROPIC_API_KEY가 설정되지 않았습니다."})

        try:
            result = self._call_claude(prompt_template.format(text=text))
            self._json(200, result)
        except urllib.error.HTTPError as e:
            self._json(502, {"error": f"API 오류: {e.code}"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _call_claude(self, prompt):
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        body = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            CLAUDE_URL, data=body,
            headers={
                "x-api-key":           API_KEY,
                "anthropic-version":   "2023-06-01",
                "content-type":        "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            response = json.loads(resp.read().decode("utf-8"))

        raw = response["content"][0]["text"].strip()
        m   = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise ValueError("JSON 파싱 실패")
        return json.loads(m.group(0))

    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

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
