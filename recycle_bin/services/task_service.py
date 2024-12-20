import logging
import time
import traceback
from json import JSONDecodeError

from api import logger
from api.base import Account, Chaoxing
from api.cookies import use_account
from osc_module import OSCModule

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

osc_module = OSCModule(own_port=5005, peer_port=5006)


@osc_module.method("get_state")
def get_state_handler(unused_addr, *args):
    print(f"Received get_state request with args: {args}")
    return "success"


task = None
clazzid = None
courseid = None
cpi = None
chaoxing = None

point_list = None  #当前章节列表
point_index = -1  #当前章节下标

job_list = []  #当前任务点列表
job_index = -1  #当前任务点下标
job_info = None  #当前任务点信息

media_info = None  #媒体信息
media_context = None  #当前播放的上下文


def clear_task():
    # 清空当前任务信息
    global task, clazzid, courseid, cpi, chaoxing
    task = None
    clazzid = None
    courseid = None
    cpi = None
    chaoxing = None


def clear_point():
    # 清空当前的章节信息
    global point_list, point_index
    point_list = None
    point_index = -1


def clear_job():
    # 从队列中删除当前完成的任务
    global job_list, job_index, job_info
    job_list = []
    job_index = -1
    job_info = None


def clear_media():
    # 清空当前的媒体信息
    global media_info, media_context
    media_info = None
    media_context = None


def do_task():
    global chaoxing, cpi, courseid, clazzid, task
    global point_list, point_index
    global job_list, job_index, job_info

    global media_info, media_context

    if media_info:
        # 有视频正在播放
        course = {
            "clazzid": clazzid,
            "courseid": courseid,
            "cpi": cpi
        }

        job = job_list[job_index]

        media_context = chaoxing.study_video_sync(course, job, job_info, media_info, media_context)
        if media_context['_isFinished']:
            # 当前视频播放完成
            clear_media()

        if media_context['_isFinished']:
            # 当前视频播放出错，跳过
            clear_media()

        return

    if job_list:
        # 当前有章节的任务点在队列中
        # 视频任务

        # 判断任务点编号是否越界
        if job_index >= len(job_list):
            # 所有任务点已经完成
            clear_job()
            return

        job = job_list[job_index]

        if job["type"] == "video":
            # logger.trace(f"识别到视频任务, 任务章节: {course['title']} 任务ID: {job['jobid']}")
            # 超星的接口没有返回当前任务是否为Audio音频任务
            isAudio = False
            try:
                media_info = chaoxing.get_media_info(job)
            except JSONDecodeError as e:
                logger.warning("当前任务非视频任务，正在尝试音频任务解码")
                isAudio = True

            if isAudio:
                try:
                    media_info = chaoxing.get_media_info(job)
                except JSONDecodeError as e:
                    # logger.warning(f"出现异常任务 -> 任务章节: {course['title']} 任务ID: {job['jobid']}, 已跳过")
                    # Todo 播放媒体异常处理
                    pass
        # 文档任务
        elif job["type"] == "document":
            # logger.trace(f"识别到文档任务, 任务章节: {course['title']} 任务ID: {job['jobid']}")
            course = {
                "clazzid": clazzid,
                "courseid": courseid,
                "cpi": cpi
            }
            chaoxing.study_document(course, job)
        # 测验任务
        elif job["type"] == "workid":
            # logger.trace(f"识别到章节检测任务, 任务章节: {course['title']}")
            course = {
                "clazzid": clazzid,
                "courseid": courseid,
                "cpi": cpi
            }
            chaoxing.study_work(course, job, job_info)
        # 阅读任务
        elif job["type"] == "read":
            # logger.trace(f"识别到阅读任务, 任务章节: {course['title']}")
            course = {
                "clazzid": clazzid,
                "courseid": courseid,
                "cpi": cpi
            }
            chaoxing.strdy_read(course, job, job_info)

        job_index += 1

        return

    if point_list:
        # 当前已经读取过了章节列表，但是还没有任务点数据，进入章节，获取任务点
        # 获取当前章节的所有任务点

        # 判断章节编号是否越界
        if point_index >= len(point_list["points"]):
            # 所有章节已经完成
            clear_point()
            # 通知当前任务已经完成
            osc_module.call_method("task_done", task)
            clear_task()

        point = point_list["points"][point_index]
        jobs, job_info = chaoxing.get_job_list(clazzid, courseid, cpi, point["id"])

        # Todo 未开放章节处理
        # 发现未开放章节，尝试回滚上一个任务重新完成一次
        # if job_info.get('notOpen', False):
        #     point_index -= 1  # 默认第一个任务总是开放的
        #     # 针对题库启用情况
        #     # if not tiku or tiku.DISABLE or not tiku.SUBMIT:
        #     #     # 未启用题库或未开启题库提交，章节检测未完成会导致无法开始下一章，直接退出
        #     #     logger.error(
        #     #         f"章节未开启，可能由于上一章节的章节检测未完成，请手动完成并提交再重试，或者开启题库并启用提交")
        #     #     break
        #     RB.add_times(point["id"])
        #     continue

        # 可能存在章节无任何内容的情况
        if not jobs:
            # 清空当前任务点
            clear_job()

        job_index += 1  # 开始进入任务点(-1到0)

        # 章节编号加一，记录当前章节已获取过
        point_index += 1

        return

    # 还没有进入过章节，第一次获取章节列表
    point_list = chaoxing.get_course_point(courseid, clazzid, cpi)
    point_index += 1


# 保持服务进程运行
try:
    while True:
        time.sleep(2)
        if task:
            do_task()
        else:
            task = osc_module.call_method("get_tasks")[0]
            clazzid = task['clazzid']
            courseid = task['courseid']
            cpi = task['cpi']
            account_history = use_account()
            account = Account(account_history['username'], account_history['password'])
            chaoxing = Chaoxing(account)
except KeyboardInterrupt:
    osc_module.close()
