"""
Computing Visual Correspondence with Occlusions using Graph Cuts demo
interaction script
"""

from lib import base_app, build, image, http
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import time
import shutil

#
# FRACTION UTILITY FUNCTIONS
#

def str2frac(qstr):
    """
    parse the string representation of a rational number
    """
    # handle simple integer cases
    if not '/' in qstr:
        qstr += "/1"
    # split the fraction
    (a, b) = [int(x) for x in qstr.split('/')][:2]
    return (a, b)

def frac2str(q):
    """
    represent a rational number as string
    """
    return "%i/%i" % q
#
# INTERACTION
#

class NoMatchError(RuntimeError):
    """ Exception raised when epipolar rectification fails """
    pass

class app(base_app):
    """ template demo app """
    
    title = "Computing Visual Correspondence with Occlusions using Graph Cuts"
    xlink_article = 'http://www.ipol.im/'

    input_nb = 2 # number of input images
    input_max_pixels = 1024*1024 # max size (in pixels) of an input image
    input_max_method = 'zoom'
    input_dtype = '3x8i' # input image expected data type    
    input_ext = '.ppm'   # input image expected extension (ie file format)    
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

    def __build_rectify(self):
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
                                     "sift", "size", "showRect",
                                     "convert"]])
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
            build.run("make -C %s -j4" % build_dir,
                      stdout=rectify_log_file)
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
        self.__build_rectify()
        match_tgz_file = self.dl_dir + "match.tar.gz"
        match_tgz_url = "https://edit.ipol.im/edit/algo/" \
            + "ltp_stereovision_with_graph_cuts/match.tar.gz"
        match_prog_file = self.bin_dir + "match"
        match_log_file = self.base_dir + "build_match.log"
        autok_tgz_file = self.dl_dir + "autoK.tar.gz"
        autok_tgz_url = "https://edit.ipol.im/edit/algo/" \
            + "ltp_stereovision_with_graph_cuts/autoK.tar.gz"
        autok_prog_file = self.bin_dir + "autoK"
        autok_log_file = self.base_dir + "build_autok.log"
        # get the latest source archive
        build.download(match_tgz_url, match_tgz_file)
        build.download(autok_tgz_url, autok_tgz_file)
        # MATCH
        # test if the dest file is missing, or too old
        if (os.path.isfile(match_prog_file)
            and ctime(match_tgz_file) < ctime(match_prog_file)):
            cherrypy.log("no rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(match_tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s ../bin/match"
                      % (self.src_dir + os.path.join("match-v3.3.src",
                                                     "unix")),
                      stdout=match_log_file)
            # save into bin dir
            shutil.copy(self.src_dir
                        + os.path.join("match-v3.3.src", "bin", "match"),
                        match_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        # AUTOK
        # test if the dest file is missing, or too old
        if (os.path.isfile(autok_prog_file)
            and ctime(autok_tgz_file) < ctime(autok_prog_file)):
            cherrypy.log("no rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(autok_tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s ../bin/autoK"
                      % (self.src_dir + os.path.join("autoK", "unix")),
                      stdout=autok_log_file)
            # save into bin dir
            shutil.copy(self.src_dir + os.path.join("autoK", "bin", "autoK"),
                        autok_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        try:
            if 'K' in kwargs:
                k_ = str2frac(kwargs['K'])
                k_prev = str2frac(self.cfg['param']['k'])
                self.cfg['param']['k'] = frac2str((k_[0]*k_prev[0],
                                                   k_[1]*k_prev[1]))
            if 'lambda' in kwargs:
                l_ = str2frac(kwargs['lambda'])
                l_prev = str2frac(self.cfg['param']['lambda'])
                self.cfg['param']['lambda'] = frac2str((l_prev[0]*l_[0],
                                                        l_prev[1]*l_[1]))
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
                ar.add_file("H_im0.png", info="rectified #1")
                ar.add_file("H_im1.png", info="rectified #2")
                ar.add_file("output.png", info="output")
                try:
                    ar.add_info({"k" : self.cfg['param']['k'],
                                 "lambda" : self.cfg['param']['lambda']})
                except KeyError:
                    pass
            ar.save()

        return self.tmpl_out("run.html")

    def __compute_k_auto(self, dmin, dmax):
        """
        compute default K and lambda values
        """
        # create autok.conf file
        kfile = open(self.work_dir + 'autok.conf', 'w')
        kfile.write("LOAD_COLOR input_0.ppm input_1.ppm\n")
        kfile.write("SET disp_range "+dmin+" 0 "+dmax+" 0\n")
        kfile.close()
        
        # run autok
        stdout = open(self.work_dir +'stdout.txt', 'w')
        p = self.run_proc(['autoK', 'autok.conf'],
                          stdout=stdout, stderr=stdout)
        self.wait_proc(p, timeout=self.timeout)
        stdout.close()
        
        # get k from stdout
        stdout = open(self.work_dir + 'stdout.txt', 'r')
        k_auto = str2frac(stdout.readline()) 
        lambda_auto = (k_auto[0], k_auto[1] * 5)
        stdout.close()
        return (k_auto, lambda_auto)

    def __rectify(self):
        """
        rectify input images
        """
        image(self.work_dir + 'input_0.ppm').save(self.work_dir + 'im0.png')
        image(self.work_dir + 'input_1.ppm').save(self.work_dir + 'im1.png')
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        p = self.run_proc(['Rectify.sh',
                           self.work_dir + 'im0.png',
                           self.work_dir + 'im1.png'],
                          stdout=stdout, stderr=stdout)
        try:
            self.wait_proc(p)
        except RuntimeError:
            if 0 != p.returncode:
                stdout.close()
                raise NoMatchError
            else:
                raise
        stdout.close()
        stdout = open(self.work_dir + 'im0.png_im1.png_disparity.txt', 'r')
        lines = stdout.readlines()
        for line in lines:
            words = line.split()
            if words[0] == "Disparity:":
                dmin = words[1]
                dmax = words[2]
        stdout.close()
        return (dmin, dmax)

    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        # use default or overrriden parameter values
        if not self.cfg['param'].has_key('k'):
            # First run: rectification
            (dmin, dmax) = self.__rectify()
            self.cfg['param']['dmin'] = dmin
            self.cfg['param']['dmax'] = dmax
            image(self.work_dir+'H_im0.png').save(self.work_dir+'input0_r.ppm')
            image(self.work_dir+'H_im1.png').save(self.work_dir+'input1_r.ppm')
            # get the default parameters
            (k, l) = self.__compute_k_auto(dmin, dmax)
            self.cfg['param']['k_auto'] = frac2str(k)
            self.cfg['param']['lambda_auto'] = frac2str(l)
            self.cfg['param']['k'] = self.cfg['param']['k_auto']
            self.cfg['param']['lambda'] = \
                self.cfg['param']['lambda_auto']
        k = self.cfg['param']['k']
        l = self.cfg['param']['lambda']
        dmin = self.cfg['param']['dmin']
        dmax = self.cfg['param']['dmax']
        # split the input images
        nproc = 6   # number of slices
        margin = 6  # overlap margin 

        input0_fnames = image(self.work_dir + 'input0_r.ppm') \
            .split(nproc, margin=margin,
                   fname=self.work_dir + 'input0_split.ppm')
        input1_fnames = image(self.work_dir + 'input1_r.ppm') \
            .split(nproc, margin=margin,
                   fname=self.work_dir + 'input1_split.ppm')
        output_fnames = ['output_split.__%0.2i__.png' % n
                         for n in range(nproc)]
        plist = []
        for n in range(nproc):
            # creating the conf files (one per process)
            fname = open(self.work_dir + 'match_%i.conf' % n,'w')
            fname.write("LOAD_COLOR %s %s\n"
                        % (input0_fnames[n], input1_fnames[n]))
            fname.write("SET disp_range "+str(dmin)+" 0 "+str(dmax)+" 0\n")
            fname.write("SET iter_max 30\n")
            fname.write("SET randomize_every_iteration\n")
            fname.write("SET k %s\n" % k)
            fname.write("SET lambda %s\n" % l)
            fname.write("KZ2\n")
            fname.write("SAVE_X_SCALED %s\n" % output_fnames[n])
            fname.close()
            # run each process
            plist.append(self.run_proc(['match', 'match_%i.conf' %n],
                                       ))
        self.wait_proc(plist, timeout)

        # join all the partial results into a global one
        output_img = image().join([image(self.work_dir + output_fnames[n])
                                   for n in range(nproc)], margin=margin)
        output_img.save(self.work_dir + 'output.ppm')
        output_img.save(self.work_dir + 'output.png')

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
                                              + 'input_0.png').size[1],
                                 k_prev=self.cfg['param']['k'],
                                 lambda_prev=self.cfg['param']['lambda'],
                                 k_proposed=[frac2str((1,2)),
                                             frac2str((2,3)),
                                             '1',
                                             frac2str((3,2)),
                                             '2'],
                                 l_proposed=[frac2str((1,2)),
                                             frac2str((2,3)),
                                             '1',
                                             frac2str((3,2)),
                                             '2'])
