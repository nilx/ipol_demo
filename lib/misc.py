"""
various help tools for the IPOL demo environment
"""
# pylint: disable=C0103


import os.path
import time
from datetime import datetime

#
# TINY STUFF
#

prod = lambda l : reduce(lambda a, b : a * b, l, 1)

#
# ACTION DECORATOR TO HANDLE DEMO KEY
#

def init_app(func):
    """
    decorator to reinitialize the app with the current request key
    """
    def init_func(self, *args, **kwargs):
        """
        original function with a preliminary key check
        """
        key = kwargs.pop('key', None)
        self.init_key(key)
        self.init_cfg()
        return func(self, *args, **kwargs)
    return init_func

#
# BASE_APP REUSE
#

def app_expose(function):
    """
    shortcut to expose app actions from the base class
    """
    function.im_func.exposed = True

#
# TIME
#

def _timeformat(t, format="struct"):
    """
    provide alternative time type pormatting:
    * default: struct time
    * s : seconds since Epoch
    * iso : iso string
    """
    if "struct" == format:
        return time.gmtime(t)
    elif "s" == format:
        return  t
    elif "iso" == format:
        return datetime.fromtimestamp(t).isoformat('-')
    else:
        raise AttributeError

def ctime(path, format="struct"):
    """
    get the (unix) change time of a file/dir
    """
    return _timeformat(os.path.getctime(path), format)

def mtime(path, format="struct"):
    """
    get the (unix) modification time of a file/dir
    """
    return _timeformat(os.path.getmtime(path), format)
