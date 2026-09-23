#!/usr/bin/env python3
# 小小的游戏屋 · 本地小服务器（Python 标准库，无需安装任何依赖）
# 运行:  python3 server.py
# 打开:  http://localhost:8123
import os
import re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 8123))

# 子路径 → 项目目录（都挂在本服务器下，iframe 同源可直接交互）
ROUTES = [
    ("/shadertoy/", os.path.join(ROOT, "shadertoy-1d-radial-lightmap")),
    ("/lifebook/", os.path.join(ROOT, "lifebook", "dist")),
    ("/water/", os.path.join(ROOT, "webgpu-compute-water")),
]

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".glb": "model/gltf-binary",
    ".gltf": "model/gltf+json",
    ".hdr": "application/octet-stream",
    ".bin": "application/octet-stream",
    ".wasm": "application/wasm",
    ".txt": "text/plain; charset=utf-8",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def resolve(self):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            return os.path.join(ROOT, "index.html")
        route = next(
            (r for r in ROUTES if path == r[0].rstrip("/") or path.startswith(r[0])),
            None,
        )
        if route is not None:
            rel = path[len(route[0]):] or "index.html"
            base = route[1]
        else:
            # 其余文件按站点根目录静态兜底（fonts/、README 等）
            base = ROOT
            rel = path.lstrip("/")
        file = os.path.normpath(os.path.join(base, rel))
        # 防目录穿越
        if not (file == base or file.startswith(base + os.sep)):
            return None
        if os.path.isdir(file):
            file = os.path.join(file, "index.html")
        return file if os.path.isfile(file) else None

    def do_GET(self):
        file = self.resolve()
        if file is None:
            self.send_error(404, "Not Found")
            return
        size = os.path.getsize(file)
        ctype = MIME.get(os.path.splitext(file)[1].lower(), "application/octet-stream")

        # Range 支持（音频拖动进度条需要）
        start, end, partial = 0, size - 1, False
        range_header = self.headers.get("Range")
        if range_header:
            m = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else size - 1
                elif m.group(2):  # bytes=-N
                    start = max(size - int(m.group(2)), 0)
                if start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                end = min(end, size - 1)
                partial = True

        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()

        with open(file, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                remaining -= len(chunk)

    def do_HEAD(self):
        file = self.resolve()
        if file is None:
            self.send_error(404, "Not Found")
            return
        size = os.path.getsize(file)
        ctype = MIME.get(os.path.splitext(file)[1].lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass  # 安静一点，不刷屏


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"小小的游戏屋已开门 → http://localhost:{PORT}")
    print(f"  · 追光的小屋  http://localhost:{PORT}/shadertoy/")
    print(f"  · 转眼·小书   http://localhost:{PORT}/lifebook/")
    print(f"  · 小鱼的池塘  http://localhost:{PORT}/water/")
    print("（按 Ctrl+C 关门）")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("小屋关门啦，再见 👋")
