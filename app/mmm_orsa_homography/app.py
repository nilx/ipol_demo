"""
Image registration with a contrario RANSAC variant
"""

from lib import base_app, image, http, build
from lib.misc import app_expose, ctime
from lib.base_app import init_app
from cherrypy import TimeoutError
import os.path
import time
import cherrypy
import shutil

#
# INTERACTION
#

class NoMatchError(RuntimeError):
    """ Exception raised when ORSA fails """
    pass

class app(base_app):
    """ template demo app """
    
    title = "Image registration with a contrario RANSAC variant"

    input_nb = 2 # number of input images
    input_max_pixels = 1600 * 1200 # max size (in pixels) of an input image
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)    
    is_test = False      # switch to False for deployment

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

    def build(self):
        """
        program build/update
        """
        # store common file path in variables
        tgz_file = self.dl_dir + "OrsaHomography.tar.gz"
        tgz_url = "http://www.ipol.im/pub/algo/mmm_orsa_homography/" + \
            "OrsaHomography.tar.gz"
        build_dir = (self.src_dir
                     + os.path.join("OrsaHomography", "build") + os.path.sep)
        exe = build_dir + os.path.join("demo","demo_orsa_homography")
        prog = self.bin_dir + "demo_orsa_homography"
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if any of the dest files is missing, or too old
        if os.path.isfile(prog) and ctime(tgz_file) < ctime(prog):
            cherrypy.log("no rebuild needed", context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            os.mkdir(build_dir)
            build.run("cmake -D CMAKE_BUILD_TYPE:string=Release ../src",
                      stdout=log_file, cwd=build_dir)
            build.run("make -C %s -j4" % build_dir,
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(exe, prog)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #
    # PARAMETER HANDLING
    #

    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        height = max(image(self.work_dir + 'input_0.png').size[1],
                     image(self.work_dir + 'input_1.png').size[1])
        return self.tmpl_out("params.html", height=height)

    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        if 'precision' in kwargs:
            self.cfg['param']['precision'] = kwargs['precision']
            self.cfg.save()
        # no parameter
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        height = max(image(self.work_dir + 'input_0.png').size[1],
                     image(self.work_dir + 'input_1.png').size[1])
        return self.tmpl_out("wait.html", height=height)

    @cherrypy.expose
    @init_app
    def run(self, **kwargs):
        """
        algorithm execution
        """
        success = False
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except NoMatchError:
            http.redir_303(self.base_url +
                           'result?key=%s&error_nomatch=1' % self.key)
        except RuntimeError:
            return self.error(errcode='runtime')
        else:
            http.redir_303(self.base_url + 'result?key=%s' % self.key)
            success = True

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="uploaded #1")
            ar.add_file("input_1.orig.png", info="uploaded #2")
            ar.add_file("input_0.png", info="input #1")
            ar.add_file("input_1.png", info="input #2")
            if 'precision' in self.cfg['param']:
                ar.add_info({"precision": self.cfg['param']['precision']})
            ar.add_file("match.txt", compress=True)
            ar.add_file("matchOrsa.txt", compress=True)
            ar.add_file("outliers.png", info="outliers image")
            if success:
                ar.add_file("inliers.png", info="inliers image")
                ar.add_file("panorama.png", info="panorama")
                ar.add_file("registered_0.png", info="registered image #1")
                ar.add_file("registered_1.png", info="registered image #2")
            ar.add_file("stdout.txt", compress=True)
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        precision = "0"
        if 'precision' in self.cfg['param']:
            try:
                float(self.cfg['param']['precision'])
                precision = str(self.cfg['param']['precision'])
            except ValueError:
                pass
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        proc = self.run_proc(['demo_orsa_homography',
                              self.work_dir + 'input_0.png',
                              self.work_dir + 'input_1.png',
                              precision,
                              "match.txt",
                              "matchOrsa.txt",
                              "inliers.png",
                              "outliers.png",
                              "panorama.png",
                              "registered_0.png",
                              "registered_1.png"],
                             stdout=stdout, stderr=stdout)
        try:
            self.wait_proc(proc, timeout)
        except RuntimeError:
            if 0 != proc.returncode:
                stdout.close()
                raise NoMatchError
            else:
                raise
        stdout.close()
        return

    @cherrypy.expose
    @init_app
    def result(self, error_nomatch=None):
        """
        display the algo results
        """
        height = max(image(self.work_dir + 'input_0.png').size[1],
                     image(self.work_dir + 'input_1.png').size[1])
        if error_nomatch:
            return self.tmpl_out("result_nomatch.html", height=height)
        else:
            return self.tmpl_out("result.html", height=height)
