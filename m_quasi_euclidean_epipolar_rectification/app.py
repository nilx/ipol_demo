# -*- coding: utf-8 -*-
# pylint: disable-msg=C0103
"""
Quasi-Euclidean Epipolar Rectification
"""

from base_demo import app as base_app
from lib import get_check_key, http_redirect_303, app_expose, image
from lib import TimeoutError
import os.path
import time
import cherrypy
import shutil

#
# INTERACTION
#

class app(base_app):
    """ template demo app """
    
    title = "Quasi-Euclidean Epipolar Rectification"
    description = """V. Kolmogorov and R. Zabih's method tries to minimize an 
    energy defined on all possible configurations.<br />
    Please select or upload the image pair to rectify.
    """

    input_nb = 2 # number of input images
    input_max_pixels = 1024 * 1024 # max size (in pixels) of an input image
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'  # input image expected extension (ie file format)    
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
        #app_expose(base_app.input_select)
        #app_expose(base_app.input_upload)
        # params() is modified from the template
        #app_expose(base_app.params)
        # run() and result() must be defined here

    @cherrypy.expose
    @get_check_key
    def run(self, **kwargs):
        """
        params handling and run redirection
        """
        # no parameter
        # redirect to the result page
        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')]}
        return self.tmpl_out("run.html", urld=urld)

    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        # run Rectify.sh
        stdout = open(self.path('tmp', 'stdout.txt'), 'w')
        p = self.run_proc(['Rectify.sh',
                           self.path('tmp', 'input_0.png'),
                           self.path('tmp', 'input_1.png')],
                          stdout=stdout, stderr=stdout)
        self.wait_proc(p, timeout)
        stdout.close()

        return

    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # TODO check image size
        # no parameters
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout)
            run_time = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="""
The algorithm took more than %i seconds and had to be interrupted.
Try again with simpler images.""" % self.timeout)
        except RuntimeError:
            return self.error(errcode='retime',
                              errmsg="""
The program ended with a failure return code,
something must have gone wrong""")
        self.log("input processed")
        
        shutil.move(self.path('tmp', 'input_0.png_input_1.png_pairs_orsa.txt'),
                    self.path('tmp', 'orsa.txt'))
        shutil.move(self.path('tmp', 'input_0.png_h.txt'),
                    self.path('tmp', 'H_input_0.txt'))
        shutil.move(self.path('tmp', 'input_1.png_h.txt'),
                    self.path('tmp', 'H_input_1.txt'))

        urld = {'new_input' : self.url('index'),
                'run' : self.url('run'),
                'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')],
                'output' : [self.url('tmp', 'H_input_0.png'),
                           self.url('tmp', 'H_input_1.png')],
                'orsa' : self.url('tmp', 'orsa.txt'),
                'homo_0' : self.url('tmp', 'H_input_0.txt'),
                'homo_1' : self.url('tmp', 'H_input_1.txt')}
                
        return self.tmpl_out("result.html", urld=urld,
                             run_time="%0.2f" % run_time,
                             height=image(self.path('tmp', 
                                                    'input_0.png')).size[1],
                             stdout=open(self.path('tmp', 
                                                   'stdout.txt'), 'r').read())
