import threading
import time

from web_terminal import WebTerminal

from main_callfunc import callfunc

# def callfunc():
#     print('This is a test.')
#     input_message = input("Please input something:")
#     print(f'Input was: {input_message}')


web_terminal = WebTerminal(callfunc)
web_terminal.start()


