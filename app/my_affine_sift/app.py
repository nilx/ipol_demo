"""
ASIFT demo interaction script
"""
# pylint: disable=C0103

from lib import base_app, image, build, http
from lib.misc import app_expose, ctime
from lib.base_app import init_app
from cherrypy import TimeoutError
import cherrypy
import os.path
import time
import shutil

class app(base_app):
    """ demo app """
    
    title = "ASIFT: A New Framework for Fully Affine Invariant Comparison"

    input_nb = 2
    input_max_pixels = None
    input_max_method = 'zoom'
    input_dtype = '1x8i'
    input_ext = '.png'
    timeout = 60
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

    def build(self):
        """
        program build/update
        """
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        # store common file path in variables
        asift_tgz_file = self.dl_dir + "demo_ASIFT_src.tar.gz"
        asift_tgz_url = \
            "http://www.ipol.im/pub/algo/my_affine_sift/demo_ASIFT_src.tar.gz"
        asift_prog_file = self.bin_dir + "asift"
        asift_log_file = self.base_dir + "build_asift.log"
        sift_tgz_file = self.dl_dir + "SIFT_png.tar.gz"
        sift_tgz_url = \
            "http://www.ipol.im/pub/algo/my_affine_sift/SIFT_png.tar.gz"
        sift_prog_file = self.bin_dir + "sift"
        sift_log_file = self.base_dir + "build_sift.log"
        # get the latest source archive
        build.download(asift_tgz_url, asift_tgz_file)
        build.download(sift_tgz_url, sift_tgz_file)
        # ASIFT
        # test if the dest file is missing, or too old
        if (os.path.isfile(asift_prog_file)
            and ctime(asift_tgz_file) < ctime(asift_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(asift_tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s demo_ASIFT OMP=1" %
                      (self.src_dir + "demo_ASIFT_src"),
                      stdout=asift_log_file)
            # save into bin dir
            shutil.copy(self.src_dir + os.path.join("demo_ASIFT_src",
                                                    "demo_ASIFT"),
                        asift_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        # SIFT
        # test if the dest file is missing, or too old
        if (os.path.isfile(sift_prog_file)
            and ctime(sift_tgz_file) < ctime(sift_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(sift_tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s demo_SIFT OMP=1" %
                      (self.src_dir + "SIFT_png"),
                      stdout=sift_log_file)
            # save into bin dir
            shutil.copy(self.src_dir + os.path.join("SIFT_png", "demo_SIFT"),
                        sift_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    @cherrypy.expose
    @init_app
    def wait(self):
        """
        params handling and run redirection
        """
        # no parameters
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout, stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="Try again with simpler images.")
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="first uploaded image")
            ar.add_file("input_1.orig.png", info="second uploaded image")
            ar.add_file("input_0.png", info="first input image")
            ar.add_file("input_1.png", info="second input image")
            ar.add_file("output_SIFT_V.png", info="SIFT matches")
            ar.add_file("output_ASIFT_V.png", info="ASIFT matches")
            ar.add_file("match_ASIFT.txt", compress=True)
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        asift = self.run_proc(['asift', 'input_0.png', 'input_1.png', 
                               'output_ASIFT_V.png', 'output_ASIFT_H.png',
                               'match_ASIFT.txt',
                               'keys_0_ASIFT.txt', 'keys_1_ASIFT.txt'],
                              stdout=stdout, stderr=stdout)
        sift = self.run_proc(['sift', 'input_0.png', 'input_1.png', 
                              'output_SIFT_V.png', 'output_SIFT_H.png',
                              'match_SIFT.txt',
                              'keys_0_SIFT.txt', 'keys_1_SIFT.txt'],
                             stdout=None, stderr=None)
        self.wait_proc([asift, sift], timeout)
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        return self.tmpl_out("result.html",
                             height=image(self.work_dir 
                                          + 'output_ASIFT_V.png').size[1])
