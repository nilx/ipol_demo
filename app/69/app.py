"""
SURF demo interaction script
"""

from lib import base_app, image, build, http
from lib.misc import ctime
from lib.base_app import init_app
from lib.config import cfg_open
from cherrypy import TimeoutError
import cherrypy
import os.path
import time
import shutil

class app(base_app):
    """ demo app """
    
    title = "SURF : Speeded Up Robust Features"

    input_nb = 2
    input_max_pixels = None
    input_max_method = 'zoom'
    input_dtype = '3x8i'
    input_ext = '.png'
    is_test = False
    default_param = {
        'orsa' : '0',
        'action' : 'launch surf'}
    xlink_article = "http://www.ipol.im/pub/pre/69/"

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() is input_max_pixelsgeneric
        #app_expose(base_app.index)
        #app_expose(base_app.input_select)
        #app_expose(base_app.input_upload)
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True



#
# PARAMETER HANDLING
#

    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None):
        """
            Configure the algo execution
        """
        if newrun:
            old_work_dir = self.work_dir
            self.clone_input()
            # Keep old parameters
            self.cfg['param'] = cfg_open(old_work_dir
                                     + 'index.cfg', 'rb')['param']
    # Also need to clone input_0_sel.png in case the user is running
    # with new parameters but on the same subimage.

    # Set undefined parameters to default values
        self.cfg['param'] = dict(self.default_param, **self.cfg['param'])
    # Generate a new timestamp
        self.timestamp = int(100*time.time())
    
        return self.tmpl_out('params.html')








    def build(self):
        """
        program build/update
        """
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        # store common file path in variables
        surf_zip_file = self.dl_dir + "demo_SURF_src.zip"
        surf_zip_url = "http://www.ipol.im/pub/pre/69/demo_SURF_src.zip"
        surf_prog_file = self.bin_dir + "surf"
        surf_log_file = self.base_dir + "build_surf.log"
        # get the latest source archive
        build.download(surf_zip_url, surf_zip_file)
        # SURF
        # test if the dest file is missing, or too old
        if (os.path.isfile(surf_prog_file)
            and ctime(surf_zip_file) < ctime(surf_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(surf_zip_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s" %
                      (self.src_dir + "demo_SURF_src"),
                      stdout=surf_log_file)
            # save into bin dir
            shutil.copy(self.src_dir + os.path.join("demo_SURF_src",
                                                    "bin", "surf"),
                        surf_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return



    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        self.cfg['param'] = self.default_param
        self.cfg['param'] = dict(self.default_param.items() +
                                 [(p,kwargs[p]) for p in self.default_param.keys() if p in kwargs])

        # no parameters
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout, stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="Try again with simpler images.")
        except RuntimeError:
            return self.error(errcode='runtime')


        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_info({'orsa' : str(self.cfg['param']['orsa'])})
            ar.add_file("input_0.png", info="first uploaded image")
            ar.add_file("input_1.png", info="second uploaded image")
            ar.add_file("matches.png", info="SURF matches")
            ar.add_file("descriptor.png", info="SURF descriptors")
            ar.add_file("matches.txt", compress=True)
            ar.add_file("k1.txt", compress=True)
            ar.add_file("k2.txt", compress=True)
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        #Launch code
        surf_detection = self.run_proc(['extract_surf', 'input_0.png', 'k1.txt'], stdout=stdout, stderr=stdout)
        self.wait_proc(surf_detection, timeout)
        surf_detection2 = self.run_proc(['extract_surf', 'input_1.png', 'k2.txt'], stdout=stdout, stderr=stdout)
        self.wait_proc(surf_detection2, timeout)
        if str(self.cfg['param']['orsa']) == '1':
            surf_matching = self.run_proc(['match_surf', 'k1.txt', 'k2.txt', 'matches.txt','orsa'],stdout=stdout, stderr=stdout)
        else:
            surf_matching = self.run_proc(['match_surf', 'k1.txt', 'k2.txt', 'matches.txt'],stdout=stdout, stderr=stdout)
        self.wait_proc(surf_matching, timeout)
                                           
        surf_display=self.run_proc(['display_surf', 'k1.txt', 'k2.txt','matches.txt','input_0.png', 'input_1.png','descriptor.png', 'matches.png'],stdout=stdout, stderr=stdout)

        self.wait_proc(surf_display, timeout)
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """

        self.cfg['param']['orsa']= '0'
        height = 10 + image(self.work_dir+'matches.png').size[1]
        return self.tmpl_out("result.html", height=height)
