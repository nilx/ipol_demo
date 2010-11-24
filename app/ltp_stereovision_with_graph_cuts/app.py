"""
Computing Visual Correspondence with Occlusions using Graph Cuts demo
interaction script
"""
# pylint: disable=C0103

from lib import base_app, build, image, http
from lib.misc import init_app, app_expose, ctime
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
    if 1 == q[1]:
        return "%i" % q[0]
    else:
        return "%i/%i" % q
#
# INTERACTION
#

class app(base_app):
    """ template demo app """
    
    title = "Computing Visual Correspondence with Occlusions using Graph Cuts"

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

    def build(self):
        """
        program build/update
        """
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        # store common file path in variables
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
            cherrypy.log("not rebuild needed",
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
            cherrypy.log("not rebuild needed",
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
                self.cfg['param']['k'] = frac2str(k_)
            if 'lambda' in kwargs:
                lambda_ = str2frac(kwargs['lambda'])
                self.cfg['param']['lambda'] = frac2str(lambda_)
            self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be rationals.")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html",
                             input=['input_0.png',
                                    'input_1.png'],
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
            ar.add_file("input_0.png")
            ar.add_file("input_1.png")
            ar.add_file("output.png")
            ar.add_info({"k" : self.cfg['param']['k'],
                         "lambda" : self.cfg['param']['lambda']})
            ar.commit()

        return self.tmpl_out("run.html")

    def _compute_k_auto(self):
        """
        compute default K and lambda values
        """
        # TODO: cleanup, refactor
        # create autok.conf file
        kfile = open(self.work_dir + 'autok.conf', 'w')
        kfile.write("LOAD_COLOR input_0.ppm input_1.ppm\n")
        kfile.write("SET disp_range -15 0 0 0\n")
        kfile.close()
        
        # run autok
        stdout = open(self.work_dir +'stdout.txt', 'w')
        p = self.run_proc(['autoK', 'autok.conf'],
                          stdout=stdout, stderr=stdout)
        self.wait_proc(p)
        stdout.close()
        
        # get k from stdout
        stdout = open(self.work_dir + 'stdout.txt', 'r')
        k_auto = str2frac(stdout.readline()) 
        lambda_auto = (k_auto[0], k_auto[1] * 5)
        stdout.close()
        return (k_auto, lambda_auto)

    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        # TODO: cleanup, refactor
        # get the default parameters
        (k_auto, lambda_auto) = self._compute_k_auto()
        self.cfg['param']['k_auto'] = frac2str(k_auto)
        self.cfg['param']['lambda_auto'] = frac2str(lambda_auto)
        # use default or overrriden parameter values
        if not self.cfg['param'].has_key('k'):
            self.cfg['param']['k'] = self.cfg['param']['k_auto']
            self.cfg['param']['lambda'] = \
                self.cfg['param']['lambda_auto']
        self.cfg.save()
        k = self.cfg['param']['k']
        l = self.cfg['param']['lambda']

        # split the input images
        nproc = 6   # number of slices
        margin = 6  # overlap margin 

        input0_fnames = image(self.work_dir + 'input_0.ppm') \
            .split(nproc, margin=margin,
                   fname=self.work_dir + 'input0_split.ppm')
        input1_fnames = image(self.work_dir + 'input_1.ppm') \
            .split(nproc, margin=margin,
                   fname=self.work_dir + 'input1_split.ppm')
        output_fnames = ['output_split.__%0.2i__.png' % n
                         for n in range(nproc)]
        plist = []
        for n in range(nproc):
            # creating the conf files (one per process)
            conf_file = open(self.work_dir + 'match_%i.conf' % n,'w')
            conf_file.write("LOAD_COLOR %s %s\n"
                            % (input0_fnames[n], input1_fnames[n]))
            conf_file.write("SET disp_range -15 0 0 0\n")
            conf_file.write("SET iter_max 30\n")
            conf_file.write("SET randomize_every_iteration\n")
            conf_file.write("SET k %s\n" % k)
            conf_file.write("SET lambda %s\n" % l)
            conf_file.write("KZ2\n")
            conf_file.write("SAVE_X_SCALED %s\n" % output_fnames[n])
            conf_file.close()
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
    def result(self):
        """
        display the algo results
        """
        k = str2frac(self.cfg['param']['k'])
        l = str2frac(self.cfg['param']['lambda'])

        return self.tmpl_out("result.html",
                             input=['input_0.png', 'input_1.png'],
                             output=['output.png'],
                             height=image(self.work_dir 
                                          + 'input_0.png').size[1],
                             k=self.cfg['param']['k'],
                             l=self.cfg['param']['lambda'],
                             k_proposed=[frac2str((k[0] * 1, k[1] * 2)),
                                         frac2str((k[0] * 2, k[1] * 3)),
                                         frac2str((k[0] * 1, k[1] * 1)),
                                         frac2str((k[0] * 3, k[1] * 2)),
                                         frac2str((k[0] * 2, k[1] * 1))],
                             l_proposed=[frac2str((l[0] * 1, l[1] * 2)),
                                         frac2str((l[0] * 2, l[1] * 3)),
                                         frac2str((l[0] * 1, l[1] * 1)),
                                         frac2str((l[0] * 3, l[1] * 2)),
                                         frac2str((l[0] * 2, l[1] * 1))])
