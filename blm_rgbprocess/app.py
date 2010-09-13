"""
rgbprocess ipol demo web app
"""

from base_demo import app as base_app
from lib import get_check_key, http_redirect_303
from lib import TimeoutError, RuntimeError
import os.path
import time

class app(base_app):
    """ rgbprocess app """

    title = "RGB process"
    description = "Processing of the RGB color cube of an image"

    input_nb = 1
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    display_ext = '.png' # displayed image extention (ie. file format)
    is_test = True;

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # TODO : simplify
        # index() and input_xxx() are generic
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
    def run_algo(self, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

	"""
	Version 1

        p = self.run_proc(['rgbprocess', 'filter', 'input_0.png', 'output.png'])
	p2 = self.run_proc(['rgbprocess', 'rmisolated', 'input_0.png', 'output_0.png'])
	self.wait_proc(p2)
	wOut=256
	hOut=256
	#p3 = self.run_proc(['rgbprocess', 'pcaviews', 'output_0.png', 'output_0.png', 'view12.png', 'view13.png', 'view23.png', str(wOut), str(hOut)])
	p3 = self.run_proc(['rgbprocess', 'pcaviewsB', 'output_0.png', 'output_0.png', 'view123.png', str(wOut), str(hOut)])
	self.wait_proc(p)
	p4 = self.run_proc(['rgbprocess', 'rmisolated', 'output.png', 'output_1.png'])
	self.wait_proc(p4)
	#p5 = self.run_proc(['rgbprocess', 'pcaviews', 'output_1.png', 'input_0.png', 'outview12.png', 'outview13.png', 'outview23.png', str(wOut), str(hOut)])
	p5 = self.run_proc(['rgbprocess', 'pcaviewsB', 'output_1.png', 'output_0.png', 'outview123.png', str(wOut), str(hOut)])
	p6 = self.run_proc(['rgbprocess', 'density', 'output_1.png', 'output_0.png', 'dstview123.png', str(wOut), str(hOut)])
	self.wait_proc(p3)
	self.wait_proc(p5)
	self.wait_proc(p6)
        return
	"""

	"""
	Version 2
	"""
	p = self.run_proc(['rgbprocess', 'rmisolated', 'input_0.png', 'input_1.png'], stdout=stdout, stderr=stdout)
	self.wait_proc(p)
	wOut=256
	hOut=256
	p2 = self.run_proc(['rgbprocess', 'pcaviewsB', 'input_1.png', 'input_1.png', 'view123.png', str(wOut), str(hOut)], stdout=stdout, stderr=stdout)
        p3 = self.run_proc(['rgbprocess', 'filter', 'input_1.png', 'output_1.png'], stdout=stdout, stderr=stdout)
	self.wait_proc(p3)
	p4 = self.run_proc(['rgbprocess', 'pcaviewsB', 'output_1.png', 'input_1.png', 'outview123.png', str(wOut), str(hOut)], stdout=stdout, stderr=stdout)
	p5 = self.run_proc(['rgbprocess', 'density', 'output_1.png', 'input_1.png', 'dstview123.png', str(wOut), str(hOut)], stdout=stdout, stderr=stdout)
	p6 = self.run_proc(['rgbprocess', 'combineimages', 'output_1.png', 'input_0.png', 'output_2.png'], stdout=stdout, stderr=stdout)
	self.wait_proc([p2, p4, p5, p6])



    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # run the algorithm
        stdout = open(self.path('tmp', 'stdout.txt'), 'w')
        try:
            run_time = time.time()
            self.run_algo(stdout=stdout)
            run_time = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')
        self.log("input processed")

	"""
	Version 1

        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png')],
                #'inputViews' : [self.url('tmp', 'view12.png'), self.url('tmp', 'view13.png'), self.url('tmp', 'view23.png')],
                'inputViews' : [self.url('tmp', 'view123.png')],
                'output' : [self.url('tmp', 'output.png')],
                #'outputViews' : [self.url('tmp', 'outview12.png'), self.url('tmp', 'outview13.png'), self.url('tmp', 'outview23.png')]
                #'outputViews' : [self.url('tmp', 'outview123.png')]
                'outputViews' : [self.url('tmp', 'outview123.png'), self.url('tmp', 'dstview123.png')]
		}
	"""

	"""
	Version 2
	"""
        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png'), self.url('tmp', 'input_1.png')],
                'inputViews' : [self.url('tmp', 'view123.png')],
                'output' : [self.url('tmp', 'output_2.png')],
                'outputViews' : [self.url('tmp', 'outview123.png'), self.url('tmp', 'dstview123.png')]
		}


        #return self.tmpl_out("result.html", urld=urld, run_time="%0.2f" % run_time)
        return self.tmpl_out("result2.html", urld=urld, run_time="%0.2f" % run_time)
    result.exposed = True

