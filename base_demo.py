"""
generic ipol demo web app
"""
# TODO : add steps (cf amazon cart)

#
# EMPTY APP
#

import hashlib
from datetime import datetime
from random import random

import os
import time
from subprocess import PIPE, Popen

from lib import TimeoutError, RuntimeError

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
        self.run_environ = {}

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
            path = os.path.join(self.base_dir, 'tmp', self.key, fname)
        elif folder == 'bin':
            path = os.path.join(self.base_dir, 'bin', fname)
        elif folder == 'input':
            path = os.path.join(self.base_dir, 'input', fname)
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

    #
    # SUBPROCESS
    #

    def run_proc(self, args, stdin=None, stdout=None, stderr=None):
        """
        execute a sub-process from the 'tmp' folder
        """
        # update the environment
        newenv = os.environ.copy()
        newenv.update(self.run_environ)
        # TODO : clear the PATH, hard-rewrite the exec arg0
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
            timeout = False;
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

#
# BASE APP
#

import os, shutil
from lib import index_dict, tn_image, image, prod, \
    get_check_key, http_redirect_303

import cherrypy
from mako.lookup import TemplateLookup

class app(empty_app):
    """ base demo app class with a typical flow """

    # default class attributes
    # to be modified in subclasses
    title = "base demo"
    description = "This demo contains all the generic actions," \
        + "none of which should be exposed."

    input_nb = 1 # number of input files
    input_max_pixels = 1024 * 1024 # max size of an input image
    input_max_weight = 5 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '1x8i' # input image expected data type
    input_ext = '.tiff' # input image expected extention (ie. file format)
    display_ext = '.jpeg' # html embedded displayed image extention
    timeout = 60 # subprocess execution timeout
    is_test = False;

    def __init__(self, base_dir):
        """
        app setup
        base_dir is supposed to be received from a subclass
        """
        # setup the parent class
        empty_app.__init__(self, base_dir)
        cherrypy.log("demo base_dir: %s" % self.base_dir,
                     context='SETUP', traceback=False)
        # local base_app templates folder
        tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'base_template')
        # first search in the subclass template dir
        self.tmpl_lookup = TemplateLookup( \
            directories=[os.path.join(self.base_dir,'template'), tmpl_dir],
            input_encoding='utf-8',
            output_encoding='utf-8', encoding_errors='replace')
        # [TEST] flag
        if self.is_test:
            self.title = '[TEST] ' + self.title

        # TODO : early attributes validation

    #
    # TEMPLATES HANDLER
    #

    def tmpl_out(self, tmpl_fname, **kwargs):
        """
        templating shortcut, populated with the default app attributes
        """
        # app attributes dict
        attrd = dict([(attr, getattr(self, attr, ''))
                      for attr in ['id',
                                   'key',
                                   'input_nb',
                                   'title',
                                   'description']])
        kwargs.update(attrd)

        # create urld if it doesn't exist
        kwargs.setdefault('urld', {})
        # add urld items
        kwargs['urld'].update({'start' : self.url('index'),
                               'xlink_algo' : self.url('algo'),
                               'xlink_demo' : self.url('demo'),
                               'xlink_archive' : self.url('archive'),
                               'xlink_forum' : self.url('forum')})
        # production flag
        kwargs['prod'] = (cherrypy.config['server.environment']
                          == 'production')

        tmpl = self.tmpl_lookup.get_template(tmpl_fname)
        return tmpl.render(**kwargs)

    #
    # INDEX
    #

    def index(self):
        """
        demo presentation and input menu
        """
        # read the input index as a dict
        inputd = index_dict(self.path('input'))
        for key in inputd.keys():
            # convert the files to a list of file names
            # by splitting at blank characters
            inputd[key]['files'] = inputd[key]['files'].split()
            # generate thumbnails and thumbnail urls
            tn_fname = [tn_image(self.path('input', fname))
                        for fname in inputd[key]['files']]
            inputd[key]['tn_url'] = [self.url('input',
                                              os.path.basename(fname))
                                     for fname in tn_fname]

        # urls dict
        urld = {'select_form' : self.url('input_select'),
                'upload_form' : self.url('input_upload')}
        return self.tmpl_out("input.html", urld=urld,
                              inputd=inputd)

    #
    # INPUT HANDLING TOOLS
    #

    def process_input(self):
        """
        pre-process the input data
        """
        msg = None;
        for i in range(self.input_nb):
            # open the file as an image
            try:
                im = image(self.path('tmp', 'input_%i' % i))
            except IOError:
                raise cherrypy.HTTPError(400, # Bad Request
                                         "Bad input file")
            # convert to the expected input format
            im.convert(self.input_dtype)
            # check max size
            if self.input_max_pixels \
                    and prod(im.size) > (self.input_max_pixels):
                im.resize(self.input_max_pixels)
                self.log("input resized")
                msg = """The image has been resized
                      for a reduced computation time."""
            # save a working copy
            im.save(self.path('tmp', 'input_%i' % i + self.input_ext))
            # save a web viewable copy
            if (self.display_ext != self.input_ext):
                im.save(self.path('tmp', 'input_%i' % i + self.display_ext))
        return msg

    def clone_input(self):
        """
        clone the input for a re-run of the algo
        """
        # get a new key
        oldkey = self.key
        oldpath = self.path('tmp')
        self.new_key()
        # copy the input files
        fnames = ['input_%i' % i + self.input_ext
                  for i in range(self.input_nb)]
        fnames += ['input_%i' % i + self.display_ext
                   for i in range(self.input_nb)]
        for fname in fnames:
            shutil.copy(os.path.join(oldpath, fname),
                        os.path.join(self.path('tmp'), fname))
        self.log("input cloned from %s" % oldkey)
        return

    #
    # INPUT STEP
    #

    def input_select(self, input_id, **kwargs):
        """
        use the selected available input images
        """
        # kwargs is for input_id.x and input_id.y, unused
#        del kwargs
        self.new_key()
        input_dict = index_dict(self.path('input'))
        fnames = input_dict[input_id]['files'].split()
        for i in range(len(fnames)):
            shutil.copy(self.path('input', fnames[i]),
                        self.path('tmp', 'input_%i' % i))
        msg = self.process_input()
        self.log("input selected : %s" % input_id)
        # jump to the params page
        return self.params(key=self.key, msg=msg)

    def input_upload(self, **kwargs):
        """
        use the uploaded input images
        """
        self.new_key()
        for i in range(self.input_nb):
            file_up = kwargs['file_%i' % i]
            file_save = file(self.path('tmp', 'input_%i' % i), 'wb')
            if '' == file_up.filename:
                # missing file
                raise cherrypy.HTTPError(400, # Bad Request
                                         "Missing input file")
            size = 0
            while True:
                # TODO : larger data size
                data = file_up.file.read(128)
                if not data:
                    break
                size += len(data)
                if size > self.input_max_weight:
                    # file too heavy
                    raise cherrypy.HTTPError(400, # Bad Request
                                             "File too large, " +
                                             "resize or use better compression")
                file_save.write(data)
            file_save.close()
        msg = self.process_input()
        self.log("input uploaded")
        # jump to the params page
        return self.params(key=self.key, msg=msg)

    #
    # ERROR HANDLING
    #

    def error(self, errcode=None, errmsg=''):
        """
        signal an error
        """
        return self.tmpl_out("error.html", errcode=errcode, errmsg=errmsg)

    #
    # PARAMETER HANDLING
    #

    @get_check_key
    def params(self, newrun=False, msg=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        urld = {'next_step' : self.url('run'),
                'input' : [self.url('tmp', 'input_%i' % i + self.display_ext)
                           for i in range(self.input_nb)]}
        return self.tmpl_out("params.html", urld=urld, msg=msg)

    #
    # EXECUTION AND RESULTS
    #

    @get_check_key
    def run(self, **kwargs):
        """
        params handling and run redirection
        SHOULD be defined in the derived classes, to check the parameters
        """
        # redirect to the result page
        # TODO: check_params as another function
        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'input' : [self.url('tmp', 'input_%i' % i + self.display_ext)
                           for i in range(self.input_nb)]}
        return self.tmpl_out("run.html", urld=urld)

    def run_algo(self, params):
        """
        the core algo runner
        * could also be called by a batch processor
        * MUST be defined by the derived classes
        """
        pass

    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # TODO : ensure only running once
        # TODO : save each result in a new archive
        # TODO : give the archive link
        # TODO : give the option to not be public
        #        (and remember it from a cookie)
        # TODO : read the kwargs from a file, and pass to run_algo
        # TODO : pass these parameters to the template
        self.run_algo({})
        self.log("input processed")
        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_%i' % i + self.display_ext)
                           for i in range(self.input_nb)],
                'output' : [self.url('tmp', 'output' + self.display_ext)]}
        return self.tmpl_out("result.html", urld=urld)
