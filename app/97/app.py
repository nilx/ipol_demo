"""
Computing Visual Correspondence with Occlusions using Graph Cuts
"""

from lib import base_app, build, image, http
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
from math import floor, ceil
from fractions import Fraction
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
    
    title = "Computing Visual Correspondence with Occlusions using Graph Cuts"

    input_nb = 2 # number of input images
    input_max_pixels = 512*512 # max size (in pixels) of an input image
    input_max_method = 'zoom'
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
        rectify_tgz_url = "http://www.ipol.im/pub/algo/" + \
            "m_quasi_euclidean_epipolar_rectification/MissStereo.tar.gz"
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
            return
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
        KZ2_tgz_file = self.dl_dir + "KZ2.tar.gz"
        #*************To be corrected later************
        KZ2_tgz_url = "https://edit.ipol.im/edit/algo/" \
            + "ltp_stereovision_with_graph_cuts/KZ2.tar.gz"
        KZ2_prog_file = self.bin_dir + "KZ2"
        KZ2_log_file = self.base_dir + "build_KZ2.log"
        # get the latest source archive
        build.download(KZ2_tgz_url, KZ2_tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(KZ2_prog_file)
            and ctime(KZ2_tgz_file) < ctime(KZ2_prog_file)):
            cherrypy.log("no rebuild needed",
                         context='BUILD', traceback=False)
            return
        # extract the archive
        build.extract(KZ2_tgz_file, self.src_dir)
        build_dir = (self.src_dir + os.path.join("KZ2", "build")
                     + os.path.sep)
        os.mkdir(build_dir)
        # build the program
        build.run("cmake -D CMAKE_BUILD_TYPE:string=Release ../src",
                  stdout=KZ2_log_file, cwd=build_dir)
        build.run("make -j4 -C %s" % build_dir,
                  stdout=KZ2_log_file)
        # save into bin dir
        shutil.copy(build_dir + "KZ2", KZ2_prog_file)
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
            cp_list = ['H_input_0.png','H_input_1.png']
            for fname in cp_list:
                shutil.copy(old_work_dir + fname, self.work_dir + fname)
        else:
            self.cfg['param']['k'] = 'auto'
            self.cfg['param']['lambda'] = 'auto'
        self.cfg.save()

        proposed = ['1/2', '2/3', '1', '3/2', '2', 'auto']
        return self.tmpl_out("params.html",
                             k_proposed=proposed, l_proposed=proposed)

    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        try:
            if 'norectif' in kwargs:
                self.cfg['param']['norectif'] = True
                self.cfg.save()
            if 'K' in kwargs:
                if kwargs['K'] == 'auto':
                    self.cfg['param']['k'] = 'auto'
                else:
                    m = Fraction(kwargs['K'])
                    k = Fraction(self.cfg['param']['k'])
                    self.cfg['param']['k'] = str(m*k)
                self.cfg.save()
            if 'lambda' in kwargs:
                if kwargs['lambda'] == 'auto':
                    self.cfg['param']['lambda'] = 'auto'
                else:
                    m = Fraction(kwargs['lambda'])
                    l = Fraction(self.cfg['param']['lambda'])
                    self.cfg['param']['lambda'] = str(m*l)
                self.cfg.save()
            if 'dmin' in kwargs: # Check integer values
                dmin = int(kwargs['dmin'])
                dmax = int(kwargs['dmax'])
                self.cfg['param']['dmin'] = dmin
                self.cfg['param']['dmax'] = dmax
                self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be rationals.")

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
                try:
                    ar.add_info({"k" : str(self.cfg['param']['k']),
                                 "lambda" : str(self.cfg['param']['lambda'])})
                    dmin = str(self.cfg['param']['dmin'])
                    dmax = str(self.cfg['param']['dmax'])
                    ar.add_info({"disparity range": dmin+","+dmax})
                except KeyError:
                    pass
            ar.save()

        return self.tmpl_out("run.html")

    def _compute_auto(self, timeout, stdout, dmin, dmax):
        """
        compute default K and lambda values
        """
        # run without output file to compute parameters automatically
        name = self.work_dir + 'outk.txt'
        outk = open(name, 'w')
        p = self.run_proc(['KZ2', 'H_input_0.png', 'H_input_1.png',
                           str(dmin), str(dmax)],
                          stdout=outk, stderr=outk)
        try:
            self.wait_proc(p, timeout=timeout)
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
            if len(words)==2:
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
        end_time = start_time + self.timeout/3
        (w, h) = image(self.work_dir+'input_0.png').size
        pairs = self.work_dir+'input_0.png_input_1.png_pairs.txt'
        pairs_good = self.work_dir+'input_0.png_input_1.png_pairs_orsa.txt'
        try:
            p = self.run_proc(['sift',
                               self.work_dir+'input_0.png',
                               self.work_dir+'input_1.png',
                               pairs],
                              stdout=stdout, stderr=stdout)
            self.wait_proc(p, timeout=end_time-start_time)
            start_time = time.time()
            p = self.run_proc(['orsa', str(w), str(h),
                               pairs, pairs_good, '500', '1', '0', '2', '0'],
                              stdout=stdout, stderr=stdout)
            self.wait_proc(p, timeout=end_time-start_time)
            start_time = time.time()
            outRect = open(self.work_dir+'rect.txt','w')
            p = self.run_proc(['rectify', pairs_good, str(w), str(h),
                               self.work_dir+'input_0.png_h.txt',
                               self.work_dir+'input_1.png_h.txt'],
                              stdout=outRect, stderr=outRect)
            self.wait_proc(p, timeout=end_time-start_time)
            start_time = time.time()
            p = []
            p.append(self.run_proc(['homography', '-f',
                                    self.work_dir+'input_0.png',
                                    self.work_dir+'input_0.png_h.txt',
                                    self.work_dir+'H_input_0.png'],
                                   stdout=outRect, stderr=outRect))
            p.append(self.run_proc(['homography', '-f',
                                    self.work_dir+'input_1.png',
                                    self.work_dir+'input_1.png_h.txt',
                                    self.work_dir+'H_input_1.png'],
                                   stdout=outRect, stderr=outRect))
            self.wait_proc(p, timeout=end_time-start_time)
        except RuntimeError:
            if 0 != p.returncode:
                stdout.close()
                raise NoMatchError
            else:
                raise
        outRect.close()
        outRect = open(self.work_dir+'rect.txt','r')
        lines = outRect.readlines()
        for line in lines:
            stdout.write(line)
            words = line.split()
            if words[0] == "Disparity:":
                dmin = words[1]
                dmax = words[2]
        outRect.close()
        os.unlink(self.work_dir+'rect.txt')
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
        name = self.work_dir + 'input_0.png_input_1.png_pairs_orsa.txt'
        with open(name,'w') as orsa:
            orsa.writelines(out)
        return (dmin, dmax)

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
            stdout.write("Disparity: " + str(dmin) + ' ' + str(dmax) + '\n')
        else:
            (dmin, dmax) = self._rectify(stdout)
            self.cfg['param']['dmin'] = dmin
            self.cfg['param']['dmax'] = dmax
            self.cfg.save()

        # use default or overrriden parameter values
        if (self.cfg['param']['k'] == 'auto'
            or self.cfg['param']['lambda'] == 'auto'):
            start_time = time.time()
            (k, l) = self._compute_auto(timeout/10, stdout, dmin, dmax)
            timeout -= time.time() - start_time
            if self.cfg['param']['k'] == 'auto':
                self.cfg['param']['k'] = k
            if self.cfg['param']['lambda'] == 'auto':
                self.cfg['param']['lambda'] = l
            self.cfg.save()
        dmin = self.cfg['param']['dmin']
        dmax = self.cfg['param']['dmax']
        # split the input images
        nproc = 6   # number of slices
        margin = 6  # overlap margin 

        input0_fnames = image(self.work_dir + 'H_input_0.png') \
            .split(nproc, margin=margin,
                   fname=self.work_dir + 'input0_split.png')
        input1_fnames = image(self.work_dir + 'H_input_1.png') \
            .split(nproc, margin=margin,
                   fname=self.work_dir + 'input1_split.png')
        output_fnames = ['output_split.__%0.2i__.png' % n
                         for n in range(nproc)]
        plist = []
        loglist = []
        floglist = []
        for n in range(nproc):
            cmd = ['KZ2',
                   '-o', output_fnames[n],
                   '-k', str(self.cfg['param']['k']),
                   '-l', str(self.cfg['param']['lambda']),
                   input0_fnames[n], input1_fnames[n],
                   str(dmin), str(dmax)]
            print cmd
            loglist.append(self.work_dir + 'out_%i.txt' % n)
            f = open(loglist[-1],'w')
            floglist.append(f)
            plist.append(self.run_proc(cmd, stdout=f, stderr=f))
        self.wait_proc(plist, timeout)

        # join all the partial results into a global one
        output_img = image().join([image(self.work_dir + output_fnames[n])
                                   for n in range(nproc)], margin=margin)
        output_img.save(self.work_dir + 'disparity.png')
        for n in range(nproc): # concatenate output logs
            floglist[n].close()
            f = open(loglist[n], 'r')
            stdout.write(f.read())
            f.close()
            os.unlink(loglist[n])

        # delete the strips
        for fname in input0_fnames + input1_fnames:
            os.unlink(fname)
        for fname in output_fnames:
            os.unlink(self.work_dir + fname)
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
