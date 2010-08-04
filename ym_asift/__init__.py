"""
demo example for the X->aX+b transform
"""

from base_demo import app as base_app
from lib import get_check_key, http_redirect_303, app_expose, index_dict
import os.path
import time

class app(base_app):
    """ template demo app """
    
    title = "ASIFT: A New Framework for Fully Affine Invariant Comparison"
    description = """This program performs the affine scale-invariant
    matching method known as ASIFT.<br />
    Please select two images; color images will be converted into gray
    level."""

    input_nb = 2 # number of input images
    #input_max_pixels = # max size (in pixels) of an input image
    #input_max_weight = # max size (in bytes) of an input file
    input_dtype = '1x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    output_ext = '.png'  # output image extention (ie. file format)
    display_ext = '.png' # displayed image extention (ie. file format)
    is_test = True;      # switch to False for deployment

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

    # run() is defined here,
    # because the parameters validation depends on the algorithm
    @get_check_key
    def run(self):
        """
        params handling and run redirection
        """
        # no parameters
        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')]}
        return self.tmpl_out("run.html", urld=urld)
    run.exposed = True

    # run_algo() is defined here,
    # because it is the actual algorithm execution, hence specific
    # run_algo() is called from result(),
    # with the parameters validated in run()
    def run_algo(self):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        run_time = time.time()
        p = self.run_proc(['asift', 'input_0.png', 'input_1.png', 
                           'outputV.png', 'outputH.png',
                           'match.txt', 'keys_0.txt', 'keys_1.txt'])
        returncode, stdout, stderr = self.wait_proc(p)
        stdout_file = open(self.path('tmp', 'stdout.txt'), 'w')
        stdout_file.write(stdout)
        stderr_file = open(self.path('tmp', 'stderr.txt'), 'w')
        stderr_file.write(stderr)
        run_time = time.time() - run_time

        if (0 != returncode):
            return -1
        return run_time

    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # no parameters
        run_time = self.run_algo()
#        if (0 > run_time):
#            return self.error(error='run-time error')
        self.log("input processed")
        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')],
                'output' : [self.url('tmp', 'outputH.png'),
                            self.url('tmp', 'outputV.png')],
                'match' : self.url('tmp', 'match.txt'),
                'keys_0' : self.url('tmp', 'keys_0.txt'),
                'keys_1' : self.url('tmp', 'keys_1.txt')}
        stdout_file = open(self.path('tmp', 'stdout.txt'), 'r')
        stderr_file = open(self.path('tmp', 'stderr.txt'), 'r')
        return self.tmpl_out("result.html", urld=urld,
                             run_time="%0.2f" % run_time,
                             stdout=stdout_file.read(),
                             stderr=stderr_file.read())
    result.exposed = True
