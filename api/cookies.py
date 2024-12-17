# -*- coding: utf-8 -*-
import json
import os.path
import pickle
from api.config import GlobalConst as gc


def save_cookies(_session):
    with open(gc.COOKIES_PATH, 'wb') as f:
        print(_session.cookies)
        pickle.dump(_session.cookies, f)


def use_cookies():
    if os.path.exists(gc.COOKIES_PATH):
        with open(gc.COOKIES_PATH, 'rb') as f:
            _cookies = pickle.load(f)
        return _cookies


def save_account(username, password):
    with open(gc.ACCOUNT_PATH, 'w+', encoding='utf-8') as f:
        data = {
            'username': username,
            'password': password
        }
        f.write(json.dumps(data))


def use_account():
    if os.path.exists(gc.ACCOUNT_PATH):
        with open(gc.ACCOUNT_PATH, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
        return data
