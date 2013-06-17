"""
NL_Bayes denoising ipol demo web app
"""

from lib import base_app, build, http, image
from lib.misc import ctime
from lib.misc import prod
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time

class app(base_app):
    """ NL_Bayes app """

    title = """Implementation of the "Non-Local Bayes" Image Denoising Algorithm"""
    xlink_article = 'http://www.ipol.im/pub/art/2013/16/'

    input_nb = 1
    input_max_pixels = 1200 * 1200 # max size (in pixels) of an input image
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
        zip_filename = 'NL_Bayes.zip'
        src_dir_name = ''
        prog_filename = 'NL_Bayes'
        # store common file path in variables
        zip_file = self.dl_dir + zip_filename
        prog_file = self.bin_dir + prog_filename
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download('http://www.ipol.im/pub/art/2013/16/' + \
                       zip_filename, zip_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(zip_file, self.src_dir)
            # build the program
            build.run("make OMP=1 -j4 -C %s %s" % (self.src_dir + src_dir_name,
                                             os.path.join(".", prog_filename)),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir + os.path.join(src_dir_name,
                                                    prog_filename), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #
    # PARAMETER HANDLING
    #


    def select_subimage(self, x0, y0, x1, y1):
        """
        cut subimage from original image
        """
        # draw selected rectangle on the image
        imgS = image(self.work_dir + 'input_0.png')
        imgS.draw_line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)],
                       color="red")
        imgS.draw_line([(x0+1, y0+1), (x1-1, y0+1), (x1-1, y1-1),
                        (x0+1, y1-1), (x0+1, y0+1)], color="white")
        imgS.save(self.work_dir + 'input_0s.png')
        # crop the image
        # try cropping from the original input image
        # (if different from input_1)
        im0 = image(self.work_dir + 'input_0.orig.png')
        dx0 = im0.size[0]
        img = image(self.work_dir + 'input_0.png')
        dx = img.size[0]
        if (dx != dx0) :
            z = float(dx0)/float(dx)
            im0.crop((int(x0*z), int(y0*z), int(x1*z), int(y1*z)))
            # resize if cropped image is too big
            if (self.input_max_pixels
                and prod(im0.size) > self.input_max_pixels):
                im0.resize(self.input_max_pixels, method="antialias")
            img = im0
        else :
            img.crop((x0, y0, x1, y1))
        # save result
        img.save(self.work_dir + 'input_0.sel.png')
        return


    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, \
               x0=None, y0=None, x1=None, y1=None, \
               sigma=None, usearea1=None, usearea2=None, computebias=None):
        """
        configure the algo execution
        """

        if newrun:
            self.clone_input()

        if x0:
            self.select_subimage(int(x0), int(y0), int(x1), int(y1))

        return self.tmpl_out("params.html",
                             msg=msg, x0=x0, y0=y0, x1=x1, y1=y1, \
                             sigma=sigma, \
                             usearea1=usearea1, \
                             usearea2=usearea2, \
                             computebias=computebias)


    @cherrypy.expose
    @init_app
    def rectangle(self, action=None, sigma=None, \
                  usearea1=None, usearea2=None, computebias=None, \
                  x=None, y=None, x0=None, y0=None):
        """
        params handling 
        """

        if action == 'run':
            if x == None:
                #save parameters
                try:
                    self.cfg['param'] = {
                                         'sigma': sigma,
                                         'usearea1': usearea1,
                                         'usearea2': usearea2,
                                         'computebias': computebias}
                    self.cfg.save()
                except ValueError:
                    return self.error(errcode='badparams',
                                      errmsg="Incorrect standard"
                                      + " deviation value.")
            else:
                #save parameters
                try:
                    self.cfg['param'] = {
                                         'sigma': sigma,
                                         'usearea1': usearea1,
                                         'usearea2': usearea2,
                                         'computebias': computebias,
                                         'x0' : int(x0),
                                         'y0' : int(y0),
                                         'x1' : int(x),
                                         'y1' : int(y)}
                    self.cfg.save()
                except ValueError:
                    return self.error(errcode='badparams',
                                      errmsg="Incorrect parameters.")
        
            # use the whole image if no subimage is available
            try:
                img = image(self.work_dir + 'input_0.sel.png')
            except IOError:
                img = image(self.work_dir + 'input_0.png')
                img.save(self.work_dir + 'input_0.sel.png')

            # go to the wait page, with the key
            http.redir_303(self.base_url + "wait?key=%s" % self.key)
            return
        else:
            # use a part of the image
            if x0 == None:
                # first corner selection
                x = int(x)
                y = int(y)
                # draw a cross at the first corner
                img = image(self.work_dir + 'input_0.png')
                img.draw_cross((x, y), size=4, color="white")
                img.draw_cross((x, y), size=2, color="red")
                img.save(self.work_dir + 'input.png')
                return self.tmpl_out("params.html", sigma=sigma, \
                                      usearea1=usearea1, \
                                      usearea2=usearea2, \
                                      computebias=computebias, x0=x, y0=y)
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
                #save parameters
                try:
                    self.cfg['param'] = {
                                         'sigma': sigma,
                                         'usearea1': usearea1,
                                         'usearea2': usearea2,
                                         'computebias': computebias,
                                         'x0' : x0,
                                         'y0' : y0,
                                         'x1' : x1,
                                         'y1' : y1}
                    self.cfg.save()
                except ValueError:
                    return self.error(errcode='badparams',
                                      errmsg="Incorrect parameters.")
                #select subimage
                self.select_subimage(x0, y0, x1, y1)
                # go to the wait page, with the key
                http.redir_303(self.base_url + "wait?key=%s" % self.key)
            return

    @cherrypy.expose
    @init_app
    def wait(self):
        """
        run redirection
        """
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        # read the parameters
        sigma = self.cfg['param']['sigma']
        usearea1 = self.cfg['param']['usearea1']
        usearea2 = self.cfg['param']['usearea2']
        computebias = self.cfg['param']['computebias']

        # run the algorithm
        try:
            run_time = time.time()
            print 'run_time1'
            print run_time
            self.run_algo(sigma, usearea1, usearea2, computebias)
            print 'time.time()'
            print time.time()
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            print "Run time error"
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="uploaded image")
            ar.add_file("input_0.sel.png", info="selected subimage")
            ar.add_file("noisy.png", info="noisy image")
            ar.add_file("denoised.png", info="denoised image")
            ar.add_file("diff.png", info="difference image")

            try:
                test = str(computebias)            
                computebiasParam = 1 if test != 'None' else 0
            except StandardError:
                computebiasParam = 0

            if computebiasParam == 1:
                ar.add_file("bias.png", info="bias image")
                ar.add_file("basic_bias.png", info="basic bias image")
                ar.add_file("diff_bias.png", info="difference bias image")

            ar.add_info({"sigma": sigma})
            ar.add_info({"usearea1": usearea1})
            ar.add_info({"usearea2": usearea2})
            ar.add_info({"computebias": computebias})

            ar.save()
        return self.tmpl_out("run.html")

    def run_algo(self, sigma, usearea1, usearea2, computebias, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        """

        try:
            test = str(computebias)            
            computebiasParam = 1 if test != 'None' else 0
        except StandardError:
            computebiasParam = 1

        procOptions = ['NL_Bayes', 'input_0.sel.png', '%d' % sigma, \
                       'noisy.png', 'denoised.png', 'basic.png', \
                       'diff.png', 'bias.png', 'basic_bias.png', \
                       'diff_bias.png', \
                       '%d' % usearea1, '%d' % usearea2, \
                       '%d' % computebiasParam]

        # Run
        procDesc = self.run_proc(procOptions)
        self.wait_proc(procDesc, timeout*0.8)

        
    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        print "Display results"

        # read the parameters
        sigma = self.cfg['param']['sigma']
        usearea1 = self.cfg['param']['usearea1']
        usearea2 = self.cfg['param']['usearea2']
        computebias = self.cfg['param']['computebias']

        try:
            x0 = self.cfg['param']['x0']
        except KeyError:
            x0 = None
        try:
            y0 = self.cfg['param']['y0']
        except KeyError:
            y0 = None
        try:
            x1 = self.cfg['param']['x1']
        except KeyError:
            x1 = None
        try:
            y1 = self.cfg['param']['y1']
        except KeyError:
            y1 = None

        (sizeX, sizeY) = image(self.work_dir + 'input_0.sel.png').size
        zoom_factor = None
        return self.tmpl_out("result.html", sigma=sigma, \
                             usearea1=usearea1, 
                             usearea2=usearea2,
                             computebias=computebias, \
                             x0=x0, y0=y0, x1=x1, y1=y1, \
                             sizeX=sizeX, sizeY=sizeY, \
                             zoom_factor=zoom_factor)

