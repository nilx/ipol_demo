"""
Binocular Stereo Pipeline
"""
# pylint: disable=C0103

from lib import base_app, image, build, http
from lib.misc import init_app, app_expose, ctime, index_dict
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
        tgz_file = self.dl_dir + "MissStereo.tar.gz"
        tgz_url = "https://edit.ipol.im/edit/algo/" + \
            "m_quasi_euclidean_epipolar_rectification/MissStereo.tar.gz"
        build_dir = (self.src_dir + os.path.join("MissStereo", "build")
                     + os.path.sep)
        src_bin = dict([(build_dir + os.path.join("bin", prog),
                         self.bin_dir + prog)
                        for prog in ["homography", "orsa", "rectify",
                                     "sift", "size", "stereo",
                                     "convert", "mesh"]])
        src_bin[self.src_dir
                + os.path.join("MissStereo",
                               "scripts", "MissStereo.sh")] \
                               = os.path.join(self.bin_dir, "MissStereo.sh")
        log_file = self.base_dir + "build.log"
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
    @init_app
    def params(self, newrun=False, msg=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        if (image(self.work_dir + 'input_0.png').size
            != image(self.work_dir + 'input_1.png').size):
            return self.error('badparams',
                              "The images must have the same size")
        return self.tmpl_out("params.html", msg=msg,
                             input=[self.work_url + 'input_%i.png' % i
                                    for i in range(self.input_nb)])

    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html", 
                             input=[self.work_url + 'input_0.png',
                                    self.work_url + 'input_1.png'],
                             height=image(self.work_dir
                                          + 'input_0.png').size[1])

    @cherrypy.expose
    @init_app
    def run(self, **kwargs):
        """
        algorithm execution
        """
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout)
            params_file = index_dict(self.work_dir)
            params_file['params'] = {}
            params_file['params']['run_time'] = time.time() - run_time
            params_file.save()
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="Try again with simpler images.")
        except RuntimeError:
            return self.error(errcode='runtime')
        
        shutil.move(self.work_dir + 'input_0.png_input_1.png_pairs_orsa.txt',
                    self.work_dir + 'orsa.txt')
        shutil.move(self.work_dir + 'input_0.png_h.txt',
                    self.work_dir + 'H_input_0.txt')
        shutil.move(self.work_dir + 'input_1.png_h.txt',
                    self.work_dir + 'H_input_1.txt')
        shutil.move(self.work_dir + 'disp1_H_input_0.png.png',
                    self.work_dir + 'disp1_H_input_0.png')
        shutil.move(self.work_dir + 'disp3_H_input_0.png.png',
                    self.work_dir + 'disp3_H_input_0.png')
        shutil.move(self.work_dir + 'disp1_H_input_0.png_float.tif',
                    self.work_dir + 'disp1_H_input_0.tif')
        shutil.move(self.work_dir + 'disp2_H_input_0.png_float.tif',
                    self.work_dir + 'disp2_H_input_0.tif')
        shutil.move(self.work_dir + 'disp3_H_input_0.png_float.tif',
                    self.work_dir + 'disp3_H_input_0.tif')
        shutil.move(self.work_dir + 'disp3_H_input_0.png.ply',
                    self.work_dir + 'disp3_H_input_0.ply')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html")


    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        # run Rectify.sh
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        p = self.run_proc(['MissStereo.sh',
                           self.work_dir + 'input_0.png',
                           self.work_dir + 'input_1.png'],
                          stdout=stdout, stderr=stdout)
        self.wait_proc(p, timeout)
        stdout.close()

        mv_map = {'input_0.png_input_1.png_pairs_orsa.txt' : 'orsa.txt',
                  'input_0.png_h.txt' : 'homo_0.txt',
                  'input_1.png_h.txt' : 'homo_1.txt',
                  'disp1_H_input_0.png.png' : 'disp1_0.png',
                  'disp3_H_input_0.png.png' : 'disp3_0.png',
                  'disp1_H_input_0.png_float.tif' : 'disp1_0.tif',
                  'disp2_H_input_0.png_float.tif' : 'disp2_0.tif',
                  'disp3_H_input_0.png_float.tif' : 'disp3_0.tif',
                  'disp3_H_input_0.png.ply' : 'disp3_0.ply',
                  'H_input_0.png' : 'rect_0.png',
                  'H_input_1.png' : 'rect_1.png'}
        for (src, dst) in mv_map.items():
            shutil.move(self.work_dir + src, self.work_dir + dst)

        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        run_time = float(index_dict(self.work_dir)['params']['run_time'])
        return self.tmpl_out("result.html",
                             input=[self.work_url + 'input_0.png',
                                    self.work_url + 'input_1.png'],
                             disp=[self.work_url + 'disp1_H_input_0.png',
                                   self.work_url + 'disp3_H_input_0.png'],
                             rect=[self.work_url + 'H_input_0.png',
                                   self.work_url + 'H_input_1.png'],
                             orsa=self.work_url + 'orsa.txt',
                             homo=[self.work_url + 'H_input_0.txt',
                                   self.work_url + 'H_input_1.txt'],
                             exact=[self.work_url + 'disp1_H_input_0.tif',
                                    self.work_url + 'disp2_H_input_0.tif',
                                    self.work_url + 'disp3_H_input_0.tif'],
                             ply=self.work_url + 'disp3_H_input_0.ply',
                             run_time=run_time,
                             height=image(self.work_dir
                                          + 'input_0.png').size[1],
                             stdout=open(self.work_dir
                                         + 'stdout.txt', 'r').read())
