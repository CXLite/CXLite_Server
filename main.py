import socketserver
import sys

from main_callfunc import callfunc
from web_terminal import WebTerminal

from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse

web_terminal = WebTerminal(callfunc)
web_terminal.start()

PORT = 8080
DIRECTORY = "./static"


class MyHttpRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # 解析 URL 并获取查询参数
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        self.path = path

        if self.path == '/':
            self.path = './index.html'
            return super().do_GET()
        else:
            return super().do_GET()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')  # 添加CORS头
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def log_message(self, format, *args):
        # 使用 sys.__stdout__.write 进行日志输出
        sys.__stdout__.write(f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}\n")


handler = MyHttpRequestHandler

with socketserver.TCPServer(("", PORT), handler) as httpd:
    sys.__stdout__.write(f"Serving HTTP on port {PORT}")
    httpd.serve_forever()
