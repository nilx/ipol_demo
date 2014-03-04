"""
screened Poisson equation ipol demo web app
"""

from lib import base_app, build, http
from lib import image
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time
import PIL

class app(base_app):
    """ screened Poisson equation app """

    title = "Screened Poisson Equation for Image Contrast Enhancement"

    input_nb = 1
    input_max_pixels = 700 * 700 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = False

    xlink_article = 'http://www.ipol.im/pub/pre/84/'

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
        tgz_url = "http://www.ipol.im/pub/pre/84/screened_poisson.tgz"
        tgz_file = self.dl_dir + "screened_poisson.tgz"
        prog = "screened_poisson"
        bin_file = self.bin_dir + prog
        build_file = self.src_dir + os.path.join("screened_poisson", prog)
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if any dest file is missing, or too old
        if (os.path.isfile(bin_file)
            and ctime(tgz_file) < ctime(bin_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the programs
            build.run("make -C %s %s"
                      % (self.src_dir + "screened_poisson", prog),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(build_file, bin_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


    #
    # PARAMETER HANDLING
    #
    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, L="1.0e-4", s="0.1"):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

        return self.tmpl_out("params.html", msg=msg, L=L, s=s)

    @cherrypy.expose
    @init_app
    def wait(self, L="1.0e-4", s="0.1"):
        """
        params handling and run redirection
        """
        # save and validate the parameters
        if (float(L) < 0) or (float(L) > 1.5) :
            return self.error(errcode='badparams',
                          errmsg="Lambda must be a value in the range (0, 1.5]")
        try:
            L = float(L)
            s = float(s)
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")
#self.cfg['param'] = {'l' : L}
#self.cfg['param'] = {'s' : s}
#self.cfg.save()
        self.cfg['param']['l'] = L
        self.cfg['param']['s'] = s


        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        # read the parameters
        L = self.cfg['param']['l']
        s = self.cfg['param']['s']
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(L, s, stdout=stdout, timeout=self.timeout)
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
            ar.add_file("inputSimplest.png", info="original (simplest)")
            ar.add_file("output.png", info="result image")
            ar.add_info({"L": L})
            ar.add_info({"s": s})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, L, s, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        p = self.run_proc(['screened_poisson', str(L), 
                           'input_0.png', 'inputSimplest.png', 'output.png', 
                           str(s)],
                           stdout=None, stderr=None)
        self.wait_proc(p, timeout)

        # compute histograms of images
        scale_h = 0
        for im_basename in ('input_0', 'inputSimplest', 'output'):
            im = PIL.Image.open(self.work_dir + im_basename + '.png')
            h = im.histogram()
            if 'input_0' == im_basename:
                # the scale is based on then input image, first to be computed
                scale_h = 127. / max(h)
            # define RGB colors and dark variants
            color = {'R' : (255, 0, 0), 'G' : (0, 255, 0), 'B' : (0, 0, 255)}
            dark = {'R' : (63, 0, 0), 'G' : (0, 63, 0), 'B' : (0, 0, 63)}
            # draw histograms of R, G, B values
            for channel in ('R', 'G', 'B'):
                # PIL stores the RGB histograms in a single array
                xoffset = {'R' : 0, 'G' : 256, 'B' : 512}[channel]
                # new histogram image
                him = PIL.Image.new('RGB', (256, 128), (255, 255, 255))
                draw = PIL.ImageDraw.Draw(him)
                for x in range(0, 256):
                    hx = int(h[x+xoffset] * scale_h)
                    if hx <= 127:
                        draw.line([(x, 127), (x, 127 - hx)],
                                  fill=color[channel])
                    else:
                        draw.line([(x, 127), (x, 0)],
                                  fill=dark[channel])
                him.save(self.work_dir + im_basename + '_%s.png' % channel)

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        # read the parameters
        L = self.cfg['param']['l']
        s = self.cfg['param']['s']
        sizeX = image(self.work_dir + 'input_0.png').size[0]
        sizeY = max(image(self.work_dir + 'input_0.png').size[1],
                    3 * 128 + 4 * 20)

        return self.tmpl_out("result.html", L=L, s=s,
                             sizeX=sizeX, sizeY=sizeY)
