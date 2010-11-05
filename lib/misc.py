"""
various help tools for the IPOL demo environment
"""
# pylint: disable=C0103


import os.path
import time

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

def ctime(fname):
    """
    get the (unix) change time of a file
    """
    return time.gmtime(os.path.getmtime(fname))
