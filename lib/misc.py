"""
various help tools for the IPOL demo environment
"""
# pylint: disable=C0103


import os.path
import ConfigParser
import time

#
# TINY STUFF
#

prod = lambda l : reduce(lambda a, b : a * b, l, 1)

#
# INDEX DICTIONARY
#

class index_dict(dict):
    """
    handle a config file as a dictionary
    """
    # TODO rename to file_dict or config_dict
    fname = None

    def __init__(self, location, fname='index.cfg'):
        """
        initalize a dictionary from a config file

        @param location: folder containing this config file
        @param fname: name of the config file
        """
        # TODO drop fname parameter
        dict.__init__(self)
        self.fname = os.path.join(location, fname)

        index = ConfigParser.RawConfigParser()
        index.read(self.fname)
        for section in index.sections():
            self[section] = dict(index.items(section))

    def save(self):
        """
        save the (updated) dictionary to the config file
        """
        dict.__init__(self)
        
        index = ConfigParser.RawConfigParser()
        for section in self.keys():
            index.add_section(section)
            for option in self[section].keys():
                index.set(section, option,
                          self[section][option])
        index_file = open(self.fname, 'w')
        index.write(index_file)
        index_file.close()

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
