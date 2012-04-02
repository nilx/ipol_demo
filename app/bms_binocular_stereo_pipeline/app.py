"""
Binocular Stereo Pipeline
"""

from lib import base_app, image, build, http
from lib.misc import app_expose, ctime, gzip
from lib.base_app import init_app
from cherrypy import TimeoutError
import os.path
import time
import cherrypy
import shutil
import sys
from math import floor, ceil

#
# INTERACTION
#

class NoMatchError(RuntimeError):
    """ Exception raised when epipolar rectification fails """
    pass

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
                  "bms_binocular_stereo_pipeline/MissStereo.tar.gz"
        build_dir = (self.src_dir + os.path.join("MissStereo", "build")
                     + os.path.sep)
        src_bin = dict([(build_dir + os.path.join("bin", prog),
                         self.bin_dir + prog)
                        for prog in ["homography", "orsa", "rectify",
                                     "sift", "size", "stereoAC",
                                     "selfSimilar", "subPixel", "medianFill",
                                     "convert", "mesh", "density"]])
        path = os.path.join("MissStereo", "scripts", "MissStereo.sh")
        src_bin[self.src_dir+path] = os.path.join(self.bin_dir, "MissStereo.sh")
        path = os.path.join("MissStereo", "scripts", "Disparity.sh")
        src_bin[self.src_dir+path] = os.path.join(self.bin_dir, "Disparity.sh")
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if any of the dest files is missing, or too old
        if all([(os.path.isfile(bin_file) and ctime(tgz_file) < ctime(bin_file))
                for bin_file in src_bin.values()]):
            cherrypy.log("no rebuild needed",
                         context='BUILD', traceback=False)
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
            old_work_dir = self.work_dir
            old_cfg_param = self.cfg['param']
            self.clone_input()
            self.cfg['param'].update(old_cfg_param)
            self.cfg['param']['norectif'] = True # No rectif for new run
            self.cfg.save()
            cp_list = ['input_0.png_input_1.png_pairs_orsa.txt',
                       'input_0.png_h.txt',
                       'input_1.png_h.txt',
                       'H_input_0.png',
                       'H_input_1.png',
                       'H_input_0_float.tif',
                       'H_input_1_float.tif']
            for fname in cp_list:
                try:
                    shutil.copy(old_work_dir + fname, self.work_dir + fname)
                except IOError:
                    pass
        if (image(self.work_dir + 'input_0.png').size
            != image(self.work_dir + 'input_1.png').size):
            return self.error('badparams',
                              "The images must have the same size")
        return self.tmpl_out("params.html")

    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        if 'norectif' in kwargs:
            self.cfg['param']['norectif'] = True
            self.cfg.save()
        if 'percent' in kwargs:
            dmin = int(self.cfg['param']['disp_min_base'])
            dmax = int(self.cfg['param']['disp_max_base'])
            percent = int(kwargs['percent'])
            inc = int(ceil((dmax-dmin)*(int(percent)-100)/100.0/2.0))
            dmin -= inc
            dmax += inc
            if 0 == percent:
                dmax = image(self.work_dir + 'input_0.png').size[0]
                dmin = -dmax
            self.cfg['param']['disp_min'] = str(dmin)
            self.cfg['param']['disp_max'] = str(dmax)
            self.cfg.save()
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html",
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
            self.cfg['info']['run_time'] = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="Try again with simpler images.")
        except NoMatchError:
            http.redir_303(self.base_url +
                           'result?key=%s&error_nomatch=1' % self.key)
        except RuntimeError:
            return self.error(errcode='runtime')
        else:
            http.redir_303(self.base_url + 'result?key=%s' % self.key)

            # archive
            if self.cfg['meta']['original']:
                ar = self.make_archive()
                ar.add_file("input_0.orig.png", info="uploaded #1")
                ar.add_file("input_1.orig.png", info="uploaded #2")
                ar.add_file("input_0.png", info="input #1")
                ar.add_file("input_1.png", info="input #2")
                ar.add_file("rect_0.png", info="rectified #1")
                ar.add_file("rect_1.png", info="rectified #2")
                ar.add_file("disp1_0.png", info="AC pixel disparity")
                ar.add_file("disp2_0.png", info="self-sim. filter disp.")
                ar.add_file("disp3_0.png", info="sub-pixel disparity")
                ar.add_file("disp4_0.png", info="denser disparity")
                f = open(self.work_dir + 'homo_0.txt')
                ar.add_info({"homography #1" : f.readline()})
                f.close()
                f = open(self.work_dir + 'homo_1.txt')
                ar.add_info({"homography #2" : f.readline()})
                f.close()
                ar.add_file("orsa.txt.gz")
                ar.add_file("disp4_0.ply.gz")
                if 'norectif' in self.cfg['param']:
                    ar.add_info({"rectification": "disabled"})
                dmin = str(self.cfg['param']['disp_min_base'])
                dmax = str(self.cfg['param']['disp_max_base'])
                ar.add_info({"disparity range base": dmin+","+dmax})
                dmin = str(self.cfg['param']['disp_min'])
                dmax = str(self.cfg['param']['disp_max'])
                ar.add_info({"disparity range": dmin+","+dmax})
                ar.save()

        return self.tmpl_out("run.html")


    def _disparity(self, timeout=None, stdout=None):
        """
        Compute disparity range without rectification
        """
        p = self.run_proc(['sift',
                           self.work_dir + 'input_0.png',
                           self.work_dir + 'input_1.png',
                           self.work_dir + 'sift.txt'],
                          stdout=stdout, stderr=stdout)
        try:
            self.wait_proc(p, timeout)
        except RuntimeError:
            if 0 != p.returncode:
                raise NoMatchError
            else:
                raise
        match = open(self.work_dir + 'sift.txt', 'r')
        lines = match.readlines()
        out = []
        dmin = sys.float_info.max
        dmax = -dmin
        for m in lines:
            val = m.split()
            dy = float(val[3])-float(val[1])
            if -1.0 <= dy <= 1.0:
                out.append(m)
                dx = float(val[2])-float(val[0])
                dmin, dmax = min(dmin, dx), max(dmax, dx)
        match.close()
        if not out:
            raise NoMatchError
        orsa = open(self.work_dir + 'input_0.png_input_1.png_pairs_orsa.txt',
                    'w')
        orsa.writelines(out)
        orsa.close()
        return (dmin, dmax)

    def _trivial_h_files(self):
        """
        Write trivial homography in files (useful when skipping rectification)
        """
        file_h = open(self.work_dir + 'input_0.png_h.txt','w')
        file_h.write("[1 0 0; 0 1 0; 0 0 1]")
        file_h.close()
        shutil.copy(self.work_dir + 'input_0.png_h.txt',
                    self.work_dir + 'input_1.png_h.txt')

    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        if 'norectif' in self.cfg['param']: # skip rectification
            if 'disp_min' not in self.cfg['param']: # unknown disparity range
                start_time = time.time()
                (dmin, dmax) = self._disparity(timeout/10, stdout)
                timeout -= time.time() - start_time
                self.cfg['param']['disp_min'] = str(int(floor(dmin)))
                self.cfg['param']['disp_max'] = str(int(ceil (dmax)))
                self.cfg.save()
                # First run: copy original images as rectified ones
                shutil.copy(self.work_dir + 'input_0.png',
                            self.work_dir + 'H_input_0.png')
                shutil.copy(self.work_dir + 'input_1.png',
                            self.work_dir + 'H_input_1.png')
            dmin = str(self.cfg['param']['disp_min'])
            dmax = str(self.cfg['param']['disp_max'])
            self._trivial_h_files()
            stdout.write("Disparity: " + dmin + ' ' + dmax)
            hin0 = self.work_dir + 'H_input_0.png'
            hin1 = self.work_dir + 'H_input_1.png'
            if (os.path.isfile(self.work_dir + 'H_input_0_float.tif') and
                os.path.isfile(self.work_dir + 'H_input_1_float.tif')):
               hin0 = self.work_dir + 'H_input_0_float.tif'
               hin1 = self.work_dir + 'H_input_1_float.tif'
            p = self.run_proc(['Disparity.sh',
                               hin0, hin1,
                               dmin, dmax,
                               self.work_dir + 'H_input_0.png'],
                              stdout=stdout, stderr=stdout)
        else: # full pipeline
            p = self.run_proc(['MissStereo.sh',
                               self.work_dir + 'input_0.png',
                               self.work_dir + 'input_1.png'],
                              stdout=stdout, stderr=stdout)
        try:
            self.wait_proc(p, timeout)
        except RuntimeError:
            if 0 != p.returncode:
                stdout.close()
                raise NoMatchError
            else:
                raise
        stdout.close()

        # Read disparity range from rectification output if necessary
        if 'disp_min' not in self.cfg['param']:
            output = open(self.work_dir +
                          'input_0_input_1_disparity.txt', 'r')
            lines = output.readlines()
            for line in lines:
                words = line.split()
                if words[0] == "Disparity:":
                    self.cfg['param']['disp_min'] = words[1]
                    self.cfg['param']['disp_max'] = words[2]
                    self.cfg.save()
                    break
            output.close()

        if 'disp_min_base' not in self.cfg['param']:
            self.cfg['param']['disp_min_base'] = self.cfg['param']['disp_min']
            self.cfg['param']['disp_max_base'] = self.cfg['param']['disp_max']

        mv_map = {'disp1_H_input_0.png' : 'disp1_0.png',
                  'disp2_H_input_0.png' : 'disp2_0.png',
                  'disp3_H_input_0.png' : 'disp3_0.png',
                  'disp4_H_input_0.png' : 'disp4_0.png',
                  'disp1_H_input_0_float.tif' : 'disp1_0.tif',
                  'disp2_H_input_0_float.tif' : 'disp2_0.tif',
                  'disp3_H_input_0_float.tif' : 'disp3_0.tif',
                  'disp4_H_input_0_float.tif' : 'disp4_0.tif',
                  'disp4_H_input_0.ply' : 'disp4_0.ply'}
        cp_map = {'input_0.png_input_1.png_pairs_orsa.txt' : 'orsa.txt',
                  'input_0.png_h.txt' : 'homo_0.txt',
                  'input_1.png_h.txt' : 'homo_1.txt',
                  'H_input_0.png' : 'rect_0.png',
                  'H_input_1.png' : 'rect_1.png'}
        for (src, dst) in mv_map.items():
            shutil.move(self.work_dir + src, self.work_dir + dst)
        for (src, dst) in cp_map.items():
            shutil.copy(self.work_dir + src, self.work_dir + dst)
        gzip(self.work_dir + 'orsa.txt')
        gzip(self.work_dir + 'disp4_0.ply')

        return

    @cherrypy.expose
    @init_app
    def result(self, error_nomatch=None):
        """
        display the algo results
        """
        if error_nomatch:
            return self.tmpl_out("result_nomatch.html")
        else:
            return self.tmpl_out("result.html",
                                 height=image(self.work_dir
                                              + 'input_0.png').size[1])
