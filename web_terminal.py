import sys

from websockets.sync.server import serve

from api.logger import logger
from webscoket_io import WebScoketIO
import threading


class WebTerminal:
    def __init__(self, _callfunc):
        self.server = None
        self.callfunc = _callfunc
        self.websocket = None
        self.websocket_init = False
        self.websocket_io = None
        self.end = False

    def websocket_callback(self, websocket):
        # 初始化websocket相关
        if not self.websocket_init:
            self.websocket_init = True
            self.websocket = websocket
            self.websocket_io = WebScoketIO(websocket)
            threading.Thread(target=self.start_callfunc).start()

        # 处理websocket消息
        for message in websocket:
            self.websocket_io.add_input(message)

    def start_callfunc(self):
        sys.stdin = self.websocket_io
        sys.stdout = self.websocket_io
        sys.stderr = self.websocket_io

        logger.remove()
        logger_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> <red>|</red> " \
                        "<cyan>{level: <8}</cyan> <red>|</red> " \
                        "<magenta>{name}</magenta><red>:</red><magenta>{function}</magenta><red>:</red><magenta>{line}</magenta> <red>-</red> " \
                        "<cyan>{message}</cyan>"

        logger.add(sys.stdout, colorize=True, format=logger_format)

        logger.info('调用函数开始运行 | The callfunc is starting. ')

        self.callfunc()
        print('调用函数已经运行完毕 | The callfunc has finished. ')
        input('请手动结束程序 | Please end the program manually. ')
        self.end = True

    def start_server(self):
        self.server = serve(self.websocket_callback, "localhost", 8765)
        self.server.serve_forever()

    def start(self):
        threading.Thread(target=self.start_server).start()
        print('WebTerminal等待连接 | WebTerminal is waiting for connection. ')
