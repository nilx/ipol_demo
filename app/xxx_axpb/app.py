"""
demo example for the X->aX+b transform
"""
# pylint: disable=C0103

from lib import base_app
from lib import build
from lib import http
from lib.misc import get_check_key, app_expose
from lib.misc import index_dict, ctime

import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil

class app(base_app):
    """ template demo app """
    
    title = "f(x)=ax+b"
    input_nb = 1 # number of input images
    input_max_pixels = 500000 # max size (in pixels) of an input image
    input_max_weight = 1 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = True       # switch to False for deployment

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() is generic
        app_expose(base_app.index)
        app_expose(base_app.input_select)
        app_expose(base_app.input_upload)
        # params() is modified from the template
        app_expose(base_app.params)
        # run() and result() must be defined here

    def build(self):
        """
        program build/update
        """
        # store common file path in variables
        tgz_file = os.path.join(self.dl_dir, "axpb.tar.gz")
        prog_file = os.path.join(self.bin_dir, "axpb")
        log_file = os.path.join(self.base_dir, "build.log")
        # get the latest source archive
        build.download("https://edit.ipol.im/meta/dev/axpb.tar.gz", tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -C %s axpb"
                      % os.path.join(self.src_dir, "axpb")
                      + " CC='ccache cc' -j4", stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(os.path.join(self.src_dir, "axpb", "axpb"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    # run() is defined here,
    # because the parameters validation depends on the algorithm
    @cherrypy.expose
    @get_check_key
    def run(self, a="1.", b="0"):
        """
        params handling and run redirection
        """
        # save and validate the parameters
        try:
            params_file = index_dict(self.key_dir)
            params_file['params'] = {'a' : float(a),
                                     'b' : float(b)}
            params_file.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        http.refresh(self.url('result?key=%s' % self.key))
        urld = {'input' : [self.url('tmp', 'input_0.png')]}
        return self.tmpl_out("run.html", urld=urld)

    # run_algo() is defined here,
    # because it is the actual algorithm execution, hence specific
    # run_algo() is called from result(),
    # with the parameters validated in run()
    def run_algo(self, a, b):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        p = self.run_proc(['axpb', str(a), 'input_0.png', str(b), 
                           'output.png'])
        self.wait_proc(p)
        return

    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # read the parameters
        params_file = index_dict(self.key_dir)
        a = float(params_file['params']['a'])
        b = float(params_file['params']['b'])
        # run the algorithm
        try:
            self.run_algo(a, b)
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')
        self.log("input processed")
        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png')],
                'output' : [self.url('tmp', 'output.png')]}
        return self.tmpl_out("result.html", urld=urld)
