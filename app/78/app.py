"""
Stereo Disparity through Cost Aggregation with Guided Filter
"""

from lib import base_app, build, image, http
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
from math import floor, ceil
import os.path
from sys import float_info
import time
import shutil

#
# INTERACTION
#

class NoMatchError(RuntimeError):
    """ Exception raised when epipolar rectification fails """
    pass

class app(base_app):
    """ template demo app """
    
    title = "Stereo Disparity through Cost Aggregation with Guided Filter"

    input_nb = 2 # number of input images
    input_max_pixels = 512*512 # max size (in pixels) of an input image
    input_max_method = 'zoom'
    input_dtype = '3x8i' # input image expected data type    
    input_ext = '.png'   # input image expected extension (ie file format)    
    is_test = False      # switch to False for deployment

    xlink_article = 'http://www.ipol.im/pub/pre/78/'

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

    def _build_rectify(self):
        """
        build/update of rectify program
        """
                # store common file path in variables
        rectify_tgz_file = self.dl_dir + "MissStereo.tar.gz"
        rectify_tgz_url = "http://www.ipol.im/pub/pre/78/MissStereo.tar.gz"
        rectify_log_file = self.base_dir + "build_MissStereo.log"
        build_dir = (self.src_dir + os.path.join("MissStereo", "build")
                     + os.path.sep)
        src_bin = dict([(build_dir + os.path.join("bin", prog),
                         self.bin_dir + prog)
                        for prog in ["homography", "orsa", "rectify",
                                     "sift", "size", "showRect"]])
        src_bin[self.src_dir
                + os.path.join("MissStereo","scripts","Rectify.sh")] \
                               = os.path.join(self.bin_dir, "Rectify.sh")
        build.download(rectify_tgz_url, rectify_tgz_file)
        if all([(os.path.isfile(bin_file) and
                 ctime(rectify_tgz_file) < ctime(bin_file))
                for bin_file in src_bin.values()]):
            cherrypy.log("no rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(rectify_tgz_file, self.src_dir)
            # build the program
            os.mkdir(build_dir)
            build.run("cmake -D CMAKE_BUILD_TYPE:string=Release ../src",
                      stdout=rectify_log_file, cwd=build_dir)
            build.run("make -C %s homography orsa rectify showRect sift size"
                      % build_dir, stdout=rectify_log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for (src, dst) in src_bin.items():
                shutil.copy(src, dst)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)

    def build(self):
        """
        program build/update
        """
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        self._build_rectify()
        tgz_file = self.dl_dir + "CostVolumeFilter_1.0.tar.gz"
        # following line to be adapted for IPOL final demo
        tgz_url = "http://www.ipol.im/pub/pre/78/CostVolumeFilter_1.0.tar.gz"
        prog_file = self.bin_dir + "costVolumeFilter"
        log_file = self.base_dir + "build.log"
        # # get the latest source archive
        # uncomment next line for IPOL final demo
        build.download(tgz_url, tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("no rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build_dir = (self.src_dir + os.path.join("CostVolumeFilter_1.0",
                                                     "build") + os.path.sep)
            os.mkdir(build_dir)
            build.run("cmake -DCMAKE_BUILD_TYPE:string=Release ..",
                      stdout=log_file, cwd=build_dir)
            build.run("make -C %s -j4" % build_dir, stdout=log_file)
            # save into bin dir
            shutil.copy(build_dir + "costVolumeFilter", prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


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
            cp_list = ['H_input_0.png','H_input_1.png']
            for fname in cp_list:
                shutil.copy(old_work_dir + fname, self.work_dir + fname)
        if 'radius' not in self.cfg['param']:
            self.cfg['param']['radius'] = 9
            self.cfg['param']['alpha'] = 0.9
            self.cfg.save()
        if 'sense' not in self.cfg['param']:
            self.cfg['param']['sense'] = 'r'
        if (image(self.work_dir + 'input_0.png').size !=
            image(self.work_dir + 'input_1.png').size):
            return self.error('badparams',
                              "The images must have the same size")
        return self.tmpl_out("params.html")

    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        if 'sense' in kwargs:
            self.cfg['param']['sense'] = kwargs['sense']
            self.cfg.save()
        if 'norectif' in kwargs:
            self.cfg['param']['norectif'] = True
            self.cfg.save()
        try:
            if 'dmin' in kwargs: # Check integer values
                dmin = int(kwargs['dmin'])
                dmax = int(kwargs['dmax'])
                self.cfg['param']['dmin'] = dmin
                self.cfg['param']['dmax'] = dmax
                self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                     errmsg="The disparity range parameters must be integers.")

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
        success = True
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout)
            self.cfg['info']['run_time'] = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="Try again with simpler images.")
        except NoMatchError:
            success = False
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
            if success:
                ar.add_file("H_input_0.png", info="rectified #1")
                ar.add_file("H_input_1.png", info="rectified #2")
                ar.add_file("disparity.png", info="disparity")
                ar.add_file("disparity_occlusion.png",
                            info="disparity occlusion")
                ar.add_file("disparity_occlusion_filled.png",
                            info="disparity simple densified")
                ar.add_file("disparity_occlusion_filled_smoothed.png",
                            info="disparity densified")
                if 'norectif' in self.cfg['param']:
                    ar.add_info({"rectification": "disabled"})
                else:
                    f = open(self.work_dir + 'input_0.png_h.txt')
                    ar.add_info({"homography #1" : f.readline()})
                    f.close()
                    f = open(self.work_dir + 'input_1.png_h.txt')
                    ar.add_info({"homography #2" : f.readline()})
                    f.close()
                dmin = str(self.cfg['param']['dmin'])
                dmax = str(self.cfg['param']['dmax'])
                ar.add_info({"disparity range": dmin+","+dmax})
                radius = str(self.cfg['param']['radius'])
                alpha = str(self.cfg['param']['alpha'])
                ar.add_info({'radius':radius, 'alpha':alpha})
                if self.cfg['param']['sense'] == 'r':
                    sense = 'left to right'
                else:
                    sense = 'right to left'
                ar.add_info({'camera motion direction':sense})
            ar.save()

        return self.tmpl_out("run.html")

    def _rectify(self, stdout):
        """
        rectify input images
        """
        start_time = time.time()
        end_time = start_time + self.timeout/3
        (w,h) = image(self.work_dir+'input_0.png').size
        pairs = self.work_dir+'input_0.png_input_1.png_pairs.txt'
        pairs_good = self.work_dir+'input_0.png_input_1.png_pairs_orsa.txt'
        try:
            p = self.run_proc(['sift',
                               self.work_dir+'input_0.png',
                               self.work_dir+'input_1.png',
                               pairs],
                              stdout=stdout, stderr=stdout)
            self.wait_proc(p,timeout=end_time-start_time)
            start_time = time.time()
            p = self.run_proc(['orsa', str(w), str(h),
                               pairs, pairs_good, '500', '1', '0', '2', '0'],
                              stdout=stdout, stderr=stdout)
            self.wait_proc(p,timeout=end_time-start_time)
            start_time = time.time()
            outRect = open(self.work_dir+'rect.txt','w')
            p = self.run_proc(['rectify', pairs_good, str(w), str(h),
                               self.work_dir+'input_0.png_h.txt',
                               self.work_dir+'input_1.png_h.txt'],
                              stdout=outRect, stderr=outRect)
            self.wait_proc(p,timeout=end_time-start_time)
            start_time = time.time()
            p = []
            p.append(self.run_proc(['homography',
                                    self.work_dir+'input_0.png',
                                    self.work_dir+'input_0.png_h.txt',
                                    self.work_dir+'H_input_0.png'],
                                   stdout=outRect, stderr=outRect))
            p.append(self.run_proc(['homography',
                                    self.work_dir+'input_1.png',
                                    self.work_dir+'input_1.png_h.txt',
                                    self.work_dir+'H_input_1.png'],
                                   stdout=outRect, stderr=outRect))
            self.wait_proc(p,timeout=end_time-start_time)
        except RuntimeError:
            if 0 != p.returncode:
                stdout.close()
                raise NoMatchError
            else:
                raise
        outRect.close()
        outRect = open(self.work_dir+'rect.txt','r')
        lines = outRect.readlines()
        #print lines
        for line in lines:
            stdout.write(line)
            words = line.split()
            if words[0] == "Disparity:":
                dmin = words[1]
                dmax = words[2]
        outRect.close()
        stdout.flush()
        return (dmin, dmax)

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
        dmin = float_info.max
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
        return

    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        if 'norectif' in self.cfg['param']: # skip rectification
            if 'dmin' not in self.cfg['param']: # unknown disparity range
                start_time = time.time()
                (dmin, dmax) = self._disparity(timeout/10, stdout)
                timeout -= time.time() - start_time
                self.cfg['param']['dmin'] = int(floor(dmin))
                self.cfg['param']['dmax'] = int(ceil (dmax))
                self.cfg.save()
                # First run: copy original images as rectified ones
                shutil.copy(self.work_dir + 'input_0.png',
                            self.work_dir + 'H_input_0.png')
                shutil.copy(self.work_dir + 'input_1.png',
                            self.work_dir + 'H_input_1.png')
            dmin = self.cfg['param']['dmin']
            dmax = self.cfg['param']['dmax']
            self._trivial_h_files()
            stdout.write("Disparity: " + str(dmin) + ' ' + str(dmax))
        else:
            (dmin,dmax) = self._rectify(stdout)
            self.cfg['param']['dmin'] = dmin
            self.cfg['param']['dmax'] = dmax
            self.cfg.save()

        # Read disparity range from rectification output if necessary
        if 'dmin' not in self.cfg['param']:
            output = open(self.work_dir +
                          'input_0.png_input_1.png_disparity.txt', 'r')
            lines = output.readlines()
            for line in lines:
                words = line.split()
                if words[0] == "Disparity:":
                    self.cfg['param']['dmin'] = int(words[1])
                    self.cfg['param']['dmax'] = int(words[2])
                    self.cfg.save()
                    break
            output.close()

        p = self.run_proc(['costVolumeFilter',
                           '-O', self.cfg['param']['sense'],
                           '-R', str(self.cfg['param']['radius']),
                           '-A', str(self.cfg['param']['alpha']),
                           self.work_dir+'H_input_0.png',
                           self.work_dir+'H_input_1.png',
                           str(self.cfg['param']['dmin']),
                           str(self.cfg['param']['dmax'])],
                          stdout=stdout, stderr=stdout)
        self.wait_proc(p, timeout)
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
