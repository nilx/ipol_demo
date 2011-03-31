"""
Linear Methods for Image Interpolation ipol demo web app
"""
# pylint: disable-msg=R0904,C0103

from lib import base_app, build, http
from lib.misc import ctime
from lib.base_app import init_app
from lib.config import cfg_open
import shutil
import cherrypy
from cherrypy import TimeoutError
from lib import image
import math
import os.path
import time
import string

class app(base_app):
    """ Linear Methods for Image Interpolation app """

    title = 'Linear Methods for Image Interpolation'

    input_nb = 1
    input_max_pixels = 1048576          # max size (in pixels) input image
    input_max_weight = 3 * 1024 * 1024  # max size (in bytes) input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False    
    
    # List of methods in the order in which they are to be displayed
    methodtitles = ['Bilinear', 'Bicubic', 'Fourier', 
        'Lanczos 2', 'Lanczos 3', 'Lanczos 4', 
        'B-Spline 2', 'B-Spline 3', 'B-Spline 5', 
        'B-Spline 7', 'B-Spline 9', 'B-Spline 11', 
        'o-Moms 3', 'o-Moms 5', 'Schaum 2', 'Schaum 3']    
    # For display in params.html
    methodcolumnbreaks = ['Lanczos 2', 'B-Spline 2', 'o-Moms 3']
    # The method identifier (lowercase with no spaces, dashes, etc.)
    methodidentifiers = [m.lower().translate(string.maketrans('', ''), ' -/&') 
        for m in methodtitles]
    # Make a list of dictionaries 
    methods = [{'title' : m, 'identifier' : mid} 
        for m, mid in zip(methodtitles, methodidentifiers)]
    
    # These methods are selected by default
    defaultselected = ['bilinear', 'bicubic', 'fourier', 
        'lanczos3', 'bspline3', 'omoms3']
    
    # Default parameters
    default_param = dict(
            [(m, str(m in defaultselected)) for m in methodidentifiers] +
            {'scalefactor': 4,  
             'psfsigma'   : 0.6,
             'grid'       : 'centered',
             'boundary'   : 'hsym',
             'action'     : 'Interpolate image',             
             'x0': None,
             'y0': None,
             'x' : None,
             'y' : None}.items())

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
        # Generate a new timestamp
        self.timestamp = int(100*time.time())        

    def build(self):
        """
        Program build/update
        """
        # Store common file path in variables
        tgz_url = 'http://www.ipol.im/pub/algo/' \
            + 'g_linear_methods_for_image_interpolation/src.tar.gz'
        tgz_file = self.dl_dir + 'src.tar.gz'
        progs = ['linterp', 'imcoarsen', 'imdiff']
        sub_dir = 'linterp-src'
        src_bin = dict([(self.src_dir + os.path.join(sub_dir, prog),
                         self.bin_dir + prog)
                        for prog in progs])
        log_file = self.base_dir + 'build.log'
        # Get the latest source archive
        build.download(tgz_url, tgz_file)
        # Test if any dest file is missing, or too old
        if all([(os.path.isfile(bin_file)
                 and ctime(tgz_file) < ctime(bin_file))
                for bin_file in src_bin.values()]):
            cherrypy.log('not rebuild needed',
                         context='BUILD', traceback=False)
        else:
            # Extract the archive
            build.extract(tgz_file, self.src_dir)
            # Build the programs
            build.run("make -C %s %s"
                % (self.src_dir + sub_dir, " ".join(progs))
                + " --makefile=makefile.gcc"
                + " CXX='ccache c++' -j4", stdout=log_file)
            # Save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for (src, dst) in src_bin.items():
                shutil.copy(src, dst)
            # Cleanup the source dir
            shutil.rmtree(self.src_dir)
        return
    
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
        
        self.cfg.save()
        return self.tmpl_out('params.html')

    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        Params handling and run redirection
        """
        
        # Read webpage parameters from kwargs, but only those that 
        # are defined in the default_param dict.  If a parameter is not
        # defined by kwargs, the value from default_param is used.
        # However, if a method ID is not in kwargs, it should be false.
        self.cfg['param'] = self.default_param.copy()
        
        for k in self.default_param.keys():
            if k in self.methodidentifiers:
                self.cfg['param'][k] = str(k in kwargs and \
                    kwargs[k].lower() in ['true', 'on', 'yes', 'checked', '1'])
            elif k in kwargs:
                self.cfg['param'][k] = kwargs[k]
            
        # If no method has been selected, just do bicubic
        if all([self.cfg['param'][k] == 'False' \
            for k in self.methodidentifiers]):
            self.cfg['param']['bicubic'] = 'True'
            
        # Generate a new timestamp
        self.timestamp = int(100*time.time())
                        
        # Validate scalefactor and psfsigma
        if not (1 <= float(self.cfg['param']['scalefactor']) <= 8) \
            or not (0 <= float(self.cfg['param']['psfsigma']) <= 1):
            return self.error(errcode='badparams') 
        
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
                    img.draw_cross((x0, y0), size=4, color="white")
                    img.draw_cross((x0, y0), size=2, color="red")
                else:
                    # (x,y) specifies the second corner
                    (x0, x) = sorted((int(x0), int(x)))
                    (y0, y) = sorted((int(y0), int(y)))
                    assert (x - x0) > 0 and (y - y0) > 0
                    # Crop the image
                    img.crop((x0, y0, x, y))
                    
                img.save(self.work_dir + 'input_0_sel.png')
                self.cfg['param']['x0'] = x0
                self.cfg['param']['y0'] = y0
                self.cfg['param']['x'] = x
                self.cfg['param']['y'] = y
                
            self.cfg.save()
            return self.tmpl_out('params.html')
        else:
            if any(self.cfg['param'][k] == None \
                for k in ['x0', 'y0', 'x', 'y']):
                img0 = image(self.work_dir + 'input_0.png')
                img0.save(self.work_dir + 'input_0_sel.png')
            
            self.cfg.save()
            http.refresh(self.base_url + 'run?key=%s' % self.key)            
            return self.tmpl_out("wait.html")


    @cherrypy.expose
    @init_app
    def run(self):
        """
        Algorithm execution
        """
        
        try:
            self.run_algo(stdout=open(self.work_dir + 'stdout.txt', 'w'))
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # Archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file('input_0_sel.png', info='Selected subimage')
            ar.add_info({'action': self.cfg['param']['action'], 
                'scalefactor': self.cfg['param']['scalefactor'], 
                'psfsigma': self.cfg['param']['psfsigma']})
            
            if self.cfg['param']['action'] == self.default_param['action']:
                # "Interpolate directly"
                for m in self.methods:
                    if str(self.cfg['param'][m['identifier']]) == 'True':
                        ar.add_file('interp_' + m['identifier'] + '.png', 
                        info=m['title'])
            else:
                # "Coarsen, interpolate, and compare"
                ar.add_file('coarsened.png', info='Coarsened image')
                ar.add_file('smoothed.png', info='Smoothed image')
                
                # Save the interpolations and PSNR and MSSIM metrics
                for m in self.methods:
                    if str(self.cfg['param'][m['identifier']]) == 'True':
                        ar.add_file('interp_' + m['identifier'] + '.png', 
                        info=('%s (PSNR %.2f, MSSIM %.4f)' % (m['title'], 
                        self.cfg['param'][m['identifier'] + '_psnr'],
                        self.cfg['param'][m['identifier'] + '_mssim'])))
            
            ar.save()

        return self.tmpl_out("run.html")


    def run_algo(self, stdout=None):
        """
        The core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        
        timeout = False
        scalefactor = float(self.cfg['param']['scalefactor'])
        runmethods = [m for m in self.methodidentifiers if
            str(self.cfg['param'][m]) == 'True']
        img = image(self.work_dir + 'input_0_sel.png')
        (sizeX, sizeY) = img.size
        
        if self.cfg['param']['action'] == self.default_param['action']:
            # In this run mode, the interpolation is performed directly on the
            # selected image.
            
            # If the image dimensions are small, zoom the displayed results.
            # This value is always at least 1.
            displayzoom = int(math.ceil(400.0/(scalefactor*max(sizeX, sizeY))))
            # Check that interpolated image dimensions are not too large
            cropsize = (min(sizeX, int(500/scalefactor)),
                min(sizeY, int(500/scalefactor)))
            
            if (sizeX, sizeY) != cropsize:
                (x0, y0) = (int(math.floor((sizeX - cropsize[0])/2)),
                    int(math.floor((sizeY - cropsize[1])/2)))
                img.crop((x0, y0, x0 + cropsize[0], y0 + cropsize[1]))
                img.save(self.work_dir + 'input_0_sel.png')
            
            self.wait_proc(
                # Perform the interpolations
                [self.run_proc(['linterp', 
                    '-g', self.cfg['param']['grid'],
                    '-b', self.cfg['param']['boundary'],
                    '-p', '0',
                    '-x', str(scalefactor),
                    '-m', m,
                    'input_0_sel.png', 'interp_' + m + '.png'],
                    stdout=stdout, stderr=stdout)
                    for m in runmethods] +
                # For display, create a nearest neighbor zoomed version of the
                # input. nninterp does nearest neighbor interpolation on 
                # precisely the same grid so that displayed images are aligned.
                [self.run_proc(['linterp',
                    '-m', 'nearest',
                    '-g', 'centered',
                    '-x', str(scalefactor*displayzoom),
                    'input_0_sel.png', 'input_zoom.png'],
                    stdout=stdout, stderr=stdout)
                ], timeout)
        else:
            # In this run mode, the selected image is coarsened, interpolated
            # and compared with the original.
            
            # If the image dimensions are small, zoom the displayed results.
            # This value is always at least 1.
            displayzoom = int(math.ceil(350.0/max(sizeX, sizeY)))
            displaysize = (displayzoom*sizeX, displayzoom*sizeY)
            
            # Coarsen the image
            self.wait_proc(
                self.run_proc(['imcoarsen', 
                    '-g', self.cfg['param']['grid'],
                    '-p', str(self.cfg['param']['psfsigma']),
                    '-x', str(scalefactor),
                    'input_0_sel.png', 'coarsened.png'],
                    stdout=stdout, stderr=stdout), timeout)
                        
            self.wait_proc(
                # Perform the interpolations
                [self.run_proc(['linterp', 
                    '-g', self.cfg['param']['grid'],
                    '-b', self.cfg['param']['boundary'],
                    '-p', '0',
                    '-x', str(scalefactor),
                    '-m', m,
                    'coarsened.png', 'interp_' + m + '.png'],
                    stdout=stdout, stderr=stdout)
                    for m in runmethods] +
                # Compute the image smoothed but not downsampled
                [self.run_proc(['imcoarsen', 
                    '-g', self.cfg['param']['grid'],
                    '-p', str(scalefactor*float(self.cfg['param']['psfsigma'])),
                    '-x', '1',
                    'input_0_sel.png', 'smoothed.png'],
                    stdout=stdout, stderr=stdout),
                # For display, create a nearest neighbor zoomed version of the
                # input. nninterp does nearest neighbor interpolation on 
                # precisely the same grid so that displayed images are aligned.
                self.run_proc(['linterp',
                    '-m', 'nearest',
                    '-g', 'centered',
                    '-x', str(scalefactor*displayzoom),
                    'coarsened.png', 'input_zoom.png'],
                    stdout=stdout, stderr=stdout)], timeout)
            
            # Because of rounding, the interpolated image dimensions might be 
            # slightly larger than the original image.  For example, if the 
            # input is 100x100 and the scale factor is 3, then the coarsened 
            # image has size 34x34, and the interpolation has size 102x102.
            # The following crops the results if necessary.
            for m in runmethods:
                f = self.work_dir + 'interp_' + m + '.png'
                img = image(f)
                
                if (sizeX, sizeY) != img.size:
                    img.crop((0, 0, sizeX, sizeY))
                    img.save(f)
            
            # Crop input_zoom.png if necessary.
            img = image(self.work_dir + 'input_zoom.png')
            
            if displaysize != img.size:
                img.crop((0, 0, displaysize[0], displaysize[1]))
                img.save(self.work_dir + 'input_zoom.png')
            
            # Compute metrics, the results are saved in files metrics_*.txt
            self.wait_proc(
                [self.run_proc(['imdiff',
                    'smoothed.png', 'interp_' + m + '.png'],
                    stdout=open(self.work_dir 
                    + 'metrics_' + m + '.txt', 'w'), stderr=None)
                for m in runmethods], timeout)
            
            # Read the metrics_*.txt files
            for m in runmethods:
                f = open(self.work_dir 
                    + 'metrics_' + m + '.txt', 'r')
                self.cfg['param'][m + '_maxdiff'] = \
                    float(f.readline().split(':',1)[1])
                self.cfg['param'][m + '_psnr'] = \
                    round(float(f.readline().split(':',1)[1]),2)
                self.cfg['param'][m + '_mssim'] = \
                    round(float(f.readline().split(':',1)[1]),4)
                f.close()
            
            # Determine for each metric the best value
            self.cfg['param']['best_maxdiff'] = \
                min([self.cfg['param'][m + '_maxdiff'] for m in runmethods])
            self.cfg['param']['best_psnr'] = \
                max([self.cfg['param'][m + '_psnr'] for m in runmethods])
            self.cfg['param']['best_mssim'] = \
                max([self.cfg['param'][m + '_mssim'] for m in runmethods])
            
            # Zoom input_0_sel.png and smoothed.png for display
            if displayzoom > 1:
                self.wait_proc(                
                    [self.run_proc(['linterp',
                        '-m', 'nearest',
                        '-g', 'centered',
                        '-x', str(displayzoom),
                        'input_0_sel.png', 'input_0_sel_zoom.png'],
                        stdout=stdout, stderr=stdout),
                    self.run_proc(['linterp',
                        '-m', 'nearest',
                        '-g', 'centered',
                        '-x', str(displayzoom),
                        'smoothed.png', 'smoothed_zoom.png'],
                        stdout=stdout, stderr=stdout)], timeout)

        # Zoom the interpolations for display
        if displayzoom > 1:
            self.wait_proc(
                [self.run_proc(['linterp', 
                    '-m', 'nearest',
                    '-g', 'centered',
                    '-x', str(displayzoom),
                    'interp_' + m + '.png', 
                    'interp_' + m + '_zoom.png'],
                    stdout=stdout, stderr=stdout)
                    for m in runmethods
                ], timeout)
                
        self.cfg['param']['displayzoom'] = displayzoom
        self.cfg.save()
        return

    @cherrypy.expose
    @init_app
    def result(self, public=None):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        return self.tmpl_out('result.html',
            displaysize=image(self.work_dir + 'input_zoom.png').size,
            stdout=open(self.work_dir 
                        + 'stdout.txt', 'r').read())
