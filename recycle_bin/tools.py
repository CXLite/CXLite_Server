import atexit
import os
import signal
import sys

from jnius import autoclass

from constants import RUNNING_ON_ANDROID
from debug import DEBUG

DEBUG = DEBUG  # 是否开启调试模式


def get_android_python_activity():
    """
    Return the `PythonActivity.mActivity` using `pyjnius`.

    .. warning:: This function will only be ran if executed from android"""

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    return PythonActivity.mActivity


def get_task_service():
    return autoclass('io.github.user2061360308.cxlite.ServiceTask_service')


def raise_error(error):
    """
    A function to notify an error without raising an exception.

    .. warning:: we will try to notify via an kivy's Popup, but if kivy is not
              installed, it will only print an error message.
    """
    print('raise_error:', error)


def skip_if_not_running_from_android_device(func):
    """
    Skip run of the function in case that we are running the app form android.

    .. note:: this is useful for some kind of tests that are supposed to be run
              from an android device and relies on `pyjnius`.
    """

    def wrapper(*arg, **kwarg):
        if RUNNING_ON_ANDROID:
            return func(*arg, **kwarg)
        raise_error(
            'Function `{func_name}` only available for android devices'.format(
                func_name=func.__name__,
            ),
        )
        return None

    return wrapper


def get_private_storage_path():
    """
    Return the path to the private storage of the app.

    In android, this is the private directory of the app, in other systems, it is the project directory.
    """
    if RUNNING_ON_ANDROID:
        return os.environ["ANDROID_PRIVATE"]
    else:
        return os.path.dirname(os.path.abspath(__file__))


def gender_safe_path(path):
    """
    Return the path to the private storage of the app.
    """
    return os.path.join(get_private_storage_path(), path)


def before_destroy():
    """
    A function to do some clean up before the app is destroyed.
    """

    def before_destroy_handler(sig='', frame=''):
        # 删除cookie文件
        if not DEBUG:
            os.remove(gc.COOKIES_PATH)

        sys.exit(0)

    if RUNNING_ON_ANDROID:
        from android.activity import register_activity_lifecycle_callbacks

        register_activity_lifecycle_callbacks(
            onActivityDestroyed=before_destroy_handler,
        )
    else:
        # 正常退出时的清理工作
        atexit.register(before_destroy_handler)

        # 捕获 SIGINT 和 SIGTERM 信号
        signal.signal(signal.SIGINT, before_destroy_handler)
        signal.signal(signal.SIGTERM, before_destroy_handler)

        print("Service not stopped")
