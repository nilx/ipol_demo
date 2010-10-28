"""
Binocular Stereo Pipeline
"""
# pylint: disable=C0103

from lib import base_app
from lib import image
from lib import build
from lib import http
from lib.misc import get_check_key, app_expose, ctime
from cherrypy import TimeoutError
import os.path
import time
import cherrypy
import shutil

#
# INTERACTION
#

class app(base_app):
    """ template demo app """
    
    title = "Binocular Stereo Pipeline"

    input_nb = 2 # number of input images
    input_max_pixels = 640 * 480 # max size (in pixels) of an input image
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
        tgz_file = os.path.join(self.dl_dir, "MissStereo.tar.gz")
        tgz_url = "https://edit.ipol.im/edit/algo/" + \
            "m_quasi_euclidean_epipolar_rectification/MissStereo.tar.gz"
        build_dir = os.path.join(self.src_dir, "MissStereo", "build")
        src_bin = dict([(os.path.join(build_dir, "bin", prog),
                         os.path.join(self.bin_dir, prog))
                        for prog in ["homography", "orsa", "rectify",
                                     "sift", "size", "stereo",
                                     "convert", "mesh"]])
        src_bin[os.path.join(self.src_dir, "MissStereo",
                             "scripts", "MissStereo.sh")] \
            = os.path.join(self.bin_dir, "MissStereo.sh")
        log_file = os.path.join(self.base_dir, "build.log")
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if any of the dest files is missing, or too old
        if all([(os.path.isfile(bin_file) and ctime(tgz_file) < ctime(bin_file))
                for bin_file in src_bin.values()]):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            os.mkdir(build_dir)
            build.run("cmake -D CMAKE_BUILD_TYPE:string=Release ../src",
                      stdout=log_file, cwd=build_dir,
                      env={'CC':'ccache cc', 'CXX':'ccache c++'})
            build.run("make -C %s -j4" % build_dir,
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for (src, dst) in src_bin.items():
                shutil.copy(src, dst)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #
    # PARAMETER HANDLING
    #

    @cherrypy.expose
    @get_check_key
    def params(self, newrun=False, msg=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        if (image(os.path.join(self.key_dir, 'input_0.png')).size
            != image(os.path.join(self.key_dir, 'input_1.png')).size):
            return self.error('badparams',
                              "The images must have the same size")
        return self.tmpl_out("params.html", msg=msg,
                             input=[self.key_url + 'input_%i.png' % i
                                    for i in range(self.input_nb)])

    @cherrypy.expose
    @get_check_key
    def run(self, **kwargs):
        """
        params handling and run redirection
        """
        # no parameter
        # redirect to the result page
        http.refresh(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html", 
                             input=[self.key_url + 'input_0.png',
                                    self.key_url + 'tmp', 'input_1.png'],
                             height=image(os.path.join(self.key_dir, 
                                                       'input_0.png')).size[1])

    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        # run Rectify.sh
        stdout = open(os.path.join(self.key_dir, 'stdout.txt'), 'w')
        p = self.run_proc(['MissStereo.sh',
                           os.path.join(self.key_dir, 'input_0.png'),
                           os.path.join(self.key_dir, 'input_1.png')],
                          stdout=stdout, stderr=stdout)
        self.wait_proc(p, timeout)
        stdout.close()

        return

    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # TODO check image size
        # no parameters
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout)
            run_time = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="""
The algorithm took more than %i seconds and had to be interrupted.
Try again with simpler images.""" % self.timeout)
        except RuntimeError:
            return self.error(errcode='retime',
                              errmsg="""
The program ended with a failure return code,
something must have gone wrong""")
        self.log("input processed")
        
        shutil.move(os.path.join(self.key_dir,
                                 'input_0.png_input_1.png_pairs_orsa.txt'),
                    os.path.join(self.key_dir, 'orsa.txt'))
        shutil.move(os.path.join(self.key_dir, 'input_0.png_h.txt'),
                    os.path.join(self.key_dir, 'H_input_0.txt'))
        shutil.move(os.path.join(self.key_dir, 'input_1.png_h.txt'),
                    os.path.join(self.key_dir, 'H_input_1.txt'))
        shutil.move(os.path.join(self.key_dir, 'disp1_H_input_0.png.png'),
                    os.path.join(self.key_dir, 'disp1_H_input_0.png'))
        shutil.move(os.path.join(self.key_dir, 'disp3_H_input_0.png.png'),
                    os.path.join(self.key_dir, 'disp3_H_input_0.png'))
        shutil.move(os.path.join(self.key_dir, 'disp1_H_input_0.png_float.tif'),
                    os.path.join(self.key_dir, 'disp1_H_input_0.tif'))
        shutil.move(os.path.join(self.key_dir, 'disp2_H_input_0.png_float.tif'),
                    os.path.join(self.key_dir, 'disp2_H_input_0.tif'))
        shutil.move(os.path.join(self.key_dir, 'disp3_H_input_0.png_float.tif'),
                    os.path.join(self.key_dir, 'disp3_H_input_0.tif'))
        shutil.move(os.path.join(self.key_dir, 'disp3_H_input_0.png.ply'),
                    os.path.join(self.key_dir, 'disp3_H_input_0.ply'))

        return self.tmpl_out("result.html",
                             input=[self.key_url + 'input_0.png',
                                    self.key_url + 'input_1.png'],
                             disp=[self.key_url + 'disp1_H_input_0.png',
                                   self.key_url + 'disp3_H_input_0.png'],
                             rect=[self.key_url + 'H_input_0.png',
                                   self.key_url + 'H_input_1.png'],
                             orsa=self.key_url + 'orsa.txt',
                             homo=[self.key_url + 'H_input_0.txt',
                                   self.key_url + 'H_input_1.txt'],
                             exact=[self.key_url + 'disp1_H_input_0.tif',
                                    self.key_url + 'disp2_H_input_0.tif',
                                    self.key_url + 'disp3_H_input_0.tif'],
                             ply=self.key_url + 'disp3_H_input_0.ply',
                             run_time="%0.2f" % run_time,
                             height=image(os.path.join(self.key_dir, 
                                                       'input_0.png')).size[1],
                             stdout=open(os.path.join(self.key_dir, 
                                                      'stdout.txt'), 'r').read())
