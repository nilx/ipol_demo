"""
Texture Synthesis by Heeger-Bergen algorithm demo web app
"""

from lib import base_app, build, http, image
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time
import math


class app(base_app):
    """ Texture Synthesis by Heeger-Bergen algorithm app """

    title = 'The Heeger & Bergen Pyramid Based Texture Synthesis Algorithm'

    input_nb = 1
    input_max_pixels = 700 * 700        # max size (in pixels) of input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False

    xlink_article = "http://www.ipol.im/pub/pre/79/"

    def __init__(self):
        """
        App setup
        """
        # Setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # Select the base_app steps to expose
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
        Program build/update
        """
        # Store common file path in variables
        tgz_url = "http://www.ipol.im/pub/pre/79/heegerbergen_1.00.tgz" 
        tgz_file = self.dl_dir + "heegerbergen_1.00.tgz"
        prog_file = self.bin_dir + "hb"
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
            build.run("make -j4 -C %s hb"
                      % (self.src_dir + "heegerbergen_1.00"),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir 
                        + os.path.join("heegerbergen_1.00", "hb"), prog_file)
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
            self.clone_input()

        ratio = 1.
        img = image(self.work_dir + 'input_0.png')
        sizemax = min(img.size[0], img.size[1])
        npyr = min(4, int(math.floor(math.log(sizemax, 2)))-2)
        nmax = min(8, int(math.floor(math.log(sizemax, 2)))-2)

        return self.tmpl_out("params.html", msg=msg, 
                             ratio=ratio, npyr=npyr, nmax=nmax)

    @cherrypy.expose
    @init_app
    def crop(self, ratio=1., npyr=1, action=None, x=None, y=None,
             x0=None, y0=None, x1=None, y1=None, newrun=False):
        """
        select a rectangle in the image
        """
        if newrun:
            self.clone_input()

        if action == 'run':
            if x1 == None:
                # use the whole image
                img = image(self.work_dir + 'input_0.png')
                img.save(self.work_dir + 'input' + self.input_ext)
                img.save(self.work_dir + 'input.png')
            else:
                self.cfg['param']['x0'] = x0
                self.cfg['param']['y0'] = y0
                self.cfg['param']['x1'] = x1
                self.cfg['param']['y1'] = y1
            self.cfg['param']['ratio'] = ratio
            self.cfg['param']['npyr'] = npyr
            # go to the wait page, with the key
            http.redir_303(self.base_url + "wait?key=%s&ratio=%s&npyr=%s" 
                           % (self.key, ratio, npyr))
            return
        else:
            img = image(self.work_dir + 'input_0.png')
            sizemax = min(img.size[0], img.size[1])
            nmax = min(8, int(math.floor(math.log(sizemax, 2)))-2)
            # use a part of the image
            if x0 == None:
                if x == None:
                    return self.tmpl_out("params.html", 
                                         ratio=ratio, npyr=npyr, nmax=nmax)
                else:
                    # first corner selection
                    x = int(x)
                    y = int(y)
                    # draw a cross at the first corner
                    img = image(self.work_dir + 'input_0.png')
                    img.draw_cross((x, y), size=4, color="white")
                    img.draw_cross((x, y), size=2, color="red")
                    img.save(self.work_dir + 'input_corner.png')
                    return self.tmpl_out("params.html",
                                         x0=x, y0=y, 
                                         ratio=ratio, npyr=npyr, nmax=nmax)
            else:
                # second corner selection
                x0 = int(x0)
                y0 = int(y0)
                x1 = int(x)
                y1 = int(y)
                # reorder the corners
                (x0, x1) = (min(x0, x1), max(x0, x1))
                (y0, y1) = (min(y0, y1), max(y0, y1))
                assert (x1 - x0) > 0
                assert (y1 - y0) > 0
                # draw selection rectangle on the image
                img = image(self.work_dir + 'input_0.png')
                img.draw_line([(x0, y0), (x1, y0), 
                               (x1, y1), (x0, y1), (x0, y0)], color="red")
                img.draw_line([(x0+1, y0+1), (x1-1, y0+1),
                               (x1-1, y1-1), (x0+1, y1-1),
                               (x0+1, y0+1)], color="white")
                img.save(self.work_dir + 'input_selection.png')
                # crop from the original input image
                img = image(self.work_dir + 'input_0.orig.png')
                img_ = image(self.work_dir + 'input_0.png')
                (nx, ny) = img.size
                (nx_, ny_) = img_.size
                (zx, zy) = (float(nx) / float(nx_),
                            float(ny) / float(ny_))
                img.crop((int(x0 * zx), int(y0 * zy),
                          int(x1 * zx), int(y1 * zy)))
                img.save(self.work_dir + 'input' + self.input_ext)
                img.save(self.work_dir + 'input.png')
                #check final selected image size
                (sx, sy) = img.size
                if sx < 16 or sy < 16:
                    return self.tmpl_out("params.html",
                                         x0=x0, y0=None, x1=None, y1=None, 
                                         ratio=ratio, npyr=npyr, nmax=nmax)
                else:
                    sizemax = min(sx, sy)
                    nmax = min(8, int(math.floor(math.log(sizemax, 2)))-2)
                    if int(npyr) > int(nmax):
                        npyr = nmax
                    return self.tmpl_out("params.html",
                                    x0=x0, y0=y0, x1=x1, y1=y1, 
                                    ratio=ratio, npyr=npyr, nmax=nmax)
            return

    @cherrypy.expose
    @init_app
    def wait(self, ratio=1, npyr=1):
        """
        params handling and run redirection
        """
        try:
            ratio = float(ratio)
            assert ratio >= 1.
            assert ratio <= 5.
        except ValueError:
            ratio = 1.
        except AssertionError:
            ratio = 1.
        try:
            npyr = int(npyr)
            assert npyr >= 1
            assert npyr <= 8
        except ValueError:
            npyr = 1
        except AssertionError:
            npyr = 1
        self.cfg['param']['ratio'] = ratio
        self.cfg['param']['npyr'] = npyr
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")


    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        try:
            run_time = time.time()
            self.run_algo()
            self.cfg['info']['run_time'] = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input.png", info="input image")
            ar.add_file("input_cropped.png", 
                        info="input cropped (actual input)")
            ar.add_file("output.png", info="output image")
            try:
                fh = open(self.work_dir + 'input_selection.png')
                fh.close()
                ar.add_file("input_selection.png", info="input selected")
                ar.add_file("input_0.orig.png", info="uploaded image")
            except IOError:
                pass
            ar.add_info({"ratio": self.cfg['param']['ratio']})
            ar.add_info({"npyr": self.cfg['param']['npyr']})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        if None == timeout:
            timeout = self.timeout

        if (1. == self.cfg['param']['ratio']):
            p = self.run_proc(['hb', '-p', '1', 
                               '-s', str(self.cfg['param']['npyr']),
                               'input.png', 'output.png'])
        else:
            p = self.run_proc(['hb', '-p', '1',
                               '-x', str(self.cfg['param']['ratio']),
                               '-y', str(self.cfg['param']['ratio']),
                               '-s', str(self.cfg['param']['npyr']),
                               'input.png', 'output.png'])
        self.wait_proc(p, timeout)

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        return self.tmpl_out("result.html",
                             height=image(self.work_dir
                                          + 'output.png').size[1])
