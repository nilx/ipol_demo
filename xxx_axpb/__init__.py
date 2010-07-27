"""
demo example for the X->aX+b transform
"""

from base_demo import app as base_app
from lib import get_check_key, http_redirect_303
import os.path

class app(base_app):
    """ template demo app """
    
    title = "[TEST] example : ax + b"
    description = """This example demo interface performs the simple
    <i>f(x) = ax + b</i> transform on an image."""

    input_nb = 1 # number of input images
    input_max_pixels = 500000 # max size (in pixels) of an input image
    input_max_weight = 1 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.tiff'  # input image expected extension (ie file format)
    output_ext = '.tiff' # output image extention (ie. file format)
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
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True

    # run() is defined here,
    # because the parameters validation depends on the algorithm
    @get_check_key
    def run(self):
        """
        params handling and run redirection
        as a special case, we have no parameter to check and pass
        """
        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'next_step' : self.url('result'),
                'input' : [self.url('tmp', 'input_%i' % i + self.display_ext)
                           for i in range(self.input_nb)]}
        return self.tmpl_out("run.html", urld=urld)
    run.exposed = True

    # run_algo() is defined here,
    # because it is the actual algorithm execution, hence specific
    # run_algo() is called from result(),
    # with the parameters validated in run()
    def run_algo(self, params):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        from PIL import Image
        im = Image.open(self.path('tmp', 'input_0.png'))
        im = im.point(lambda x : 256 - x)
        # save the result, internal version
        im.save(self.path('tmp', 'output.png'))
        # save the result, embedable version
        im.save(self.path('tmp', 'output.gif'))
