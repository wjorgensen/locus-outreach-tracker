"""Minimal platform test: stdlib HTTP server, no deps."""
from http.server import BaseHTTPRequestHandler, HTTPServer


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("mini server starting on 0.0.0.0:8080", flush=True)
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()
