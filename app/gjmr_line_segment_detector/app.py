#-------------------------------------------------------------------------------
"""
LSD IPOL demo app
Line Segment Detector
by Rafael Grompone von Gioi, Jeremie Jakubowicz,
   Jean-Michel Morel and Gregory Randall.
March 20, 2012
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
# LSD IPOL demo main class.
#-------------------------------------------------------------------------------
class app(base_app):
    """LSD IPOL demo main class."""

    # IPOL demo system configuration
    title = "LSD: a Line Segment Detector"
    input_nb = 1          # number of input images
    input_max_pixels = 100000000  # max size (in pixels) of an input image
    input_max_weight = 3 * input_max_pixels  # max size (in bytes)
                                             # of an input file
    input_dtype = '1x8i'  # input image expected data type
    input_ext = '.pgm'    # input image expected extension (i.e. file format)
    is_test = True        # switch to False for deployment

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
    # Download and compile LSD program.
    #---------------------------------------------------------------------------
    def build(self):
        """"Download and compile LSD program."""

        # store common file path in variables
        lsd_url = "http://www.ipol.im/pub/algo/gjmr_line_segment_detector"
        tgz_name = "lsd_1.6.zip"
        tgz_file = self.dl_dir + tgz_name
        build_dir = self.src_dir + "lsd_1.6"
        bin_file = build_dir + "/lsd"
        prog_file = self.bin_dir + "lsd"
        log_file = self.base_dir + "build.log"

        # get the latest source archive
        build.download(lsd_url+"/"+tgz_name, tgz_file)

        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)

            # build the program
            build.run("make -C %s" % build_dir, stdout=log_file)

            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(bin_file, prog_file)

            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #---------------------------------------------------------------------------
    # Parameter handling (none in LSD, just an optional crop).
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None):
        """Parameter handling (none in LSD, just an optional crop)."""

        # if a new experiment on the same image, clone data
        if newrun:
            self.clone_input()

        # save the input image as 'input_0_selection.png', the one to be used
        img = image(self.work_dir + 'input_0.png')
        img.save(self.work_dir + 'input_0_selection.png')
        img.save(self.work_dir + 'input_0_selection.pgm')

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
                    img.save(self.work_dir + 'input_0_selection.pgm')
            return self.tmpl_out('params.html')

        # otherwise, run the algorithm
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    #---------------------------------------------------------------------------
    # Run the algorithm.
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def run(self):
        """Run the algorithm."""

        try:
            run_time = time.time()
            self.run_algo()
            self.cfg['info']['run_time'] = time.time() - run_time
            num_lines = sum(1 for line in open(self.work_dir + 'output.txt'))
            self.cfg['info']['num_detections'] = num_lines
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="Try again with simpler images.")
        except RuntimeError:
            return self.error(errcode='runtime',
                              errmsg="Something went wrong with the program.")
        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png","uploaded_image.png")
            ar.add_file("input_0.png","uploaded_image_gray.png")
            ar.add_file("input_0_selection.png","lsd_input.png")
            ar.add_file("output.txt")
            ar.add_file("output.eps")
            ar.add_file("output.svg")
            ar.add_file("output.png")
            ar.add_file("output-inv.png")
            try:
                version_file = open(self.work_dir + "version.txt", "w")
                p = self.run_proc(["lsd", "--version"], stdout=version_file)
                self.wait_proc(p)
                version_file.close()
                version_file = open(self.work_dir + "version.txt", "r")
                version_info = version_file.readline()
                version_file.close()
            except Exception:
                version_info = "unknown"
            ar.add_info({"LSD version" : version_info})
            ar.add_info({"run time (s)" : self.cfg['info']['run_time']})
            ar.save()

        return self.tmpl_out("run.html")

    #---------------------------------------------------------------------------
    # Core algorithm runner, it could also be called by a batch processor,
    # this one needs no parameter.
    #---------------------------------------------------------------------------
    def run_algo(self):
        """Core algorithm runner, it could also be called by a batch processor,
           this one needs no parameter.
        """

        # run LSD
        p = self.run_proc(['lsd', '-P', 'output.eps', '-S', 'output.svg',
                           'input_0_selection.pgm', 'output.txt'])
        self.wait_proc(p)

        # convert the EPS result into a PNG image
        try:
            p = self.run_proc(['/usr/bin/convert', 'output.svg', 'output.png'])
            self.wait_proc(p)
        except OSError:
            self.log("eps->png conversion failed,"
                     + " 'convert' is probably missing on this system")
        im = image(self.work_dir + "output.png")
        im.convert('1x8i')
        im.invert()
        im.save(self.work_dir + "output-inv.png")

        return

    #---------------------------------------------------------------------------
    # Display the algorithm result.
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def result(self):
        """Display the algorithm result."""

        png = os.path.isfile(self.work_dir + 'output-inv.png')
        h = image(self.work_dir + 'input_0_selection.png').size[1]
        if h < 70:   # if image is too small add some space for archive link
            h = 70
        return self.tmpl_out("result.html", with_png=png, height=h)

#-------------------------------------------------------------------------------
