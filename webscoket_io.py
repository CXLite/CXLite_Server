# custom_io.py
import sys

DEBUG = False

class WebScoketIO:
    def __init__(self, websocket):
        self.websocket = websocket
        self.input_buffer = []

    def init_websocket(self, websocket):
        self.websocket = websocket
        for message in websocket:
            self.add_input(message)

    def write(self, message):
        # self.output_buffer.append(message)
        self.websocket.send(message.replace('\n', '\r\n'))
        # 使用标准输出打印调试信息
        if DEBUG:
            sys.__stdout__.write(f'[CustomIO] {message}\n')

    def read(self):
        if DEBUG:
            sys.__stdout__.write('[CustomIO] Waiting for input...\n')

        while not self.input_buffer:
            pass
        return self.input_buffer.pop(0)

    def readline(self):
        if DEBUG:
            sys.__stdout__.write('[CustomIO] Waiting for input...\n')
        message = ""
        while True:
            m = self.read()
            # print(f'[CustomIO] Received: "{ord(m)}“')
            if ord(m[-1]) == 13:
                break
            elif ord(m[-1]) == 127:  # 检测到退格键
                if message:
                    message = message[:-1]
            else:
                message += m

        return message + '\n'

    def flush(self):
        if DEBUG:
            sys.__stdout__.write('[CustomIO] Flushing...\n')
        pass

    def add_input(self, message):
        if DEBUG:
            sys.__stdout__.write(f'[CustomIO] Adding input: {message}\n')
        self.input_buffer.append(message)
