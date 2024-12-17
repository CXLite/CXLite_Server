import base64
import json, os
import time
from http.server import SimpleHTTPRequestHandler
import socketserver
from urllib.parse import urlparse, parse_qs

import debug
from services import OSCModule
from tools import get_android_python_activity, get_task_service
import requests, pyaes, loguru
from bs4 import BeautifulSoup
from jnius import autoclass

from constants import RUNNING_ON_ANDROID
from api.base import Chaoxing, Account
from api.config import GlobalConst as gc
from api.cookies import save_account, use_account

PORT = 8080
DIRECTORY = "./static"

service_running = False  # 课程任务服务是否正在运行标识

DEBUG = debug.DEBUG  # 是否开启调试模式

taksList = []  # 课程任务列表


def start_service():
    global service_running

    if service_running:
        return

    if RUNNING_ON_ANDROID:
        activity = get_android_python_activity()
        task_service = get_task_service()
        task_service.start(activity, 'Some argument')
        service_running = True
    else:
        # 本地测试时，启动一个子进程运行对应的 Python 文件
        import subprocess

        # 设置工作目录为项目根目录
        project_root = os.path.dirname(os.path.abspath(__file__))

        subprocess.Popen(['python3', 'services/task_service.py'], cwd=project_root)
        print("Local service started")


def stop_service():
    global service_running

    if not service_running:
        return

    if RUNNING_ON_ANDROID:
        activity = get_android_python_activity()
        task_service = get_task_service()
        task_service.stop(activity)
        service_running = False
    else:
        # 本地测试时，先不管
        pass
        print("Local service stopped")


start_service()

osc_module = OSCModule(own_port=5006, peer_port=5005)


@osc_module.method("get_tasks")
def get_tasks_handler(unused_addr, *args):
    print(f"Received get_tasks request with args: {args}")
    if not taksList:
        return None
    return taksList[0]


@osc_module.method("task_done")
def task_done_handler(unused_addr, *args):
    print(f"Received task_done request with args: {args}")
    task = args[0]  # 提取出已经完成的任务
    if task in taksList:
        taksList.remove(task)


@osc_module.method("update_pogress")
def update_pogress_handler(unused_addr, *args):
    task = args[0]  # 当前进行的课程任务
    type = args[1]  # 当前正在完成的任务点类型
    name = args[2]  # 当前任务的名称
    pogress = args[2]  # 当前任务点的进度（仅在 video 下有效）
    job_progess = args[3]  # 完了任务点的个数


#
# time.sleep(2)
#
# response = osc_module.call_method("get_state", "param1", "param2")
# print(f"Service Response: {response}")

class MyHttpRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # 解析 URL 并获取查询参数
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        self.path = path

        if self.path == '/':
            self.path = './index.html'
            return super().do_GET()
        elif self.path == '/service':
            start_service()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Task service started')
        elif self.path == '/login':
            username = query_params.get('username', [''])[0]
            password = query_params.get('password', [''])[0]
            if not username or not password:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Username and password are required')
                return

            # 登录超星学习通
            account = Account(username, password)
            chaoxing = Chaoxing(account)
            result = chaoxing.login()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        elif self.path == '/login_state':
            if os.path.exists(gc.COOKIES_PATH):
                response = {
                    'state': True,
                }
            else:
                response = {
                    'state': False,
                }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        elif self.path == '/account_history':
            if os.path.exists(gc.ACCOUNT_PATH):
                with open(gc.ACCOUNT_PATH, 'r', encoding='utf-8') as f:
                    data = json.loads(f.read())
                response = {
                    'username': data['username'],
                    'password': data['password']
                }
            else:
                response = {
                    'username': '',
                    'password': ''
                }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        elif self.path == '/get_course_list':
            account_history = use_account()
            account = Account(account_history['username'], account_history['password'])
            chaoxing = Chaoxing(account)
            course_list = chaoxing.get_course_list()

            # 获取cover并转换为base64
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                "Accept-Encoding": "gzip, deflate",
                "Upgrade-Insecure-Requests": "1"
            }
            for course in course_list:
                response = requests.get(course['cover'], headers=headers)
                if response.status_code == 200:
                    file_extension = os.path.splitext(course['cover'])[1].lower()
                    if file_extension == '.jpg' or file_extension == '.jpeg':
                        mime_type = 'image/jpeg'
                    elif file_extension == '.png':
                        mime_type = 'image/png'
                    else:
                        mime_type = ''
                    base64_image = base64.b64encode(response.content).decode('utf-8')
                    course['cover'] = f"data:{mime_type};base64,{base64_image}"
                else:
                    print(f"Failed to get cover for course {course['cover']}, {response}")
                    course['cover'] = ''  # 或者设置为默认图片的 Base64 编码

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(course_list).encode('utf-8'))
        elif self.path == '/get_course_point':
            courseId = query_params.get('courseId', [''])[0]
            clazzId = query_params.get('clazzId', [''])[0]
            cpi = query_params.get('cpi', [''])[0]

            if not courseId or not clazzId or not cpi:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'courseId, clazzId and cpi are required')
                return

            account_history = use_account()
            account = Account(account_history['username'], account_history['password'])
            chaoxing = Chaoxing(account)
            course_point = chaoxing.get_course_point(courseId, clazzId, cpi)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(course_point).encode('utf-8'))
        elif self.path == '/get_job_list':
            clazzid = query_params.get('clazzid', [''])[0]
            courseid = query_params.get('courseid', [''])[0]
            cpi = query_params.get('cpi', [''])[0]
            knowledgeid = query_params.get('knowledgeid', [''])[0]
            if not clazzid or not courseid or not cpi or not knowledgeid:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'clazzid, courseid, cpi and knowledgeid are required')
                return

            account_history = use_account()
            account = Account(account_history['username'], account_history['password'])
            chaoxing = Chaoxing(account)
            job_list, job_info = chaoxing.get_job_list(clazzid, courseid, cpi, knowledgeid)
            data = {
                'job_list': job_list,
                'job_info': job_info
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        elif self.path == '/add_task':
            global taksList

            clazzid = query_params.get('clazzid', [''])[0]
            courseid = query_params.get('courseid', [''])[0]
            cpi = query_params.get('cpi', [''])[0]

            if not clazzid or not courseid or not cpi:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'clazzid, courseid and cpi are required')
                return

            taksList.append({'clazzid': clazzid, 'courseid': courseid, 'cpi': cpi})
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(taksList).encode('utf-8'))

        else:
            return super().do_GET()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')  # 添加CORS头
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()


handler = MyHttpRequestHandler

with socketserver.TCPServer(("", PORT), handler) as httpd:
    print(f"Serving HTTP on port {PORT}")
    httpd.serve_forever()
