"""
empty IPOL demo web app
"""
# pylint: disable=C0103

#
# EMPTY APP
#

import hashlib
from datetime import datetime
from random import random

import os
import time
from subprocess import Popen

from cherrypy import TimeoutError
import cherrypy

class empty_app(object):
    """
    This app only contains configuration and tools, no actions.
    """
    # TODO : rewrite the path/url functions

    def __init__(self, base_dir):
        """
        app setup

        @param base_dir: the base directory for this demo, used to
        look for special subfolders (input, tmp, ...)
        """
        # the demo ID is the folder name
        self.base_dir = os.path.abspath(base_dir)
        self.id = os.path.basename(base_dir)
        self.key = None

        # data subfolders
        self.input_dir = os.path.join(self.base_dir, 'input')
        self.tmp_dir = os.path.join(self.base_dir, 'tmp')
        self.dl_dir = os.path.join(self.base_dir, 'dl')
        self.src_dir = os.path.join(self.base_dir, 'src')
        self.bin_dir = os.path.join(self.base_dir, 'bin')

        # create the missing subfolders
        for static_dir in [self.input_dir, self.tmp_dir]:
            if not os.path.isdir(static_dir):
                cherrypy.log("warning: missing static folder, "
                             "creating it : %s" % static_dir,
                             context='SETUP', traceback=False)
                os.mkdir(static_dir)
                
        # static folders
        # cherrypy.tools.staticdir is a decorator,
        # ie a function modifier
        self.input = cherrypy.tools.staticdir(dir=self.input_dir)\
            (lambda x : None)
        self.tmp = cherrypy.tools.staticdir(dir=self.tmp_dir)\
            (lambda x : None)

    #
    # FILE PATH MODEL 
    #

    def path(self, folder, fname=''):
        """
        file path scheme

        @param folder: the path folder category:
          - tmp : the unique temporary folder (using the key)
          - bin : the binary folder
          - input : the input folder
        @return: the local file path
        """
        # TODO use key instead of tmp
        if folder == 'tmp':
            # TODO check key != None
            path = os.path.join(self.tmp_dir, self.key, fname)
        elif folder == 'bin':
            path = os.path.join(self.bin_dir, fname)
        elif folder == 'input':
            path = os.path.join(self.input_dir, fname)
        return os.path.abspath(path)

    #
    # URL MODEL 
    #

    def _url_xlink(self, link):
        """
        link url scheme
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
        # TODO use key instead of tmp
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
        url scheme
        """
        # TODO include a configurable url base
        #       taken from the config file 
        if arg1 in ['demo', 'algo', 'archive', 'forum']:
            return self._url_xlink(link=arg1)
        elif arg1 in ['tmp', 'input']:
            return self._url_file(folder=arg1, fname=arg2)
        else:
            return self._url_action(action=arg1, params=arg2)

    #
    # UPDATE
    #

    def build(self):
        """
        virtual function, to be overriden by subclasses
        """
        cherrypy.log("warning: no build method",
                     context='SETUP/%s' % self.id, traceback=False)
        pass

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
        verify a key exists, is safe and valid,
        and raise an error if it doesn't
        """
        
        if not (self.key
                and self.key.isalnum()
                and os.path.isdir(self.path('tmp'))):
            raise cherrypy.HTTPError(400, # Bad Request
                                     "The key is invalid")

    #
    # LOGS
    #

    def log(self, msg):
        """
        simplified log handler

        @param msg: the log message string
        """
        cherrypy.log(msg, context="DEMO/%s/%s" % (self.id, self.key),
                     traceback=False)
        return

    #
    # SUBPROCESS
    #

    def run_proc(self, args, stdin=None, stdout=None, stderr=None):
        """
        execute a sub-process from the 'tmp' folder
        """
        # update the environment
        newenv = os.environ.copy()
        # TODO clear the PATH, hard-rewrite the exec arg0
        # TODO use shell-string execution
        newenv.update({'PATH' : self.path('bin')})
        # run
        return Popen(args, stdin=stdin, stdout=stdout, stderr=stderr,
                     env=newenv, cwd=self.path('tmp'))

    def wait_proc(self, process, timeout=False):
        """
        wait for the end of a process execution with an optional timeout
        timeout: False (no timeout) or a numeric value (seconds)
        process: a process or a process list, tuple, ...
        """

        if not (cherrypy.config['server.environment'] == 'production'):
            # no timeout if just testing
            timeout = False
        if isinstance(process, Popen):
            # require a list
            process_list = [process]
        else:
            # duck typing, suppose we have an iterable
            process_list = process
        if not timeout:
            # timeout is False, None or 0
            # wait until everything is finished
            for p in process_list:
                p.wait()
        else:
            # http://stackoverflow.com/questions/1191374/
            # wainting for better : http://bugs.python.org/issue5673
            start_time = time.time()
            run_time = 0
            while True:
                if all([p.poll() is not None for p in process_list]):
                    # all processes have terminated
                    break
                run_time = time.time() - start_time
                if run_time > timeout:
                    for p in process_list:
                        try:
                            p.terminate()
                        except OSError:
                            # could not stop the process
                            # probably self-terminated
                            pass
                    raise TimeoutError
                time.sleep(0.1)
        if any([0 != p.returncode for p in process_list]):
            raise RuntimeError
        return
