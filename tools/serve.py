"""
Локальный HTTP-сервер с поддержкой Range-запросов: через file:// и через
`python3 -m http.server` (без Range) браузеры часто не дают перематывать mp3.

    python3 tools/serve.py books/<slug>        # http://localhost:8934/
    python3 tools/serve.py web                 # личный сайт со всеми книгами
    python3 tools/serve.py docs --port 8000    # предпросмотр GitHub Pages
"""
import argparse
import functools
import http.server
import os
import re
import socketserver


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send_head(self):
        self._range = None
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        if not os.path.exists(path):
            self.send_error(404, "File not found")
            return None
        size = os.stat(path).st_size
        f = open(path, "rb")
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
        if m:
            start = int(m.group(1)) if m.group(1) else 0
            end = min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            length = end - start + 1
            f.seek(start)
            self._range = length
        else:
            self.send_response(200)
            length = size
        self.send_header("Content-type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        if self._range is None:
            return super().copyfile(source, outputfile)
        remaining = self._range
        while remaining > 0:
            chunk = source.read(min(65536, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", nargs="?", default=".")
    ap.add_argument("--port", type=int, default=8934)
    args = ap.parse_args()
    handler = functools.partial(RangeHandler, directory=os.path.abspath(args.dir))
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"http://localhost:{args.port}/  ({os.path.abspath(args.dir)})")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
