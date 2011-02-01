"""
simplest color balance ipol demo web app
"""
# pylint: disable=C0103

from lib import base_app, build, http, image
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time

class app(base_app):
    """ simplest color balance app """

    title = "Simplest Color Balance"

    input_nb = 1
    input_max_pixels = 700 * 700 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = False

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() and input_xxx() are generic
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True

    def build(self):
        """
        program build/update
        """
        # store common file path in variables
        tgz_url = "https://edit.ipol.im/pub/algo/" \
            + "lmps_simplest_color_balance/simplest_color_balanceB.tar.gz"
        tgz_file = self.dl_dir + "simplest_color_balanceB.tar.gz"
        progs = ["normalize_histo", "normalize_sort"]
        src_bin = dict([(self.src_dir + os.path.join("simplest_color_balanceB", prog),
                         self.bin_dir + prog)
                        for prog in progs])
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if any dest file is missing, or too old
        if all([(os.path.isfile(bin_file)
                 and ctime(tgz_file) < ctime(bin_file))
                for bin_file in src_bin.values()]):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the programs
            build.run("make -j4 -C %s %s"
                      % (self.src_dir + "simplest_color_balanceB", " ".join(progs)),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for (src, dst) in src_bin.items():
		#print "copy %s to %s" % (src, dst) 
                shutil.copy(src, dst)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


    #
    # PARAMETER HANDLING
    #


    @cherrypy.expose
    @init_app
    def wait(self, s="3.0"):
        """
        params handling and run redirection
        """
        # save and validate the parameters
	if (float(s) < 0) or (float(s) > 100.0) :
	  return self.error(errcode='badparams',
                              errmsg="s must be a value between 0.0 and 100.0")
        try:
            self.cfg['param'] = {'s' : float(s)}
            self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        # read the parameters
        s = self.cfg['param']['s']
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(s, stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="uploaded image")
            ar.add_file("input_0.png", info="original image")
            ar.add_file("output_1.png", info="result image 1 (RGB)")
            ar.add_file("output_2.png", info="result image 2 (I)")
            ar.add_info({"s": s})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, s, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        p = self.run_proc(['normalize_histo', str(s), 'input_0.png',
                            'output_1.png', 'output_2.png'],
                           stdout=None, stderr=None)
        self.wait_proc(p, timeout)


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        # read the parameters
        s = self.cfg['param']['s']
        return self.tmpl_out("result.html", s=s,
                             sizeY="%i" % image(self.work_dir 
                                                + 'input_0.png').size[1])



