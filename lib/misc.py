"""
various help tools for the IPOL demo environment
"""
# pylint: disable-msg=C0103


#
# TINY STUFF
#

prod = lambda l : reduce(lambda a, b : a * b, l, 1)

#
# INDEX DICTIONARY
#

import os.path
import ConfigParser
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

def get_check_key(func):
    """
    decorator to read the key,
    save it as a class attribute,
    and check the key validity
    """
    def checked_func(self, *args, **kwargs):
        """
        original function with a preliminary key check
        """
        if kwargs.has_key('key'):
            self.key = kwargs.pop('key', '')
        self.check_key()
        return func(self, *args, **kwargs)
    return checked_func

#
# CHERRYPY REDIRECTION
#

import cherrypy
def http_redirect_303(url):
    """
    HTTP "303 See Other" redirection
    """
    # TODO drop 303 code, rename this function
#    cherrypy.response.status = "303 See Other"
#    cherrypy.response.headers['Location'] = "%s" % url
    cherrypy.response.headers['Refresh'] = "0; %s" % url

#
# BASE_APP REUSE
#

def app_expose(function):
    """
    shortcut to expose app actions from the base class
    """
    function.im_func.exposed = True
