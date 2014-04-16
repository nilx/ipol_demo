"""
multiscale retinex ipol demo web app
"""

from lib import base_app, build, http, image
from lib.misc import ctime
from lib.base_app import init_app
from lib.config import cfg_open
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
    """ multiscale_retinex app """

    title = "Multiscale Retinex"

    input_nb = 1
    input_max_pixels = 700 * 700 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = False
    timestamp = None

    xlink_article = 'http://www.ipol.im/pub/pre/107/'
    xlink_src     = "http://www.ipol.im/pub/pre/107/MSR_original.tgz"

    default_param = {
      'low_scale': '15',
      'medium_scale': '80',
      'high_scale': '250',
      'prc_left': '1.0',
      'prc_right': '1.0',
      'x0': None,
      'y0': None,
      'x' : None,
      'y' : None}

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
        tgz_url = self.xlink_src
        tgz_file = self.dl_dir + "MSR_original.tgz"
        prog_file = self.bin_dir + "MSR_original"
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
            build.run("make -j4 -C %s MSR_original"
                      % (self.src_dir + "MSR_original"),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir 
                  + os.path.join("MSR_original", "MSR_original"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


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
            shutil.copy(old_work_dir + 'input_0_sel.png',
                self.work_dir + 'input_0_sel.png')

        # Set undefined parameters to default values
        self.cfg['param'] = dict(self.default_param, **self.cfg['param'])
        # Generate a new timestamp
        self.timestamp = int(100*time.time())
        
        # Reset cropping parameters if running with a different subimage
        if msg == 'different subimage':
            self.cfg['param']['x0'] = None
            self.cfg['param']['y0'] = None
            self.cfg['param']['x'] = None
            self.cfg['param']['y'] = None
        
        return self.tmpl_out('params.html')


    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        Run redirection
        """
        
        # Read webpage parameters from kwargs, but only those that 
        # are defined in the default_param dict.  If a parameter is not
        # defined by kwargs, the value from default_param is used.
        self.cfg['param'] = dict(self.default_param.items() + 
            [(p,kwargs[p]) for p in self.default_param.keys() if p in kwargs])
            
        # Generate a new timestamp
        self.timestamp = int(100*time.time())
        
        if not 'action' in kwargs:
            # Select a subimage
            x = self.cfg['param']['x']
            y = self.cfg['param']['y']
            x0 = self.cfg['param']['x0']
            y0 = self.cfg['param']['y0']
            
            if x != None and y != None:
                img = image(self.work_dir + 'input_0.png')
                
                if x0 == None or y0 == None:
                    # (x,y) specifies the first corner
                    (x0, y0, x, y) = (int(x), int(y), None, None)
                    # Draw a cross at the first corner
                    img.draw_cross((x0, y0), size=4, color='white')
                    img.draw_cross((x0, y0), size=2, color='red')
                else:
                    # (x,y) specifies the second corner
                    (x0, x) = sorted((int(x0), int(x)))
                    (y0, y) = sorted((int(y0), int(y)))
                    assert (x - x0) > 0 and (y - y0) > 0
                    
                    # Crop the image
                    # Check if the original image is a different size, which is
                    # possible if the input image is very large.
                    imgorig = image(self.work_dir + 'input_0.orig.png')
                    
                    if imgorig.size != img.size:                        
                        s = float(imgorig.size[0])/float(img.size[0])
                        imgorig.crop(tuple([int(s*v) for v in (x0, y0, x, y)]))
                        img = imgorig
                    else:
                        img.crop((x0, y0, x, y))
                    
                img.save(self.work_dir + 'input_0_sel.png')
                self.cfg['param']['x0'] = x0
                self.cfg['param']['y0'] = y0
                self.cfg['param']['x'] = x
                self.cfg['param']['y'] = y
            
            return self.tmpl_out('params.html')
        else:
            if any(self.cfg['param'][p] == None \
                for p in ['x0', 'y0', 'x', 'y']):
                img0 = image(self.work_dir + 'input_0.png')
                img0.save(self.work_dir + 'input_0_sel.png')
            
            http.refresh(self.base_url + 'run?key=%s' % self.key)            
            return self.tmpl_out("wait.html")


    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(stdout=stdout, timeout=self.timeout)
            self.cfg['info']['run_time'] = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_info({"low_scale": self.cfg['param']['low_scale'], 
                         "medium_scale": self.cfg['param']['medium_scale'],
                         "high_scale": self.cfg['param']['high_scale'],
                         "prc_left": self.cfg['param']['prc_left'],
                         "prc_right": self.cfg['param']['prc_right']})
            ar.add_file("input_0.orig.png", info="uploaded image")
            ar.add_file("input_0.png", info="original image")
            ar.add_file("input_0_sel.png", info="selected subimage")
            ar.add_file("output_I.png", info="multiscale retinex on I channel")
            if not self.cfg['param']['isgray']:
                ar.add_file("output_RGB.png", \
                            info="multiscale retinex on R, G and B channels")
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        low_scale = self.cfg['param']['low_scale']
        medium_scale = self.cfg['param']['medium_scale']
        high_scale = self.cfg['param']['high_scale']
        prc_left = self.cfg['param']['prc_left']
        prc_right = self.cfg['param']['prc_right']
      
        (sizeX, sizeY) = image(self.work_dir + 'input_0_sel.png').size
      
        max_scale = int(min(sizeX, sizeY)/2)
        if low_scale > max_scale:
            low_scale = max_scale
        if medium_scale > max_scale:
            medium_scale = max_scale
        if high_scale > max_scale:
            high_scale = max_scale
          
        self.cfg['param']['low_scale'] = low_scale      
        self.cfg['param']['medium_scale'] = medium_scale      
        self.cfg['param']['high_scale'] = high_scale      
      
        p = self.run_proc(['MSR_original', 
                           '-S', '3', 
                           '-L', str(low_scale), 
                           '-M', str(medium_scale), 
                           '-H', str(high_scale), 
                           '-N', '1', 
                           '-l', str(prc_left), 
                           '-R', str(prc_right), 
                           'input_0_sel.png',
                           'output_RGB.png', 
                           'output_I.png'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc(p, timeout)
      
        #check if input image is monochrome
        isGray = check_grayimage(self.work_dir + 'input_0_sel.png')
        self.cfg['param']['isgray'] = isGray

        #Compute histograms of images
        im0 = image(self.work_dir + 'input_0_sel.png')
        imI = image(self.work_dir + 'output_I.png')
        if not isGray:
            imRGB = image(self.work_dir + 'output_RGB.png')
        #compute maximum of histogram values
        maxH = im0.max_histogram(option="all")
        #draw all the histograms using the same reference maximum
        im0.histogram(option="all", maxRef=maxH)
        im0.save(self.work_dir + 'input_0_sel_hist.png')
        imI.histogram(option="all", maxRef=maxH)
        imI.save(self.work_dir + 'output_I_hist.png')
        if not isGray:
            imRGB.histogram(option="all", maxRef=maxH)
            imRGB.save(self.work_dir + 'output_RGB_hist.png')

        sizeYhist = image(self.work_dir + 'input_0_sel_hist.png').size[1]
        # add 60 pixels to the histogram size to take margin into account
        sizeYmax = max(sizeY, sizeYhist+60)
          
        self.cfg['param']['displayheight'] = sizeYmax
        self.cfg['param']['stdout'] = \
            open(self.work_dir + 'stdout.txt', 'r').read()
          
          


