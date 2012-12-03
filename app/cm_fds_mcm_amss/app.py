"""
mcm_amss ipol demo web app
"""

from lib import base_app, image, build, http
from lib.misc import ctime
from lib.base_app import init_app
import os.path
import time
import shutil
import cherrypy
from cherrypy import TimeoutError


class app(base_app):
    """ mcm_amss app """

    title = "Finite Difference Schemes for MCM and AMSS"
    xlink_article = 'http://www.ipol.im/pub/art/2011/cm_fds/'

    input_nb = 1
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.tiff' # input image expected extension (ie file format)
    is_test = False

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

       # select the base_app steps to expose
        # index() is generic
        base_app.index.im_func.exposed = True
        # input_xxx() are modified from the template
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
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        # MCM
        # store common file path in variables
        mcm_tgz_file = self.dl_dir + "fds_mcm.tar.gz"
        mcm_tgz_url = \
            "http://www.ipol.im/pub/algo/cm_fds_mcm_amss/fds_mcm.tar.gz"
        mcm_prog_file = self.bin_dir + "mcm"
        mcm_log = self.base_dir + "build_mcm.log"
        # get the latest source archive
        build.download(mcm_tgz_url, mcm_tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(mcm_prog_file)
            and ctime(mcm_tgz_file) < ctime(mcm_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(mcm_tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s mcm OMP=1"
                      % (self.src_dir + os.path.join("fds_mcm", "mcm")),
                      stdout=mcm_log)
            # save into bin dir
            shutil.copy(self.src_dir + os.path.join("fds_mcm", "mcm", "mcm"),
                        mcm_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        # AMSS
        # store common file path in variables
        amss_tgz_file = self.dl_dir + "fds_amss.tar.gz"
        amss_tgz_url = \
            "http://www.ipol.im/pub/algo/cm_fds_mcm_amss/fds_amss.tar.gz"
        amss_prog_file = self.bin_dir + "amss"
        amss_log = self.base_dir + "build_amss.log"
        # get the latest source archive
        build.download(amss_tgz_url, amss_tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(amss_prog_file)
            and ctime(amss_tgz_file) < ctime(amss_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(amss_tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s amss OMP=1"
                      % (self.src_dir + os.path.join("fds_amss", "amss")),
                      stdout=amss_log)
            # save into bin dir
            shutil.copy(self.src_dir + os.path.join("fds_amss", "amss", "amss"),
                        amss_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #
    # PARAMETER HANDLING
    #

    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, scale_r=None, step=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

        if (step == None):
            step = '0'

        return self.tmpl_out("params.html", msg=msg,
                             scale_r=scale_r, step=step)


    @cherrypy.expose
    @init_app
    def grid(self, stepG, scaleR, action=None, x=0, y=0):
        """
        handle the grid drawing and selection
        """
        if action == 'run':
            # use the whole image
            img = image(self.work_dir + 'input_0.png')
            img.save(self.work_dir + 'input' + self.input_ext)
            img.save(self.work_dir + 'input.png')
            # go to the wait page, with the key and scale
            stepG = 0
            http.redir_303(self.base_url
                           + "wait?key=%s&scaleR=%s&step=%s" 
                           % (self.key, scaleR, stepG))
            return
        elif action == 'redraw':
            # draw the grid
            step = int(stepG)
            if 0 < step:
                img = image(self.work_dir + 'input_0.png')
                img.draw_grid(step)
                img.save(self.work_dir + 'input_grid.png')
                grid = True
            else:
                grid = False
            return self.tmpl_out("params.html", step=stepG,
                                 grid=grid, scale_r=float(scaleR))
        else:
            # use a part of the image
            x = int(x)
            y = int(y)
            # get the step used to draw the grid
            step = int(stepG)
            assert step > 0
            # cut the image section
            img = image(self.work_dir + 'input_0.png')
            x0 = (x / step) * step
            y0 = (y / step) * step
            x1 = min(img.size[0], x0 + step)
            y1 = min(img.size[1], y0 + step)
            img.crop((x0, y0, x1, y1))
            # zoom and save image
            img.resize((400, 400), method="nearest")
            img.save(self.work_dir + 'input' + self.input_ext)
            img.save(self.work_dir + 'input.png')
            # go to the wait page, with the key and scale
            http.redir_303(self.base_url
                           + "wait?key=%s&scaleR=%s&step=%s" 
                           % (self.key, scaleR, stepG))
            return

    #
    # EXECUTION AND RESULTS
    #

    @cherrypy.expose
    @init_app
    def wait(self, scaleR, step):
        """
        params handling and run redirection
        """
        # read parameters
        try:
            self.cfg['param'] = {'scale_r' : float(scaleR),
                                 'grid_step' : int(step),
                                 'zoom_factor' : (400.0 / int(step)
                                                  if int(step) > 0
                                                  else 1.)}
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="Wrong input parameters")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html",
                             input=['input.png?step=%s' % step])

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # read the parameters
        scale_r = self.cfg['param']['scale_r']
        zoom_factor = self.cfg['param']['zoom_factor']

        # denormalize the scale
        scale_r *= zoom_factor

        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(scale_r, stdout=stdout, timeout=self.timeout)
            self.cfg['info']['run_time'] = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="uploaded")
            ar.add_file("input.png", info="input")
            ar.add_file("output_MCM.png", info="output MCM")
            ar.add_file("output_AMSS.png", info="output AMSS")
            ar.add_info({'scale_r' : self.cfg['param']['scale_r'],
                         'zoom_factor' : self.cfg['param']['zoom_factor']})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, scale_r, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """             
        stdout = stdout
        # process image
        p1 = self.run_proc(['mcm', str(scale_r),
                            self.work_dir + 'input' + self.input_ext,
                            self.work_dir + 'output_MCM' + self.input_ext])
        p2 = self.run_proc(['amss', str(scale_r),
                            self.work_dir + 'input' + self.input_ext, 
                            self.work_dir + 'output_AMSS' + self.input_ext]) 
        self.wait_proc([p1, p2], timeout)
        im = image(self.work_dir + 'output_MCM' + self.input_ext)
        im.save(self.work_dir + 'output_MCM.png')
        im = image(self.work_dir + 'output_AMSS' + self.input_ext)
        im.save(self.work_dir + 'output_AMSS.png')

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # read the parameters
        scale_r = self.cfg['param']['scale_r']
        zoom_factor = self.cfg['param']['zoom_factor']

        return self.tmpl_out("result.html", 
                             scale_r=scale_r, zoom_factor=zoom_factor, 
                             sizeY="%i" % image(self.work_dir
                                                + 'input.png').size[1])
