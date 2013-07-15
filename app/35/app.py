#-------------------------------------------------------------------------------
"""
ARCED IPOL demo app
A Review of Classic Edge Detectors
by Haldo Sponton and Juan Cardelino.
June 27, 2013
"""
#-------------------------------------------------------------------------------

from lib import base_app, build, http, image
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import time

#-------------------------------------------------------------------------------
# ARCED IPOL demo main class.
#-------------------------------------------------------------------------------
class app(base_app):
    """ARCED IPOL demo main class."""

    # IPOL demo system configuration
    title = "A Review of Classic Edge Detectors"
    input_nb = 1          # number of input images
    input_max_pixels = 100000000  # max size (in pixels) of an input image
    input_max_weight = 3 * input_max_pixels  # max size (in bytes)
                                             # of an input file
    input_dtype = '1x8i'  # input image expected data type
    input_ext = '.png'    # input image expected extension (i.e. file format)
    is_test = False        # switch to False for deployment
    xlink_article = "http://www.ipol.im/pub/pre/35/"

    #---------------------------------------------------------------------------
    # Set up application.
    #---------------------------------------------------------------------------
    def __init__(self):
        """Set up application."""

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

    #---------------------------------------------------------------------------
    # Download and compile EDGES program.
    #---------------------------------------------------------------------------
    def build(self):
        """"Download and compile EDGES program."""

        # store common file path in variables
        tgz_file = self.dl_dir + "classic_edge_detectors_1.0.zip"
        prog_file = self.bin_dir + "edges"
        log_file = self.base_dir + "build.log"

        # get the latest source archive
        build.download("http://www.ipol.im/pub/pre/35/"
                   	+ "classic_edge_detectors_1.0.zip", tgz_file)

        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("cd %s && make" % (self.src_dir
                                         + "classic_edge_detectors_1.0"),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir + "classic_edge_detectors_1.0/edges",
                        prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #---------------------------------------------------------------------------
    # Parameter handling (just an optional crop).
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None):
        """Parameter handling (just an optional crop)."""

        # if a new experiment on the same image, clone data
        if newrun:
            self.clone_input()

        # save the input image as 'input_0_selection.png', the one to be used
        img = image(self.work_dir + 'input_0.png')
        img.save(self.work_dir + 'input_0_selection.png')

        # initialize subimage parameters
        self.cfg['param'] = {'x1':-1, 'y1':-1, 'x2':-1, 'y2':-1}
        self.cfg.save()

        return self.tmpl_out('params.html')

    #---------------------------------------------------------------------------
    # Input handling and run redirection.
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """Input handling and run redirection."""

        # handle image crop if used
        if not 'action' in kwargs:
            # read click coordinates
            x = kwargs['click.x']
            y = kwargs['click.y']
            x1 = self.cfg['param']['x1']
            y1 = self.cfg['param']['y1']
            self.cfg.save()
            img = image(self.work_dir + 'input_0.png')
            # check if the click is inside the image
            if int(x) >= 0 and int(y) >= 0 and \
                 int(x) < img.size[0] and int(y) < img.size[1]:
                if int(x1) < 0 or int(y1) < 0 :  # first click
                    # update (x1,y1)
                    self.cfg['param']['x1'] = int(x)
                    self.cfg['param']['y1'] = int(y)
                    self.cfg.save()

                    # draw cross
                    img.convert('3x8i')
                    img.draw_cross((int(x), int(y)), size=9, color="red")
                    img.save(self.work_dir + 'input_0_selection.png')
                elif int(x1) != int(x) and int(y1) != int(y) :  # second click
                    # update (x2,y2)
                    self.cfg['param']['x2'] = int(x)
                    self.cfg['param']['y2'] = int(y)
                    self.cfg.save()

                    # order points such that (x1,y1) is the lower left corner
                    (x1, x2) = sorted((int(x1), int(x)))
                    (y1, y2) = sorted((int(y1), int(y)))
                    assert (x2 - x1) > 0 and (y2 - y1) > 0

                    # crop the image
                    img.crop((x1, y1, x2+1, y2+1))
                    img.save(self.work_dir + 'input_0_selection.png')
            return self.tmpl_out('params.html')

        # save and validate the parameters
        try:
            # MISC
            self.cfg['param']['inv'] = kwargs['inv']
            # FDED
            self.cfg['param']['th_fded'] = kwargs['th_fded']
            # HARALICK
            self.cfg['param']['rho'] = kwargs['rho']
            # MARR-HILDRETH GAUSSIAN
            self.cfg['param']['sigma'] = kwargs['sigma']
            self.cfg['param']['n'] = kwargs['n']
            self.cfg['param']['tzc'] = kwargs['tzc']
            # MARR-HILDRETH LOG
            self.cfg['param']['sigma2'] = kwargs['sigma2']
            self.cfg['param']['n2'] = kwargs['n2']
            self.cfg['param']['tzc2'] = kwargs['tzc2']		
            self.cfg.save()

        except ValueError:
            return self.error(errcode='badparams',
                errmsg="The parameter must be numeric.")

        # otherwise, run the algorithm
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    #---------------------------------------------------------------------------
    # Run the algorithm.
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # read the parameters
        # MISC
        inv = self.cfg['param']['inv']
		# FDED
        th_fded = self.cfg['param']['th_fded']
		# HARALICK
        rho = self.cfg['param']['rho']
		# MARR-HILDRETH GAUSSIAN
        sigma = self.cfg['param']['sigma']
        n = self.cfg['param']['n']
        tzc = self.cfg['param']['tzc']
		# MARR-HILDRETH LOG
        sigma2 = self.cfg['param']['sigma2']
        n2 = self.cfg['param']['n2']
        tzc2 = self.cfg['param']['tzc2']
        # run the algorithm
        try:
            run_time = time.time()
            self.run_algo(th_fded, rho, sigma, n, tzc, sigma2, n2,
                          tzc2, inv)
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
            ar.add_file("input_0.png", info="input image")
            ar.add_file("input_0_selection.png", info="cropped input image")
            ar.add_file("out_roberts.png",
                        info="output image of Roberts algorithm")
            ar.add_file("out_prewitt.png",
                        info="output image of Prewitt algorithm")
            ar.add_file("out_sobel.png", info="output image of Sobel algorithm")
            ar.add_file("out_mh.png",
               info="output image of Marr-Hildreth algorithm (Gaussian kernel)")
            ar.add_file("out_mhl.png",
                info="output image of Marr-Hildreth algorithm (LoG kernel)")
            ar.add_file("out_haralick.png",
                        info="output image of Haralick algorithm")
            ar.add_info({"th_fded": th_fded})
            ar.add_info({"rho": rho})
            ar.add_info({"sigma": sigma})
            ar.add_info({"n": n})
            ar.add_info({"tzc": tzc})
            ar.add_info({"sigma2": sigma2})
            ar.add_info({"n2": n2})
            ar.add_info({"tzc2": tzc2})
            ar.save()

        return self.tmpl_out("run.html")

    #---------------------------------------------------------------------------
    # Core algorithm runner
    #---------------------------------------------------------------------------
    def run_algo(self, th_fded, rho, sigma, n, tzc, sigma2, n2, tzc2, inv):
        """
        the core algo runner
        """
        p = self.run_proc(["edges", "-r", str(th_fded), "-p", str(th_fded),
                           "-s", str(th_fded), "-m", str(sigma), str(n),
                           str(tzc), "-l", str(sigma2), str(n2), str(tzc2),
                           "-h", str(rho), "input_0_selection.png"])
        self.wait_proc(p)
        
        # Invert output images
        if inv == 1:
            im = image(self.work_dir + 'out_roberts.png')
            inv_im = image.invert(im)
            inv_im.save(self.work_dir + 'out_roberts.png')
            im = image(self.work_dir + 'out_prewitt.png')
            inv_im = image.invert(im)
            inv_im.save(self.work_dir + 'out_prewitt.png')
            im = image(self.work_dir + 'out_sobel.png')
            inv_im = image.invert(im)
            inv_im.save(self.work_dir + 'out_sobel.png')
            im = image(self.work_dir + 'out_mh.png')
            inv_im = image.invert(im)
            inv_im.save(self.work_dir + 'out_mh.png')
            im = image(self.work_dir + 'out_mhl.png')
            inv_im = image.invert(im)
            inv_im.save(self.work_dir + 'out_mhl.png')
            im = image(self.work_dir + 'out_haralick.png')
            inv_im = image.invert(im)
            inv_im.save(self.work_dir + 'out_haralick.png')
        return

    #---------------------------------------------------------------------------
    # Display the algorithm result.
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        try:
            # if image is too small add space for archive link
            h = max(70, image(self.work_dir + 'input_0_selection.png').size[1])
            png = True
        except Exception:
            h = 70
            png = False

        return self.tmpl_out("result.html", with_png=png, height=h)
#-------------------------------------------------------------------------------
