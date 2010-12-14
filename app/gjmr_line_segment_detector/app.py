"""
LSD demo
"""
# pylint: disable=C0103

from lib import base_app, build, http, image
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import time

class app(base_app):
    """ template demo app """
    
    title = "LSD: a Line Segment Detector"
    input_nb = 1 # number of input images
    input_max_pixels = 100000000 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes)
                                        # of an input file 
    input_dtype = '1x8i' # input image expected data type
    input_ext = '.pgm'   # input image expected extension (ie file format)
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
        tgz_file = self.dl_dir + "lsd-1.5.zip"
        prog_file = self.bin_dir + "lsd"
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download("http://www.ipol.im/pub/algo/"
                       + "gjmr_line_segment_detector/lsd-1.5.zip", tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -C %s"
                      % (self.src_dir + "lsd-1.5")
                      + " -j4", stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir + os.path.join("lsd-1.5","lsd"),
                        prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    @cherrypy.expose
    @init_app
    def wait(self):
        """
        params handling and run redirection
        """
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # run the algorithm
        try:
           run_time = time.time()
           self.run_algo()
           # save the run time in the config dict
           self.cfg['info']['run_time'] = time.time() - run_time
           self.cfg.save()
        except TimeoutError:
           return self.error(errcode='timeout',
                             errmsg="Try again with simpler images.")
        except RuntimeError:
           return self.error(errcode='runtime',
                             errmsg="Something went wrong with the program.")
        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.png","input.png")
            ar.add_file("output.txt", compress=True)
            ar.add_file("output.eps", compress=True)
            ar.add_file("output.svg", compress=True)
            ar.add_file("output.png")
            try:
                version_file = open(self.work_dir + "version.txt", "w")
                p = self.run_proc(["lsd", "--version"], stdout=version_file)
                self.wait_proc(p)
                version_file.close()
                version_file = open(self.work_dir + "version.txt", "r")
                version_info = version_file.readline()
                version_file.close()
            except Exception:
                version_info = "unknown"
            ar.add_info({"code version" : version_info})
            ar.add_info({"run time" : self.cfg['info']['run_time']})
            ar.save()
        return self.tmpl_out("run.html")

    def run_algo(self):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        p = self.run_proc(['lsd','-P','output.eps','-S','output.svg',
                           'input_0.pgm','output.txt']) 
        self.wait_proc(p)
        try:
            p = self.run_proc(['/usr/bin/gs','-dNOPAUSE','-dBATCH',
                               '-sDEVICE=pnggray','-dGraphicsAlphaBits=4',
                               '-r72','-dEPSCrop','-sOutputFile=output.png',
                               'output.eps'])
            self.wait_proc(p)
        except OSError:
            self.log("eps->png conversion failed,"
                     + " gs is probably missing on this system")
        im = image(self.work_dir + "output.png")
        im.invert()
        im.save(self.work_dir + "output.png")
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        return self.tmpl_out("result.html",
                             with_png=os.path.isfile(self.work_dir 
                                                     + 'output.png'),
                             height=image(self.work_dir
                                          + 'input_0.png').size[1])
