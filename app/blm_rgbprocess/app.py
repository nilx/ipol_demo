"""
rgbprocess ipol demo web app
"""
# pylint: disable=C0103

from lib import base_app
from lib import build
from lib import http
from lib.misc import get_check_key, ctime
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time

class app(base_app):
    """ rgbprocess app """

    title = "RGB process"

    input_nb = 1
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = True

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() and input_xxx() are generic
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True

    def build(self):
        """
        program build/update
        """
        # store common file path in variables
        tgz_url = "https://edit.ipol.im/edit/algo/" \
            + "blm_color_dimensional_filtering/rgbprocess.tar.gz"
        tgz_file = os.path.join(self.dl_dir, "rgbprocess.tar.gz")
        prog_file = os.path.join(self.bin_dir, "rgbprocess")
        log_file = os.path.join(self.base_dir, "build.log")
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -C %s rgbprocess"
                      % os.path.join(self.src_dir, "rgbprocess")
                      + " CXX='ccache c++' -j4", stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(os.path.join(self.src_dir, 
                                     "rgbprocess", "rgbprocess"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    # run() is defined here,
    # because the parameters validation depends on the algorithm
    @cherrypy.expose
    @get_check_key
    def run(self):
        """
        params handling and run redirection
        as a special case, we have no parameter to check and pass
        """
        http.refresh(self.url('result?key=%s' % self.key))
        urld = {'next_step' : self.url('result'),
                'input' : [self.url('tmp', 'input_%i.png' % i)
                           for i in range(self.input_nb)]}
        return self.tmpl_out("run.html", urld=urld)

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

        p = self.run_proc(['rgbprocess', 'filter',
                           'input_0.png', 'output.png'])
        p2 = self.run_proc(['rgbprocess', 'rmisolated',
                            'input_0.png', 'output_0.png'])
        self.wait_proc(p2)
        wOut=256
        hOut=256
        #p3 = self.run_proc(['rgbprocess', 'pcaviews',
        #                    'output_0.png', 'output_0.png',
        #                    'view12.png', 'view13.png', 'view23.png',
        #                    str(wOut), str(hOut)])
        p3 = self.run_proc(['rgbprocess', 'pcaviewsB',
                            'output_0.png', 'output_0.png',
                            'view123.png', str(wOut), str(hOut)])
        self.wait_proc(p)
        p4 = self.run_proc(['rgbprocess', 'rmisolated',
                            'output.png', 'output_1.png'])
        self.wait_proc(p4)
        #p5 = self.run_proc(['rgbprocess', 'pcaviews',
        #                    'output_1.png', 'input_0.png',
        #                    'outview12.png', 'outview13.png', 'outview23.png',
        #                    str(wOut), str(hOut)])
        p5 = self.run_proc(['rgbprocess', 'pcaviewsB',
                            'output_1.png', 'output_0.png',
                            'outview123.png', str(wOut), str(hOut)])
        p6 = self.run_proc(['rgbprocess', 'density',
                            'output_1.png', 'output_0.png',
                            'dstview123.png', str(wOut), str(hOut)])
        self.wait_proc(p3)
        self.wait_proc(p5)
        self.wait_proc(p6)
        return
        """

        """
        Version 2

        p = self.run_proc(['rgbprocess', 'rmisolated',
                           'input_0.png', 'input_1.png'],
                          stdout=stdout, stderr=stdout)
        self.wait_proc(p, timeout)
        wOut = 256
        hOut = 256
        p2 = self.run_proc(['rgbprocess', 'pcaviewsB',
                            'input_1.png', 'input_1.png', 'view123.png',
                            str(wOut), str(hOut)], stdout=stdout, stderr=stdout)
        p3 = self.run_proc(['rgbprocess', 'filter',
                            'input_1.png', 'output_1.png'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc(p3, timeout)
        p4 = self.run_proc(['rgbprocess', 'pcaviewsB', 
                            'output_1.png', 'input_1.png', 'outview123.png',
                            str(wOut), str(hOut)], stdout=stdout, stderr=stdout)
        p5 = self.run_proc(['rgbprocess', 'density',
                            'output_1.png', 'input_1.png', 'dstview123.png',
                            str(wOut), str(hOut)], stdout=stdout, stderr=stdout)
        p6 = self.run_proc(['rgbprocess', 'combineimages',
                            'output_1.png', 'input_0.png', 'output_2.png'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc([p2, p4, p5, p6], timeout)
	"""

	""" 
	Version 3

	"""

	print "remove isolated"
        p1 = self.run_proc(['rgbprocess', 'rmisolated', 'input_0.png', 'input_1.png'], stdout=stdout, stderr=stdout)

	print "view parameters"
        p2 = self.run_proc(['rgbprocess', 'RGBviewsparams', 'RGBviewsparams.txt'], stdout=stdout, stderr=stdout)
        self.wait_proc([p1, p2], timeout)

	print "LLP2"
        p3 = self.run_proc(['rgbprocess', 'filter', 'input_1.png', 'output_1.png'],
                           stdout=stdout, stderr=stdout)
        wOut = 256
        hOut = 256
	displayDensity=0
	print "original views"
        p4 = self.run_proc(['rgbprocess', 'RGBviews', 'input_1.png', 'RGBviewsparams.txt', 'inRGB', 
			   str(wOut), str(hOut), str(displayDensity)], stdout=stdout, stderr=stdout)
        self.wait_proc([p3, p4], timeout)


	print "filtered views"
        p5 = self.run_proc(['rgbprocess', 'RGBviews', 'output_1.png', 'RGBviewsparams.txt', 'outRGB', 
			   str(wOut), str(hOut), str(displayDensity)], stdout=stdout, stderr=stdout)
 	displayDensity=1

	print "density views"
        p6 = self.run_proc(['rgbprocess', 'RGBviews', 'output_1.png', 'RGBviewsparams.txt', 'dstyRGB', 
			   str(wOut), str(hOut), str(displayDensity)], stdout=stdout, stderr=stdout)
        self.wait_proc([p5, p6], timeout)

 	print "combine views"
        p7 = self.run_proc(['rgbprocess', 'combineviews', 'RGBviewsparams.txt', 'inRGB', 'outRGB', 'dstyRGB', 'view'], 
			   stdout=stdout, stderr=stdout)

	print "merge images"
        p8 = self.run_proc(['rgbprocess', 'mergeimages', 'output_1.png', 'input_0.png', 'output_2.png'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc([p7, p8], timeout)


    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # run the algorithm
        stdout = open(os.path.join(self.key_dir, 'stdout.txt'), 'w')
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
                #'inputViews' : [self.url('tmp', 'view12.png'),
                #self.url('tmp', 'view13.png'),
                #self.url('tmp', 'view23.png')],
                'inputViews' : [self.url('tmp', 'view123.png')],
                'output' : [self.url('tmp', 'output.png')],
                #'outputViews' : [self.url('tmp', 'outview12.png'),
                #                 self.url('tmp', 'outview13.png'),
                #                 self.url('tmp', 'outview23.png')]
                #'outputViews' : [self.url('tmp', 'outview123.png')]
                'outputViews' : [self.url('tmp', 'outview123.png'),
                                 self.url('tmp', 'dstview123.png')]
                }
        """

        """
        Version 2

        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')],
                'inputViews' : [self.url('tmp', 'view123.png')],
                'output' : [self.url('tmp', 'output_2.png')],
                'outputViews' : [self.url('tmp', 'outview123.png'),
                                 self.url('tmp', 'dstview123.png')]
                }

	"""

        """
        Version 3
	"""

        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png')],
                'output' : [self.url('tmp', 'output_2.png')],
                'views' : [self.url('tmp', 'view_%i.png' % i) 
			   for i in range(100, 127)]
                }


        #return self.tmpl_out("result.html", urld=urld,
        #                     run_time="%0.2f" % run_time)
        #return self.tmpl_out("result2.html", urld=urld,
        #                    run_time="%0.2f" % run_time)
        return self.tmpl_out("result3.html", urld=urld,
                            run_time="%0.2f" % run_time)



