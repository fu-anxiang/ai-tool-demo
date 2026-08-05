"""HTTP entrypoint: exposes /health and /analyze (stdlib only)."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from ai_tool.core import clean_text, sentiment


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._json({"status": "ok"})
        else:
            self._json({"usage": "GET /health | POST /analyze {text: ...}"})

    def do_POST(self):  # noqa: N802
        if self.path == "/analyze":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            text = body.get("text", "")
            self._json({"sentiment": sentiment(text), "cleaned": clean_text(text)})
        else:
            self._json({"error": "not found"}, 404)

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # noqa: D401
        pass


def main():
    print("ai-tool-demo serving on :8080", flush=True)
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()


if __name__ == "__main__":
    main()