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

def _timeformat(t, fmt="struct"):
    """
    provide alternative time type formatting:
    * default: struct time
    * s : seconds since Epoch
    * iso : iso string
    """
    if "struct" == fmt:
        return time.gmtime(t)
    elif "s" == fmt:
        return  t
    elif "iso" == fmt:
        return datetime.fromtimestamp(t).isoformat('-')
    else:
        raise AttributeError

def ctime(path, fmt="struct"):
    """
    get the (unix) change time of a file/dir
    """
    return _timeformat(os.path.getctime(path), fmt)

def mtime(path, fmt="struct"):
    """
    get the (unix) modification time of a file/dir
    """
    return _timeformat(os.path.getmtime(path), fmt)
