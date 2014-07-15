"""
Kolmogorov and Zabih's Graph Cuts Stereo Matching Algorithm
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
    title = "Kolmogorov and Zabih's Graph Cuts Stereo Matching Algorithm"

    input_nb = 2 # number of input images
    input_max_pixels = 512*512 # max size (in pixels) of an input image
    input_max_method = 'zoom'
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = False      # switch to False for deployment

    # To be changed when publishing
    # xlink_article = "http://www.ipol.im/pub/pre/97/"
    xlink_article = "http://imagine.enpc.fr/~monasse/"

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

        self.Kmax = 250
        self.Lmax = 50
        self.autoK = True
        self.autoL = True

    def _build_rectify(self):
        """
        build/update of rectify program
        """
        # store common file path in variables
        archive = "rectify-quasi-euclidean_20140626.tar.gz"
        rectify_tgz_url = self.xlink_article + archive
        rectify_tgz_file = self.dl_dir        + archive
        build.download(rectify_tgz_url, rectify_tgz_file)
        binary = self.bin_dir + "rectifyQuasiEuclidean"
        if os.path.isfile(binary) and ctime(rectify_tgz_file) < ctime(binary):
            cherrypy.log("no rebuild needed", context='BUILD', traceback=False)
            return
        # extract the archive
        build.extract(rectify_tgz_file, self.src_dir)
        # build the program
        build_dir = (self.src_dir +
                     os.path.join("rectify-quasi-euclidean_20140626", "build") +
                     os.path.sep)
        binary = build_dir + os.path.join("bin", "rectifyQuasiEuclidean")
        os.mkdir(build_dir)
        log_file = self.base_dir + "build_Rectify.log"
        build.run("cmake -D CMAKE_BUILD_TYPE:string=Release ../src",
                  stdout=log_file, cwd=build_dir)
        build.run("make -C " + build_dir, stdout=log_file)
        # save into bin dir
        if os.path.isdir(self.bin_dir):
            shutil.rmtree(self.bin_dir)
        os.mkdir(self.bin_dir)
        shutil.copy(binary, self.bin_dir)
        shutil.copy(build_dir + os.path.join("bin", "siftMatch"), self.bin_dir)
        shutil.copy(build_dir + os.path.join("bin", "warp"), self.bin_dir)
        # cleanup the source dir
        shutil.rmtree(self.src_dir)

    def build(self):
        """
        program build/update
        """
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        self._build_rectify()
        archive = "kz2_1.0.tar.gz"
        kz2_tgz_url = self.xlink_article + archive
        kz2_tgz_file = self.dl_dir        + archive
        binary = self.bin_dir + "KZ2"
        # get the latest source archive
        build.download(kz2_tgz_url, kz2_tgz_file)
        # test if the dest file is missing, or too old
        if os.path.isfile(binary) and ctime(kz2_tgz_file) < ctime(binary):
            cherrypy.log("no rebuild needed", context='BUILD', traceback=False)
            return
        # extract the archive
        build.extract(kz2_tgz_file, self.src_dir)
        build_dir = self.src_dir+os.path.join("kz2_1.0", "build")+os.path.sep
        os.mkdir(build_dir)
        log_file = self.base_dir + "build_KZ2.log"
        build.run("cmake -D CMAKE_BUILD_TYPE:string=Release ../src",
                  stdout=log_file, cwd=build_dir)
        build.run("make -j4 -C %s" % build_dir, stdout=log_file)
        # save into bin dir
        shutil.copy(build_dir + "KZ2", binary)
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
            cp_list = ['H_input_0.png', 'H_input_1.png']
            for fname in cp_list:
                shutil.copy(old_work_dir + fname, self.work_dir + fname)
        else:
            self.cfg['param']['k'] = 'auto'
            self.cfg['param']['lambda'] = 'auto'
        self.cfg['param']['rectif'] = False # No rectif a priori
        self.cfg.save()

        return self.tmpl_out("params.html", Kmax=self.Kmax, Lmax=self.Lmax)

    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        if 'rectif' in kwargs:
            self.cfg['param']['rectif'] = True
        if 'valK' in kwargs:
            self.autoK = False
            self.cfg['param']['k'] = \
                str(min(self.Kmax, float(kwargs['valK'])))
        if 'autoK' in kwargs and kwargs['autoK'] == 'True':
            self.autoK = True
            self.cfg['param']['k'] = 'auto'
        if 'valL' in kwargs:
            self.autoL = False
            self.cfg['param']['lambda'] = \
                str(min(self.Lmax, float(kwargs['valL'])))
        if 'autoL' in kwargs and kwargs['autoL'] == 'True':
            self.autoL = True
            self.cfg['param']['lambda'] = 'auto'
        if 'dmin' in kwargs: # Check integer values
            dmin = int(kwargs['dmin'])
            dmax = int(kwargs['dmax'])
            self.cfg['param']['dmin'] = dmin
            self.cfg['param']['dmax'] = dmax
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
            ark = self.make_archive()
            ark.add_file("input_0.orig.png", info="uploaded #1")
            ark.add_file("input_1.orig.png", info="uploaded #2")
            ark.add_file("input_0.png", info="input #1")
            ark.add_file("input_1.png", info="input #2")
            if success:
                if self.cfg['param']['rectif']:
                    ark.add_file("H_input_0.png", info="rectified #1")
                    ark.add_file("H_input_1.png", info="rectified #2")
                ark.add_file("disparity.png", info="disparity")
                ark.add_file("warp.png", info="warp")
                try:
                    ark.add_info({"k" : str(self.cfg['param']['k']),
                                  "lambda" : str(self.cfg['param']['lambda'])})
                    dmin = str(self.cfg['param']['dmin'])
                    dmax = str(self.cfg['param']['dmax'])
                    ark.add_info({"disparity range": dmin+","+dmax})
                except KeyError:
                    pass
            ark.save()

        return self.tmpl_out("run.html")

    def _compute_auto(self, timeout, stdout, dmin, dmax):
        """
        compute default K and lambda values
        """
        cmd = ['KZ2', 'H_input_0.png', 'H_input_1.png', str(dmin), str(dmax)]
        if self.cfg['param']['k'] != 'auto':
            cmd.append('-k')
            cmd.append(str(self.cfg['param']['k']))
        if self.cfg['param']['lambda'] != 'auto':
            cmd.append('-l')
            cmd.append(str(self.cfg['param']['lambda']))
        # run without output file to compute parameters automatically
        name = self.work_dir + 'outk.txt'
        outk = open(name, 'w')
        proc = self.run_proc(cmd, stdout=outk, stderr=outk)
        try:
            self.wait_proc(proc, timeout=timeout)
        except RuntimeError:
            outk.close()
            raise
        outk.close()
        # get k and lambda from file outk
        outk = open(name, 'r')
        lines = outk.readlines()
        for line in lines:
            stdout.write(line)
            words = line.split('=')
            if len(words) == 2:
                if words[0].endswith('K'):
                    k_auto = words[1].strip()
                if words[0].endswith('lambda'):
                    lambda_auto = words[1].strip()
        outk.close()
        os.unlink(name)
        stdout.flush()
        return (k_auto, lambda_auto)

    def _rectify(self, stdout):
        """
        rectify input images
        """
        start_time = time.time()
        end_time = start_time + self.timeout
        try:
            out_rect = open(self.work_dir+'rect.txt', 'w')
            proc = self.run_proc(['rectifyQuasiEuclidean',
                                  self.work_dir+'input_0.png',
                                  self.work_dir+'input_1.png',
                                  self.work_dir+'H_input_0.png',
                                  self.work_dir+'H_input_1.png'],
                                 stdout=out_rect, stderr=out_rect)
            self.wait_proc(proc, timeout=end_time-start_time)
            out_rect.close()
        except RuntimeError:
            if 0 != proc.returncode:
                stdout.close()
                raise NoMatchError
            else:
                raise
        out_rect = open(self.work_dir+'rect.txt', 'r')
        lines = out_rect.readlines()
        for line in lines:
            stdout.write(line)
            words = line.split()
            if words[0] == "Disparity:":
                dmin = words[1]
                dmax = words[2]
        out_rect.close()
        stdout.flush()
        return (dmin, dmax)

    def _disparity(self, timeout=None, stdout=None):
        """
        Compute disparity range without rectification
        """
        proc = self.run_proc(['siftMatch',
                              self.work_dir + 'input_0.png',
                              self.work_dir + 'input_1.png',
                              self.work_dir + 'sift.txt'],
                             stdout=stdout, stderr=stdout)
        try:
            self.wait_proc(proc, timeout)
        except RuntimeError:
            if 0 != proc.returncode:
                raise NoMatchError
            else:
                raise
        match = open(self.work_dir + 'sift.txt', 'r')
        lines = match.readlines()
        out = []
        dmin = float_info.max
        dmax = -dmin
        for line in lines:
            val = line.split()
            diffy = float(val[3])-float(val[1])
            if -1.0 <= diffy <= 1.0:
                out.append(line)
                diffx = float(val[2])-float(val[0])
                dmin, dmax = min(dmin, diffx), max(dmax, diffx)
        match.close()
        if not out:
            raise NoMatchError
        return (dmin, dmax)

    def _bound_disparity(self, timeout, stdout):
        """
        Fill self.cfg['param']['dmin'] and self.cfg['param']['dmax']
        """
        if self.cfg['param']['rectif']:
            (dmin, dmax) = self._rectify(stdout)
            self.cfg['param']['dmin'] = dmin
            self.cfg['param']['dmax'] = dmax
            self.cfg.save()
        else: # skip rectification
            if 'dmin' not in self.cfg['param']: # unknown disparity range
                (dmin, dmax) = self._disparity(timeout, stdout)
                self.cfg['param']['dmin'] = int(floor(dmin))
                self.cfg['param']['dmax'] = int(ceil(dmax))
                self.cfg.save()
                # First run: copy original images as rectified ones
                shutil.copy(self.work_dir + 'input_0.png',
                            self.work_dir + 'H_input_0.png')
                shutil.copy(self.work_dir + 'input_1.png',
                            self.work_dir + 'H_input_1.png')
            dmin = self.cfg['param']['dmin']
            dmax = self.cfg['param']['dmax']
            stdout.write("Disparity: " + str(dmin) + ' ' + str(dmax) + '\n')

        # use default or overrriden parameter values
        if self.cfg['param']['k'] == 'auto' or\
                self.cfg['param']['lambda'] == 'auto':
            (paramk, paraml) = self._compute_auto(timeout, stdout, dmin, dmax)
            if self.cfg['param']['k'] == 'auto':
                self.cfg['param']['k'] = paramk
            if self.cfg['param']['lambda'] == 'auto':
                self.cfg['param']['lambda'] = paraml
            self.cfg.save()

    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        start_time = time.time()
        self._bound_disparity(timeout, stdout)
        timeout -= time.time() - start_time

        # split the input images
        nproc = 6   # number of slices
        margin = 6  # overlap margin

        fname = self.work_dir + 'input0_split.png', \
                self.work_dir + 'input1_split.png'
        input_fnames = image(self.work_dir + 'H_input_0.png') \
                       .split(nproc, margin=margin, fname=fname[0]), \
                       image(self.work_dir + 'H_input_1.png') \
                       .split(nproc, margin=margin, fname=fname[1])
        output_fnames = [('output_split.__%0.2i__.png' % n,
                          'output_split.__%0.2i__.tif' % n,
                          'warp_split.__%0.2i__.png'   % n)
                         for n in range(nproc)]
        plist = []
        loglist = []
        floglist = []
        for num in range(nproc):
            cmd = ['KZ2',
                   '-o', output_fnames[num][0],
                   '-k', str(self.cfg['param']['k']),
                   '-l', str(self.cfg['param']['lambda']),
                   input_fnames[0][num], input_fnames[1][num],
                   str(self.cfg['param']['dmin']),
                   str(self.cfg['param']['dmax']),
                   output_fnames[num][1]]
            loglist.append(self.work_dir + 'out_%i.txt' % num)
            fname = open(loglist[-1], 'w')
            floglist.append(fname)
            plist.append(self.run_proc(cmd, stdout=fname, stderr=fname))
        start_time = time.time()
        self.wait_proc(plist, timeout)
        timeout -= time.time() - start_time

        # join all the partial results into a global one
        image().join([image(self.work_dir + output_fnames[n][0])
                      for n in range(nproc)], margin=margin) \
               .save(self.work_dir + 'disparity.png')

        # warp all partial images with disparity map
        plist = []
        for num in range(nproc):
            cmd = ['warp', output_fnames[num][1], input_fnames[1][num],
                   output_fnames[num][2]]
            plist.append(self.run_proc(cmd, stdout=fname, stderr=fname))
        self.wait_proc(plist, timeout)

        image().join([image(self.work_dir + output_fnames[n][2])
                      for n in range(nproc)], margin=margin) \
               .save(self.work_dir + 'warp.png')

        for num in range(nproc): # concatenate output logs
            floglist[num].close()
            fname = open(loglist[num], 'r')
            stdout.write(fname.read())
            fname.close()
            os.unlink(loglist[num])

        # delete the strips
        for fname in input_fnames[0] + input_fnames[1]:
            os.unlink(fname)
        for fname in output_fnames:
            os.unlink(self.work_dir + fname[0])
            os.unlink(self.work_dir + fname[1])
            os.unlink(self.work_dir + fname[2])
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
