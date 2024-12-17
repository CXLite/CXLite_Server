import threading
import time
from pythonosc import dispatcher, osc_server, udp_client
import logging


class OSCModule:
    def __init__(self, own_port, peer_port):
        self.own_port = own_port
        self.peer_port = peer_port
        self.dispatcher = dispatcher.Dispatcher()
        self.client = udp_client.SimpleUDPClient("127.0.0.1", peer_port)
        self.server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", own_port), self.dispatcher)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()
        self.responses = {}
        self.lock = threading.Lock()
        self.dispatcher_lock = threading.Lock()

    def register_method(self, method_name, handler):
        def wrapper(unused_addr, *args):
            logging.debug(f"Handling {method_name} with args: {args}")
            response = handler(unused_addr, *args)
            response_key = f"/{method_name}_response"
            logging.debug(f"Sending response to {response_key}: {response}")
            self.client.send_message(response_key, response)

        with self.dispatcher_lock:
            self.dispatcher.map(f"/{method_name}", wrapper)

    def method(self, method_name):
        def decorator(func):
            self.register_method(method_name, func)
            return func

        return decorator

    def call_method(self, method_name, *args, timeout=5):
        response_event = threading.Event()
        response_key = f"/{method_name}_response"

        def response_handler(unused_addr, *response_args):
            logging.debug(f"Received response for {method_name}: {response_args}")
            with self.lock:
                self.responses[response_key] = response_args
            response_event.set()

        with self.dispatcher_lock:
            self.dispatcher.map(response_key, response_handler)
        logging.debug(f"Calling {method_name} with args: {args}")
        self.client.send_message(f"/{method_name}", args)

        if response_event.wait(timeout):
            with self.lock:
                response = self.responses.pop(response_key, None)
            return response
        else:
            logging.debug(f"Timeout waiting for response to {method_name}")
            return None

    def close(self):
        self.server.shutdown()
        self.server_thread.join()
