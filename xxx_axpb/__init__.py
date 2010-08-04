"""
demo example for the X->aX+b transform
"""

from base_demo import app as base_app
from lib import get_check_key, http_redirect_303, app_expose, index_dict
import os.path

class app(base_app):
    """ template demo app """
    
    title = "example : ax + b"
    description = """This example demo interface performs the simple
    <i>f(x) = ax + b</i> transform on an image."""

    input_nb = 1 # number of input images
    input_max_pixels = 500000 # max size (in pixels) of an input image
    input_max_weight = 1 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
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
    def run(self, a="1.", b="0"):
        """
        params handling and run redirection
        """
        # save and validate the parameters
        try:
            params_file = index_dict(self.path('tmp'))
            params_file['params'] = {'a' : float(a),
                                     'b' : float(b)}
            params_file.save()
        except:
            return self.error(error='invalid parameters')

        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'input' : [self.url('tmp', 'input_0.png')]}
        return self.tmpl_out("run.html", urld=urld)
    run.exposed = True

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
        returncode, stdin, stdout = self.wait_proc(p)
        assert(0 == returncode)

    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # read the parameters
        params_file = index_dict(self.path('tmp'))
        a = params_file['params']['a']
        b = params_file['params']['b']
        # run the algorithm
        self.run_algo(a, b)
        self.log("input processed")
        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png')],
                'output' : [self.url('tmp', 'output.png')]}
        return self.tmpl_out("result.html", urld=urld)
    result.exposed = True
