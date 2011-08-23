"""
Roussos-Maragos Image Interpolation ipol demo web app
"""

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


class app(base_app):
    """ Roussos-Maragos Image Interpolation app """

    title = 'Roussos-Maragos Image Interpolation'

    input_nb = 1
    input_max_pixels = 1048576          # max size (in pixels) input image
    input_max_weight = 3 * 1024 * 1024  # max size (in bytes) input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False    
    default_param = {'scalefactor': 4,  # default parameters
             'psfsigma' : 0.35,
             'action' : 'Interpolate image',             
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
        # Generate a new timestamp
        self.timestamp = int(100*time.time())


    def build(self):
        """
        program build/update
        """
        # store common file path in variables
        tgz_url = 'http://www.ipol.im/pub/algo/' \
            + 'g_roussos_diffusion_interpolation/src.tar.gz'
        tgz_file = self.dl_dir + 'src.tar.gz'
        progs = ['tdinterp', 'imcoarsen', 'imdiff', 'nninterp']
        sub_dir = 'tdinterp-src'
        src_bin = dict([(self.src_dir + os.path.join(sub_dir, prog),
                         self.bin_dir + prog)
                        for prog in progs])
        log_file = self.base_dir + 'build.log'
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if any dest file is missing, or too old
        if all([(os.path.isfile(bin_file)
                 and ctime(tgz_file) < ctime(bin_file))
                for bin_file in src_bin.values()]):
            cherrypy.log('not rebuild needed',
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the programs
            build.run("make -C %s %s"
                % (self.src_dir + sub_dir, " ".join(progs))
                + " --makefile=makefile.gcc"
                + " CXX='ccache c++' -j4", stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for (src, dst) in src_bin.items():
                shutil.copy(src, dst)
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
        
        self.cfg.save()
        return self.tmpl_out('params.html')


    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        Params handling and run redirection
        as a special case, we have no parameter to check and pass
        """

        # Read webpage parameters from kwargs, but only those that 
        # are defined in the default_param dict.  If a parameter is not
        # defined by kwargs, the value from default_param is used.
        self.cfg['param'] = dict(self.default_param.items() + 
            [(p,kwargs[p]) for p in self.default_param.keys() if p in kwargs])
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
                
            self.cfg.save()
            return self.tmpl_out('params.html')
        else:
            if any(self.cfg['param'][p] == None \
                for p in ['x0', 'y0', 'x', 'y']):
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
            ar.add_file('input_0.png', 'input.png')
            ar.add_file('input_0_sel.png', info='Selected subimage')
            ar.add_file('interpolated.png', 
                info='Roussos-Maragos Interpolation')
            ar.add_file('fourier.png', info='Fourier Interpolation') 
            ar.add_info({'action': self.cfg['param']['action'], 
                'scalefactor': self.cfg['param']['scalefactor'], 
                'psfsigma': self.cfg['param']['psfsigma']})
                
            if self.cfg['param']['action'] != self.default_param['action']:
                ar.add_file('coarsened.png', info='Coarsened image')
                ar.add_file('coarsened_zoom.png')
                ar.add_file('difference.png', info='Difference image')
            else:
                ar.add_file('input_0_zoom.png')
                        
            ar.save()

        return self.tmpl_out('run.html')


    def run_algo(self, stdout=None):
        """
        The core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        
        timeout = False
        scalefactor = float(self.cfg['param']['scalefactor'])
        img = image(self.work_dir + 'input_0_sel.png')
        (sizeX, sizeY) = img.size
        p = {}
        
        if self.cfg['param']['action'] == self.default_param['action']:
            # In this run mode, the interpolation is performed directly on the
            # selected image, and the estimated contours are also shown.
            
            # If the image dimensions are small, zoom the displayed results.
            # This value is always at least 1.
            displayzoom = int(math.ceil(400.0/(scalefactor*max(sizeX, sizeY))))
            # Check that interpolated image dimensions are not too large
            cropsize = (min(sizeX, int(400/scalefactor)),
                min(sizeY, int(400/scalefactor)))
            
            if (sizeX, sizeY) != cropsize:
                (x0, y0) = (int(math.floor((sizeX - cropsize[0])/2)),
                    int(math.floor((sizeY - cropsize[1])/2)))
                img.crop((x0, y0, x0 + cropsize[0], y0 + cropsize[1]))
                img.save(self.work_dir + 'input_0_sel.png')
            
            p = {
                # Perform the actual contour stencil interpolation
                'interp' : 
                    self.run_proc(['tdinterp',
                    '-x', str(scalefactor), 
                    '-p', str(self.cfg['param']['psfsigma']),
                    'input_0_sel.png', 'interpolated.png'],
                    stdout=stdout, stderr=stdout),
                    
                # Interpolate with Fourier
                'finterp' : 
                    self.run_proc(['tdinterp', '-N0', 
                    '-x', str(scalefactor), 
                    '-p', str(self.cfg['param']['psfsigma']),
                    'input_0_sel.png', 'fourier.png'],
                    stdout=stdout, stderr=stdout),
                    
                # For display, create a nearest neighbor zoomed version of the
                # input. nninterp does nearest neighbor interpolation on 
                # precisely the same grid so that displayed images are aligned.
                'inputzoom' : 
                    self.run_proc(['nninterp',
                    '-g', 'centered',
                    '-x', str(scalefactor*displayzoom), 
                    'input_0_sel.png', 'input_0_zoom.png'],
                    stdout=stdout, stderr=stdout)
                }
            
            if displayzoom > 1:
                self.wait_proc(p.values(), timeout)
                self.wait_proc([self.run_proc(['nninterp',
                        '-g', 'centered',
                        '-x', str(displayzoom), 
                        'interpolated.png', 'interpolated_zoom.png'],
                        stdout=stdout, stderr=stdout),
                    self.run_proc(['nninterp',
                        '-g', 'centered',
                        '-x', str(displayzoom), 
                        'fourier.png', 'fourier_zoom.png'],
                        stdout=stdout, stderr=stdout)], timeout)
        else:
            # In this run mode, the selected image is coarsened, interpolated
            # and compared with the original.
            
            # Check that interpolated image dimensions are not too large
            cropsize = (min(sizeX, 400), min(sizeY, 400))
            
            if (sizeX, sizeY) != cropsize:
                (x0, y0) = (int(math.floor((sizeX - cropsize[0])/2)),
                    int(math.floor((sizeY - cropsize[1])/2)))
                img.crop((x0, y0, x0 + cropsize[0], y0 + cropsize[1]))
                img.save(self.work_dir + 'input_0_sel.png')
                (sizeX, sizeY) = cropsize
            
            # If the image dimensions are small, zoom the displayed results.
            # This value is always at least 1.
            displayzoom = int(math.ceil(350.0/max(sizeX, sizeY)))
            
            # Coarsen the image
            p['coarsened'] = self.run_proc(['imcoarsen', 
                '-g', 'topleft',
                '-x', str(scalefactor), 
                '-p', str(self.cfg['param']['psfsigma']),
                'input_0_sel.png', 'coarsened.png'])
            
            if displayzoom > 1:
                p['exactzoom'] = self.run_proc(['nninterp',
                    '-g', 'centered',
                    '-x', str(displayzoom), 
                    'input_0_sel.png', 'input_0_sel_zoom.png'],
                    stdout=stdout, stderr=stdout)
            
            # Perform the actual interpolation
            self.wait_proc(p['coarsened'], timeout)
            p['interpolated'] = self.run_proc(['tdinterp', 
                '-x', str(scalefactor), 
                '-p', str(self.cfg['param']['psfsigma']),
                'coarsened.png', 'interpolated.png'],
                stdout=stdout, stderr=stdout)
            
            # Interpolate with Fourier
            p['fourier'] = self.run_proc(['tdinterp', '-N0',
                '-x', str(scalefactor), 
                '-p', str(self.cfg['param']['psfsigma']),
                'coarsened.png', 'fourier.png'],
                stdout=stdout, stderr=stdout)

            # For display, create a nearest neighbor zoomed version of the
            # coarsened image.  nninterp does nearest neighbor interpolation 
            # on precisely the same grid as cwinterp so that displayed images
            # are aligned.
            p['coarsened_zoom'] = self.run_proc(['nninterp',
                '-g', 'topleft',
                '-x', str(scalefactor), 
                'coarsened.png', 'coarsened_zoom.png'],
                stdout=stdout, stderr=stdout)
                        
            # Because of rounding, the interpolated image dimensions might be 
            # slightly larger than the original image.  For example, if the 
            # input is 100x100 and the scale factor is 3, then the coarsened 
            # image has size 34x34, and the interpolation has size 102x102.
            # The following crops the results if necessary.
            for f in ['coarsened_zoom', 'interpolated', 'fourier']:
                self.wait_proc(p[f], timeout)
                img = image(self.work_dir + f + '.png')
                
                if (sizeX, sizeY) != img.size:
                    img.crop((0, 0, sizeX, sizeY))
                    img.save(self.work_dir + f + '.png')
                        
            # Generate difference image
            p['difference'] = self.run_proc(['imdiff', 
                'input_0_sel.png', 'interpolated.png', 'difference.png'],
                stdout=stdout, stderr=stdout)
            p['fdifference'] = self.run_proc(['imdiff', 
                'input_0_sel.png', 'fourier.png', 'fdifference.png'],
                stdout=stdout, stderr=stdout)
            # Compute maximum difference, PSNR, and MSSIM
            p['metrics'] = self.run_proc(['imdiff', 
                'input_0_sel.png', 'interpolated.png'],
                stdout=stdout, stderr=stdout)
            
            if displayzoom > 1:
                p['coarsened_zoom2'] = self.run_proc(['nninterp',
                    '-g', 'centered',
                    '-x', str(displayzoom), 
                    'coarsened_zoom.png', 'coarsened_zoom.png'],
                    stdout=stdout, stderr=stdout)
                
                for f in ['interpolated', \
                    'fourier', 'difference', 'fdifference']:
                    self.wait_proc(p[f], timeout)
                    p[f + '_zoom'] = self.run_proc(['nninterp',
                        '-g', 'centered',
                        '-x', str(displayzoom), 
                        f + '.png', f + '_zoom.png'],
                        stdout=stdout, stderr=stdout)                
        
        self.cfg['param']['displayzoom'] = displayzoom
        self.cfg.save()
        # Wait for all processes to complete 
        self.wait_proc(p.values(), timeout)
        return

    @cherrypy.expose
    @init_app
    def result(self, public=None):
        """
        Display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        self.timestamp = int(100*time.time())
        return self.tmpl_out("result.html",                           
            height = max(185,image(self.work_dir + 'interpolated.png').size[1]
                * self.cfg['param']['displayzoom']),
            stdout = open(self.work_dir + 'stdout.txt', 'r').read())
