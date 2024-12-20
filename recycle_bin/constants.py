from os import environ

RUNNING_ON_ANDROID = "ANDROID_APP_PATH" in environ

FONT_SIZE_TITLE = 32 if RUNNING_ON_ANDROID else 60
FONT_SIZE_SUBTITLE = 16 if RUNNING_ON_ANDROID else 32
FONT_SIZE_TEXT = 8 if RUNNING_ON_ANDROID else 16