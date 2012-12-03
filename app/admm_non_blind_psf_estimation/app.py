"""
PSF Estimation demo interaction
"""

from lib import base_app, build, http, image
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import time

class app(base_app):
    """ demo app """
    
    title = "Non-parametric Sub-pixel Local Point Spread Function Estimation"
    input_nb = 1 # number of input images
    input_max_pixels = 4000000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '1x8i' # input image expected data type
    input_ext = '.pgm'   # input image expected extension (ie file format)
    is_test = False

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

        self.xlink_algo = 'http://www.ipol.im/pub/art/2012/admm-nppsf/'

    def build(self):
        """
        program build/update
        """
        # store common file path in variables
        tgz_file = self.dl_dir + "psfestim_1.3.tar.gz"
        prog_file = self.bin_dir + "psf_estim"
        pattern_file = self.bin_dir + "pattern_noise.pgm"
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download("http://www.ipol.im/pub/algo/" \
        "admm_non_blind_psf_estimation/psfestim_1.3.tar.gz", tgz_file)
        # test if the dest file is missing, or too old
        # dont rebuild the file
        if  (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)) :
            cherrypy.log("not rebuild needed",
            context='BUILD', traceback=False)
        else:
            #extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s psf_estim" 
                      % (self.src_dir + "psfestim_1.3"), stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir + os.path.join("psfestim_1.3", 
                        "psf_estim"), prog_file)
            shutil.copy(self.src_dir + os.path.join("psfestim_1.3",
                        "pattern_noise.pgm"), pattern_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    @cherrypy.expose
    @init_app
    def wait(self, s="4", k="17", t="1"):
        """
        params handling and run redirection
        """
        # save and validate the parameters
        try:
            self.cfg['param'] = {'s' : int(s),
                                 'k' : int(k),
                                 't' : int(t)}
            self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

                #Original:
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        #http.refresh(self.outside_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # read the parameters
        s = self.cfg['param']['s']
        k = self.cfg['param']['k']
        t = self.cfg['param']['t']
        # save standard output
        stdout = open(self.work_dir + 'stdout.txt', 'w')

        # run the algorithm
        try:
            run_time = time.time()
            self.run_algo(s, k, t, stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            stdout_text = open(self.work_dir + 'stdout.txt', 'r').read() 
            if stdout_text.find("No pattern was detected.")!=-1:
                return self.error("returncode",
                                  "Pattern Not Found. " + 
                                  "Are you sure that there's a pattern "+ 
                                  "in the image? " +
                                  "It may have not been detected if " +
                                  "pattern covers only a small part " +
                                  "of the image. Crop " +
                                  "the image so that the pattern covers at " +
                                  "least half of the image and re-run. " +
                                  "Otherwise, upload" +
                                  " an image containing a pattern.")
            if stdout_text.find("More than one pattern was detected.")!=-1:
                return self.error('returncode', 'More than one pattern was ' +
                                  'detected. Crop the image surounding the ' +
                                  'desired pattern and re-run.')
            return self.error('returncode', 'Unknown Run Time Error')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        #http.redir_303(self.outside_url + 'result?key=%s' % self.key)
        #http.refresh(self.outside_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.png")
            ar.add_file("psf.txt", compress=True)
            ar.add_file("stdout.txt", compress=True)
            ar.add_file("det_out.png")
            ar.add_file("psf.png")
            ar.add_info({"s": s, "k": k, "t": t})
            ar.add_info({"run time" : self.cfg['info']['run_time']})
            ar.save()
        return self.tmpl_out("run.html")

    def run_algo(self, s, k, t, stdout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        
        p = self.run_proc(['psf_estim',
                           '-p', self.bin_dir + 'pattern_noise.pgm',
                           '-s', str(s),
                           '-k', str(k),
                           '-d', 'det_out.ppm',
                           '-t', str(t),
                           '-o', 'psf.pgm',
                           'input_0.pgm', 'psf.txt'],
                            stdout=stdout, stderr=stdout)
        self.wait_proc(p)               
       
        im = image(self.work_dir + "psf.pgm")
        # re adjust width and height to avoid visualization interpolation
        width = 600
        height = 600
        # interpolate it by neareset neighbor
        im = im.resize((width, height), "nearest") 
        im.save(self.work_dir + "psf.png")
        
        im = image(self.work_dir + "det_out.ppm")
        im.save(self.work_dir + "det_out.png")
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        return self.tmpl_out("result.html",
                             height=image(self.work_dir
                                          + 'input_0.png').size[1])
