"""
retinex Poisson equation ipol demo web app
"""
# pylint: disable=C0103

from lib import base_app, build, http, image
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time

PRIMES_2_3_5_7 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 16, 
                  18, 20, 21, 24, 25, 27, 28, 30, 32, 
                  35, 36, 40, 42, 45, 48, 49, 50, 54, 56, 60, 63, 64, 
                  70, 72, 75, 80, 81, 84, 90, 96, 
                  98, 100, 105, 108, 112, 120, 125, 126, 128, 
                  135, 140, 144, 147, 150, 160, 162, 168, 175, 180, 189, 192, 
                  196, 200, 210, 216, 224, 225, 240, 243, 245, 250, 252, 256, 
                  270, 280, 288, 294, 300, 315, 320, 
                  324, 336, 343, 350, 360, 375, 378, 384, 
                  392, 400, 405, 420, 432, 441, 448, 
                  450, 480, 486, 490, 500, 504, 512, 
                  525, 540, 560, 567, 576, 588, 600, 625, 630, 640, 
                  648, 672, 675, 686, 700, 720, 729, 735, 750, 756, 768, 
                  784, 800, 810, 840, 864, 875, 882, 896, 
                  900, 945, 960, 972, 980, 1000, 1008, 1024]

def closest_prime(primes=None, number=1):
    """
    fine the closest prime in the primes list
    """
    if None == primes:
        return None
    if number in primes:
        return number   
    elif number >= primes[-1]:
        return primes[-1]
    elif number <= primes[0]:
        return primes[0]
    else:
        i = 0
        while number > primes[i]:
            i += 1
        if (primes[i] - number) > (number - primes[i-1]):
            return primes[i]
        else:
            return primes[i-1]




class app(base_app):
    """ Retinex Poisson equation app """

    title = "Retinex Poisson Equation"

    input_nb = 1
    input_max_pixels = 700 * 700 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = False

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
        tgz_url = "https://edit.ipol.im/pub/algo/" \
            + "lmps_retinex_poisson_equation/retinex_pdeB.tar.gz"
        tgz_file = self.dl_dir + "retinex_pdeB.tar.gz"
        prog_file = self.bin_dir + "retinex_pde"
        log_file = self.base_dir + "build.log"
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
            build.run("make -j4 -C %s retinex_pde"
                      % (self.src_dir + "retinex_pdeB"),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir 
                        + os.path.join("retinex_pdeB", "retinex_pde"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return




    #
    # PARAMETER HANDLING
    #


    @cherrypy.expose
    @init_app
    def wait(self, t="4"):
        """
        params handling and run redirection
        """
        # save and validate the parameters
	if (float(t) < 0) or (float(t) > 255) :
	  return self.error(errcode='badparams',
                              errmsg="T must be a value between 0 and 255")
        try:
            self.cfg['param'] = {'t' : float(t)}
            self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        # read the parameters
        t = self.cfg['param']['t']
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(t, stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="uploaded image")
            ar.add_file("input_1.png", info="rescaled image")
            ar.add_file("output_1.png", info="result image")
            ar.add_info({"t": t})
            ar.save()

        return self.tmpl_out("run.html")


    def run_algo(self, t, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        # resize input image for better performance of FFT
        img = image(self.work_dir + 'input_0.png')
        size = img.size
        primes = PRIMES_2_3_5_7
        if (size[0] <= primes[-1]) and (size[1] <= primes[-1]):
           newsize = (closest_prime(primes, size[0]),
                      closest_prime(primes, size[1]))
        else:
           scale = float(primes[-1]) / max(size)
           newsize = (closest_prime(primes, size[0] * scale),
                      closest_prime(primes, size[1] * scale))
	img.resize(newsize);
	img.save(self.work_dir + 'input_1.png')

        p = self.run_proc(['retinex_pde', str(t), 'input_1.png', 'output_1.png'],
                           stdout=None, stderr=None)
        self.wait_proc(p, timeout)


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        # read the parameters
        t = self.cfg['param']['t']
        return self.tmpl_out("result.html", t=t,
                             sizeY="%i" % image(self.work_dir 
                                                + 'input_1.png').size[1])



