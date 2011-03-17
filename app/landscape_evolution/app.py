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

    title = "Landscape evolution"

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
        # store common file path in variables
        tgz_url = "https://edit.ipol.im/edit/algo/" \
            + "landscape_evolution/landscape_evolution.tar.gz"
        tgz_file = self.dl_dir + "landscape_evolution.tar.gz"
        prog_file = self.bin_dir + "landscape_evolution"
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s landscape_evolution"
                      % (self.src_dir + "landscape_evolution"),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir 
                        + os.path.join("landscape_evolution", "landscape_evolution"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #
    # PARAMETER HANDLING
    #

    @cherrypy.expose
    @init_app
    def grid(self, step, rain, expm, erosione, erosioncreep, erosions, iterationw, iteration, waterlandcst, maxvarwater, time_step, grid_step=0, action=None, x=0, y=0):
        """
        handle the grid drawing and selection
        """
        if action == 'run':
            # use the whole image
            img = image(self.work_dir + 'input_0.png')
            img.save(self.work_dir + 'input' + self.input_ext)
            img.save(self.work_dir + 'input.png')
            # go to the wait page, with the key and scale
            http.redir_303(self.base_url
                           + "wait?key=%s&time_step=%s&step=%s&rain=%s&expm=%s&erosione=%s&erosioncreep=%s&erosions=%s&iteration=%s&iterationw=%s&waterlandcst=%s&maxvarwater=%s"
                           % (self.key, time_step, step, rain, expm, erosione, erosioncreep, erosions, iteration,iterationw,waterlandcst,maxvarwater))
            return
            return

    #
    # EXECUTION AND RESULTS
    #

    @cherrypy.expose
    @init_app
    def wait(self, time_step, step, rain, expm, erosione, erosioncreep, erosions, iteration,iterationw,waterlandcst,maxvarwater):
        """
        params handling and run redirection
        """
        # read parameters
        try:
            self.cfg['param'] = {'time_step' : float(time_step),
                                 'grid_step' : int(step),
                                 'rain' : float(rain),
                                 'expm' : float(expm),
                                 'erosione' : float(erosione),
                                 'erosioncreep' : float(erosioncreep),
                                 'erosions' : float(erosions),
                                 'iteration' : float(iteration),
                                 'iterationw' : float(iterationw),
                                 'waterlandcst' : float(waterlandcst),
                                 'maxvarwater' : float(maxvarwater),
                                 'zoom_factor' : (400.0 / int(step)
                                                  if int(step) > 0
                                                  else 1.)}
            self.cfg.save()
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
        time_step = self.cfg['param']['time_step']
        zoom_factor = self.cfg['param']['zoom_factor']
        expm = self.cfg['param']['expm']
        erosione = self.cfg['param']['erosione']
        erosioncreep = self.cfg['param']['erosioncreep']
        erosions = self.cfg['param']['erosions']
        iteration = self.cfg['param']['iteration']
        iterationw = self.cfg['param']['iterationw']
        waterlandcst = self.cfg['param']['waterlandcst']
        maxvarwater = self.cfg['param']['maxvarwater']
        rain = self.cfg['param']['rain']

        # denormalize the scale
        time_step *= zoom_factor

        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(time_step, rain, expm, erosione, erosioncreep, erosions, iteration, iterationw, waterlandcst, maxvarwater, stdout=stdout, timeout=self.timeout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
	"""
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="uploaded")
            ar.add_file("input.png", info="input")
            ar.add_file("output_MCM.png", info="output MCM")
            ar.add_file("output_AMSS.png", info="output AMSS")
            ar.add_info({'time_step' : self.cfg['param']['time_step'],
                         'zoom_factor' : self.cfg['param']['zoom_factor']})
            ar.save()
	"""

        return self.tmpl_out("run.html")

    def run_algo(self, time_step, rain, expm, erosione, erosioncreep, erosions, iteration, iterationw, waterlandcst, maxvarwater, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        stdout = stdout
        # process image
        p1 = self.run_proc(['landscape_evolution',
                            self.work_dir + 'input' + self.input_ext,
                            self.work_dir + 'result',
                            str(time_step),
                            str(rain),
                            str(expm),
                            str(erosione),
                            str(erosioncreep),
                            str(erosions),
                            str(iteration),
                            str(iterationw),
                            str(waterlandcst),
                            str(maxvarwater)
                            ])
        self.wait_proc([p1], timeout)
        im = image(self.work_dir + 'result_l.tif')
        im.save(self.work_dir + 'result_l.png')
        im = image(self.work_dir + 'result_w.tif')
        im.save(self.work_dir + 'result_w.png')
        im = image(self.work_dir + 'result_orig.tif')
        im.save(self.work_dir + 'result_orig.png')
        im = image(self.work_dir + 'result_w_only.tif')
        im.save(self.work_dir + 'result_w_only.png')
        im = image(self.work_dir + 'result_c.tif')
        im.save(self.work_dir + 'result_c.png')


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # read the parameters
        time_step = self.cfg['param']['time_step']
        grid_step = self.cfg['param']['grid_step']
        zoom_factor = self.cfg['param']['zoom_factor']
        rain  = self.cfg['param']['rain']
        expm  = self.cfg['param']['expm']
        erosione  = self.cfg['param']['erosione']
        erosioncreep  = self.cfg['param']['erosioncreep']
        erosions  = self.cfg['param']['erosions']
        iteration  = self.cfg['param']['iteration']
        iterationw  = self.cfg['param']['iterationw']
        waterlandcst  = self.cfg['param']['waterlandcst']
        maxvarwater  = self.cfg['param']['maxvarwater']

        return self.tmpl_out("result.html", step=grid_step,
                             time_step=time_step, zoom_factor=zoom_factor,
                             rain=rain,
                             expm=expm,
                             erosione=erosione,
                             erosioncreep=erosioncreep,
                             erosions=erosions,
                             iteration=iteration,
                             iterationw=iterationw,
                             waterlandcst=waterlandcst,
                             maxvarwater=maxvarwater,
			     sizeY="%i" % image(self.work_dir
                                                + 'input.png').size[1])
