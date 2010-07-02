"""
simple test ipol demo web app
"""

from base_demo import base_app
import os.path

class app(base_app):
    """ simple demo app """

    title = "color inversion"
    description = "This test demo inverts the colors of an image."

    input_nb = 1
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_weight = 5 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    output_ext = '.png' # output image extention (ie. file format)
    display_ext = '.gif' # displayed image extention (ie. file format)

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # TODO : simplify
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        base_app.params.im_func.exposed = True
        base_app.run.im_func.exposed = True
        base_app.result.im_func.exposed = True

    # params() and results() are customized by their template
    # run_algo() is defined here
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
