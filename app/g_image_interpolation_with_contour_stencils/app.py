"""
cwinterp ipol demo web app
"""

from lib import base_app, build, http
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
from lib import image
import math
import os.path
import time


class app(base_app):
    """ cwinterp app """

    title = "Image Interpolation with Line-Shaped Contour Stencils"

    input_nb = 1
    input_max_pixels = 1048576 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
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
        # store common file path in variables
        tgz_url = 'https://edit.ipol.im/pub/algo/' \
            + 'g_image_interpolation_with_contour_stencils/src.tar.gz'
        tgz_file = self.dl_dir + 'src.tar.gz'
        progs = ['cwinterp', 'imcoarsen', 'imdiff', 'nninterp']
        sub_dir = 'cwinterp-src'
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
            
    def cropimage(self, x, y, x0, y0, cropped):
        """
        Select a subimage from original image
        """
        img = image(self.work_dir + 'input_0.png')
        
        if not (x0 and y0):            
            # (x,y) specifies the first corner
            (x0, y0) = (int(x), int(y))
            (x1, y1) = (None, None)            
            # Draw a cross at the first corner            
            img.draw_cross((x0, y0), size=4, color="white")
            img.draw_cross((x0, y0), size=2, color="red")
            self.cfg['param']['x0'] = x0
            self.cfg['param']['y0'] = y0
        else:
            # (x,y) specifies the second corner
            (x0, x1) = (min(int(x0), int(x)), max(int(x0), int(x)))
            (y0, y1) = (min(int(y0), int(y)), max(int(y0), int(y)))
            assert (x1 - x0) > 0 and (y1 - y0) > 0
            # Crop the image
            img.crop((x0, y0, x1, y1))
            self.cfg['param']['cropped'] = 'true'
                    
        self.cfg.save()
        img.save(self.work_dir + 'input_0_sel.png')
        return self.tmpl_out("params.html")


    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, scalefactor='4', psfsigma='0.35', cropped='false'):
        """
        configure the algo execution
        """
        if newrun:
            old_work_dir = self.work_dir
            self.clone_input()
            # Also need to clone input_0_sel.png in case the user is running
            # with new parameters but on the same subimage.
            shutil.copy(old_work_dir + 'input_0_sel.png',
                self.work_dir + 'input_0_sel.png')
        
        self.cfg['param'] = {
           'scalefactor': scalefactor,
           'psfsigma': psfsigma,
           'cropped': cropped}
        self.timestamp = int(time.time())
            
        return self.tmpl_out("params.html")


    @cherrypy.expose
    @init_app
    def wait(self, action=None, scalefactor=4, psfsigma=0.35, x=None, y=None, x0=None, y0=None, cropped='false'):
        """
        params handling and run redirection
        as a special case, we have no parameter to check and pass
        """

        self.cfg['param']['scalefactor'] = scalefactor
        self.cfg['param']['psfsigma'] = psfsigma
        self.cfg['param']['cropped'] = cropped
        self.timestamp = int(time.time())
        
        if action == None:
            return self.cropimage(x, y, x0, y0, cropped)
        else:
            self.cfg['param']['alg_action'] = action
            self.cfg.save()
            
            if (not self.cfg['param']['cropped']) or self.cfg['param']['cropped'] == 'false':
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
        try:
            self.run_algo(stdout=open(self.work_dir + 'stdout.txt', 'w'))
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file('input_0.png', 'input.png')
            ar.add_file('input_0_sel.png', 'interpolated.png', 'contour.png')
            ar.add_info({'alg_action': self.cfg['param']['alg_action'], 
                'scalefactor': self.cfg['param']['scalefactor'], 
                'psfsigma': self.cfg['param']['psfsigma']})
                
            if self.cfg['param']['alg_action'] != 'Interpolate image':
                ar.add_file('coarsened.png', 'coarsened_zoom.png', 'difference.png')
            else:
                ar.add_file('input_0_zoom.png')
                        
            ar.save()

        return self.tmpl_out('run.html')


    def run_algo(self, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        
        grid = 'centered'
        scalefactor = float(self.cfg['param']['scalefactor'])
        psfsigma = float(self.cfg['param']['psfsigma'])
        img0 = image(self.work_dir + 'input_0_sel.png')
        (sizeX, sizeY) = img0.size
        
        if self.cfg['param']['alg_action'] == 'Interpolate image':                        
            # Check that input image dimensions are not too large                                        
            sizeXCrop = min(sizeX,int(800/scalefactor))
            sizeYCrop = min(sizeY,int(800/scalefactor))
            
            if (sizeX,sizeY) != (sizeXCrop,sizeYCrop):
                x0 = int(math.floor((sizeX - sizeXCrop)/2))
                y0 = int(math.floor((sizeY - sizeYCrop)/2))
                img0.crop((x0, y0, x0 + sizeXCrop, y0 + sizeYCrop))
                img0.save(self.work_dir + 'input_0_sel.png')
            
            # For display, create a nearest neighbor zoomed version of the 
            # input. nninterp does nearest neighbor interpolation on precisely
            # the same grid as cwinterp so that displayed images are aligned.
            p1 = self.run_proc(['nninterp',
                '-g', grid,
                '-x', str(scalefactor), 
                'input_0_sel.png', 'input_0_zoom.png'],
                stdout=stdout, stderr=stdout)
                        
            # Perform the actual contour stencil interpolation
            p2 = self.run_proc(['cwinterp',
                '-g', grid,
                '-x', str(scalefactor), 
                '-p', str(psfsigma),
                'input_0_sel.png', 'interpolated.png'],
                stdout=stdout, stderr=stdout)
                
            # Generate an image showing the estimated contour orientations
            p3 = self.run_proc(['cwinterp', '-s', 
                '-g', grid,
                '-x', str(scalefactor), 
                '-p', str(psfsigma),
                'input_0_sel.png', 'contour.png'],
                stdout=stdout, stderr=stdout)
                
            self.wait_proc([p1, p2, p3], timeout)
        else:            
            # Coarsen the image
            p = self.run_proc(['imcoarsen', 
                '-g', grid,
                '-x', str(scalefactor), 
                '-p', str(psfsigma),                
                'input_0_sel.png', 'coarsened.png'])
            self.wait_proc(p, timeout)
            
            # For display, create a nearest neighbor zoomed version of the
            # coarsened image.  nninterp does nearest neighbor interpolation 
            # on precisely the same grid as cwinterp so that displayed images
            # are aligned.
            p1 = self.run_proc(['nninterp',
                '-g', grid,
                '-x', str(scalefactor), 
                'coarsened.png', 'coarsened_zoom.png'],
                stdout=stdout, stderr=stdout)
            
            # Perform the actual contour stencil interpolation
            p2 = self.run_proc(['cwinterp', 
                '-g', grid,
                '-x', str(scalefactor), 
                '-p', str(psfsigma),
                'coarsened.png', 'interpolated.png'],
                stdout=stdout, stderr=stdout)
                
            # Generate an image showing the estimated contour orientations
            p3 = self.run_proc(['cwinterp', '-s', 
                '-g', grid,
                '-x', str(scalefactor), 
                '-p', str(psfsigma),
                'coarsened.png', 'contour.png'],
                stdout=stdout, stderr=stdout)
            self.wait_proc([p1, p2, p3], timeout)
                        
            # Because of rounding, the interpolated image dimensions might be 
            # slightly larger than the original image.  For example, if the 
            # input is 100x100 and the scale factor is 3, then the coarsened 
            # image has size 34x34, and the interpolation has size 102x102.
            # The following crops the results if necessary.
            img1 = image(self.work_dir + 'coarsened_zoom.png')
            img2 = image(self.work_dir + 'interpolated.png')
            img3 = image(self.work_dir + 'contour.png')

            if (sizeX, sizeY) != img1.size:
                img1.crop((0, 0, sizeX, sizeY))
                img1.save(self.work_dir + 'coarsened_zoom.png')
                img2.crop((0, 0, sizeX, sizeY))
                img2.save(self.work_dir + 'interpolated.png')
                img3.crop((0, 0, sizeX, sizeY))
                img3.save(self.work_dir + 'contour.png')
                        
            # Compute maximum difference, PSNR, and MSSIM
            p4 = self.run_proc(['imdiff', 'input_0_sel.png', 'interpolated.png'],
                            stdout=stdout, stderr=stdout)
            # Generate difference image
            p5 = self.run_proc(['imdiff', 'input_0_sel.png', 'interpolated.png', 'difference.png'],
                            stdout=stdout, stderr=stdout)                                
            self.wait_proc([p4, p5], timeout)
        
        self.cfg.save()
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        self.timestamp = int(time.time())
        return self.tmpl_out("result.html",                           
            height = max(185,image(self.work_dir + 'interpolated.png').size[1]),
            stdout = open(self.work_dir + 'stdout.txt', 'r').read())
