"""
selective_contrast_adjustment ipol demo web app
"""

from lib import base_app, build, http, image
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time

import PIL.Image

def check_grayimage(nameimage):
    """
    Check if image is monochrome (1 channel or 3 identical channels)
    """
    isGray = True
  
    im = PIL.Image.open(nameimage)
    if im.mode not in ("L", "RGB"):
        raise ValueError("Unsuported image mode for histogram computation")

    if im.mode == "RGB":
        pix = im.load()
        size = im.size
        for y in range(0, size[1]):
            if not isGray:
                break
            for x in range(0, size[0]):
                if not isGray:
                    break
                if (pix[x, y][0] != pix[x, y][1]) or \
                   (pix[x, y][0] != pix[x, y][2]):
                    isGray = False


    return isGray

class app(base_app):
    """ selective_contrast_adjustment app """

    title = "Selective Contrast Adjustment by Poisson Equation"

    input_nb = 1
    input_max_pixels = 700 * 700 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = False
    xlink_article = 'http://www.ipol.im/pub/art/2013/41/'

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
        tgz_url = "http://www.ipol.im/pub/art/2013/41/selective_ipol.tgz"
        tgz_file = self.dl_dir + "selective_ipol.tgz"
        prog_file = self.bin_dir + "poisson_lca"
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
            build.run("make -j4 -C %s poisson_lca"
                      % (self.src_dir + "selective_ipol"),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir 
                  + os.path.join("selective_ipol", "poisson_lca"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


    #
    # PARAMETER HANDLING
    #
    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, T="50", a="3.0", alpha="0.8"):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

        return self.tmpl_out("params.html", msg=msg, T=T, a=a, alpha=alpha)


    @cherrypy.expose
    @init_app
    def wait(self, T="50", a="3.0", alpha="0.8"):
        """
        params handling and run redirection
        """
        try:
            self.cfg['param'] = {'t' : int(T),
                                 'a' : float(a),
                                 'alpha' : float(alpha)}
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
        T = self.cfg['param']['t']
        a = self.cfg['param']['a']
        alpha = self.cfg['param']['alpha']
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(T, a, alpha, stdout=stdout, timeout=self.timeout)
            self.cfg['info']['run_time'] = time.time() - run_time
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
            ar.add_file("output_normI.png", info="normalized (I)")
            ar.add_file("output_darkI.png", info="enhanced dark regions (I)")
            ar.add_file("output_powerI.png", info="global enhancement (I)")
            ar.add_file("output_normRGB.png", info="normalized (RGB)")
            ar.add_file("output_darkRGB.png", 
                        info="enhanced dark regions (RGB)")
            ar.add_file("output_powerRGB.png", 
                        info="global enhancement (RGB)")
            ar.add_info({"t": T, "a": a, "alpha":alpha})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, T, a, alpha, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        p = self.run_proc(['poisson_lca', '-t', str(T), '-a', str(a), 
                           '-b', str(alpha), 'input_0.png',
                           'output_normI.png', 'output_darkI.png', 
                           'output_powerI.png',
                           'output_normRGB.png', 'output_darkRGB.png', 
                           'output_powerRGB.png'],
                           stdout=None, stderr=None)
        self.wait_proc(p, timeout)
      
        #check if input image is monochrome
        isGray = check_grayimage(self.work_dir + 'input_0.png')
        self.cfg['param']['isgray'] = isGray

        #Compute histograms of images
        im0 = image(self.work_dir + 'input_0.png')
        imI = image(self.work_dir + 'output_normI.png')
        imdI = image(self.work_dir + 'output_darkI.png')
        impI = image(self.work_dir + 'output_powerI.png')
        if not isGray:
            imRGB = image(self.work_dir + 'output_normRGB.png')
            imdRGB = image(self.work_dir + 'output_darkRGB.png')
            impRGB = image(self.work_dir + 'output_powerRGB.png')
        #compute maximum of histogram values
        maxH = im0.max_histogram(option="all")
        #draw all the histograms using the same reference maximum
        im0.histogram(option="all", maxRef=maxH)
        im0.save(self.work_dir + 'input_0_hist.png')
        imI.histogram(option="all", maxRef=maxH)
        imI.save(self.work_dir + 'output_normI_hist.png')
        imdI.histogram(option="all", maxRef=maxH)
        imdI.save(self.work_dir + 'output_darkI_hist.png')
        impI.histogram(option="all", maxRef=maxH)
        impI.save(self.work_dir + 'output_powerI_hist.png')
        if not isGray:
            imRGB.histogram(option="all", maxRef=maxH)
            imRGB.save(self.work_dir + 'output_normRGB_hist.png')
            imdRGB.histogram(option="all", maxRef=maxH)
            imdRGB.save(self.work_dir + 'output_darkRGB_hist.png')
            impRGB.histogram(option="all", maxRef=maxH)
            impRGB.save(self.work_dir + 'output_powerRGB_hist.png')


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        # read the parameters
        T = self.cfg['param']['t']
        a = self.cfg['param']['a']
        alpha = self.cfg['param']['alpha']
        isGray = self.cfg['param']['isgray']
        
        print 'isGray:'
        print isGray
      
        sizeY = image(self.work_dir + 'input_0.png').size[1]
        sizeYhist = image(self.work_dir + 'input_0_hist.png').size[1]
        # add 20 pixels to the histogram size to take margin into account
        sizeYmax = max(sizeY, sizeYhist+60)
        
        return self.tmpl_out("result.html", T=T, a=a, alpha=alpha, 
                             isGray=isGray,
                             sizeY="%i" % sizeYmax)



