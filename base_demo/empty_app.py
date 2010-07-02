"""
Empty ipol demo web app
"""

import hashlib
from datetime import datetime
from random import random
import os.path

import cherrypy

class empty_app(object):
    """
    This app only contains configuration and tools, no actions.
    """

    def __init__(self, base_dir):
        """
        app setup
        """
        # the demo ID is the folder name
        self.base_dir = os.path.abspath(base_dir)
        self.id = os.path.basename(base_dir)
        self.key = None

    #
    # FILE PATH MODEL 
    #

    def path(self, folder, fname=''):
        """
        path scheme:
        * tmp   -> ./data/tmp/<key>/<file_name>
        * input -> ./data/input/<file_name>
        """
        if folder == 'tmp':
            # TODO : check key != None
            path = os.path.join(self.base_dir, 'data', 'tmp', self.key, fname)
        elif folder == 'input':
            path = os.path.join(self.base_dir, 'data', 'input', fname)
        return os.path.abspath(path)

    #
    # URL MODEL 
    #

    def _url_link(self, link):
        """
        url scheme for links
        """
        if link == 'demo':
            return cherrypy.url(path="/pub/demo/%s/" % self.id,
                                script_name='')
        elif link == 'algo':
            return cherrypy.url(path="/pub/algo/%s/" % self.id,
                                script_name='')
        elif link == 'archive':
            return cherrypy.url(path="/pub/archive/%s/" % self.id,
                                script_name='')
        elif link == 'forum':
            return cherrypy.url(path="/pub/forum/%s/" % self.id,
                                script_name='')

    def _url_file(self, folder, fname=None):
        """
        url scheme for files:
        * tmp   -> ./tmp/<key>/<file_name>
        * input -> ./input/<file_name>
        """
        if fname == None:
            fname = ''
        if folder == 'tmp':
            return cherrypy.url(path="tmp/%s/" % self.key + fname)
        elif folder == 'input':
            return cherrypy.url(path='input/' + fname)

    def _url_action(self, action, params=None):
        """
        url scheme for actions
        """
        query_string = ''
        if params:
            query_string = '&'.join(["%s=%s" % (key, value)
                                     for (key, value) in params.items()])
        return cherrypy.url(path="%s" % action, qs=query_string)

    def url(self, arg1, arg2=None):
        """
        url scheme wrapper
        """
        # TODO: include a configurable url base
        #       taken from the config file 
        if arg1 in ['demo', 'algo', 'archive', 'forum']:
            return self._url_link(link=arg1)
        elif arg1 in ['tmp', 'input']:
            return self._url_file(folder=arg1, fname=arg2)
        else:
            return self._url_action(action=arg1, params=arg2)

    #
    # KEY MANAGEMENT
    #

    def new_key(self):
        """
        create a key and its storage folder
        """
        keygen = hashlib.md5()
        seeds = [cherrypy.request.remote.ip,
                 # use port to improve discrimination
                 # for proxied or NAT clients 
                 cherrypy.request.remote.port, 
                 datetime.now(),
                 random()]
        for seed in seeds:
            keygen.update(str(seed))
        self.key = keygen.hexdigest()
        os.mkdir(self.path('tmp'))
        return

    def check_key(self):
        """
        verify a key exists, and raise an error if it doesn't
        """
        if not os.path.isdir(self.path('tmp')):
            raise cherrypy.HTTPError(400, # Bad Request
                                     "The key is invalid")

    #
    # LOGS
    #

    def log(self, msg):
        """
        simplified log handler
        """
        cherrypy.log(msg, context="DEMO/%s/%s" % (self.id, self.key),
                     traceback=False)
        return

