"""
Image Demosaicking with Contour Stencils ipol demo web app
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
from math import floor, ceil


class app(base_app):
    """ Image Demosaicking with Contour Stencils  app """

    title = 'Image Demosaicking with Contour Stencils '

    input_nb = 1
    input_max_pixels = 700 * 700        # max size (in pixels) of input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False
    default_param = {'pattern': 'RGGB', # default parameters
             'alpha': 1.8,
             'x0': None,
             'y0': None,
             'x' : None,
             'y' : None}
    
    # showcontours_max_pixels is the max image size in pixels for showing the
    # contours as a PDF.  If the image is small enough, the estimated contours
    # are rendered as EPS and converted with Ghostscript to PDF.
    showcontours_max_pixels = 25000

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
        # Generate a new timestamp
        self.timestamp = int(100*time.time())


    def build(self):
        """
        Program build/update
        """
        # Store common file path in variables
        tgz_url = 'http://www.ipol.im/pub/algo/' \
            + 'g_demosaicking_with_contour_stencils/src.tar.gz'
        tgz_file = self.dl_dir + 'src.tar.gz'
        progs = ['dmcswl1', 'dmbilinear', 'mosaic', 'imdiff']
        sub_dir = 'dmcswl1-src'
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
        Algorithm execution
        """
        # Run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            print "Run time error"
            return self.error(errcode='runtime')
        
        stdout.close()
        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        
        # Archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0_sel.png", 
                info="selected subimage")
            ar.add_file("mosaicked.png", 
                info="mosaicked image")
            ar.add_file("dmcswl1.png", 
                info="contour stencils demosaicked (MSE " 
                + self.cfg['param']['mse_dmcswl1'] + ")")
            ar.add_file("diffdmcswl1.png", 
                info="difference image for contour stencils")
            ar.add_file("bilinear.png", 
                info="bilinear demosaicked (MSE "
                + self.cfg['param']['mse_bilinear'] + ")")
            ar.add_file("diffbilinear.png", 
                info="difference image for bilinear")
            ar.add_info({"pattern": self.cfg['param']['pattern']})
            ar.add_info({"alpha": self.cfg['param']['alpha']})
            
            if self.cfg['param']['showcontours']:
                ar.add_file("contours.pdf", 
                    info="contours estimated from the mosaicked image")
            
            ar.save()

        return self.tmpl_out("run.html")


    def run_algo(self, stdout=None):
        """
        The core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        
        timeout = False
        pattern = self.cfg['param']['pattern']
        padding = 16
        
        # Crop image if necessary
        img = image(self.work_dir + 'input_0_sel.png')
        (sizeX, sizeY) = img.size
        cropsize = (min(sizeX, 800), min(sizeY, 800))
        
        if (sizeX, sizeY) != cropsize:
            (x0, y0) = (int(floor((sizeX - cropsize[0])/2)),
                int(floor((sizeY - cropsize[1])/2)))
            img.crop((x0, y0, x0 + cropsize[0], y0 + cropsize[1]))
            img.save(self.work_dir + 'input_0_sel.png')
        
        showcontours = (cropsize[0]*cropsize[1] \
            <= self.showcontours_max_pixels)
        
        # Mosaic image with 16-pixel padding
        self.wait_proc(self.run_proc(['mosaic', 
            '-p', pattern, '-e', str(padding),
            'input_0_sel.png', 'mosaicked.png'],
            stdout=None, stderr=None), timeout*0.1)

        # Demosaic image, CPU times are recorded in stdout_*.txt files
        p = [self.run_proc(['dmcswl1', '-p', pattern, 
                '-a', str(self.cfg['param']['alpha']),
                'mosaicked.png', 'dmcswl1.png'],
                stdout=open(self.work_dir 
                + 'stdout_dmcswl1.txt', 'w'), stderr=None),
            self.run_proc(['dmbilinear', '-p', pattern, 
                'mosaicked.png', 'bilinear.png'],
                stdout=open(self.work_dir 
                + 'stdout_bilinear.txt', 'w'), stderr=None)]
        
        # Display estimate image contours as EPS
        if showcontours:            
            p.append(self.run_proc(['dmcswl1', '-p', pattern, '-s',
                'input_0_sel.png', 'contours.eps'],
                stdout=None, stderr=None))
        
        self.wait_proc(p, timeout*0.7)
        
        # Trim the padding
        for m in ['mosaicked', 'bilinear', 'dmcswl1']:
            img = image(self.work_dir + m + '.png')
            img.crop((padding, padding, \
                padding + cropsize[0], padding + cropsize[1]))
            img.save(self.work_dir + m + '.png')
        
        # Compute MSEs, the results are saved in files mse_*.txt
        self.wait_proc(
            [self.run_proc(['imdiff','-mmse',
                'input_0_sel.png', m + '.png'],
                stdout=open(self.work_dir 
                + 'mse_' + m + '.txt', 'w'), stderr=None)
            for m in ['bilinear', 'dmcswl1']], timeout*0.1)
        
        # Read the mse_*.txt and stdout_*.txt files
        for m in ['bilinear', 'dmcswl1']:
            f = open(self.work_dir + 'mse_' + m + '.txt', 'r')
            self.cfg['param']['mse_' + m] = "%.2f" % float(f.readline())
            f.close()
            
            self.cfg['param']['cpu_' + m] = ''
            
            for line in open(self.work_dir + 'stdout_' + m + '.txt', 'r'):
                if line.count('CPU Time:') > 0:
                    self.cfg['param']['cpu_' + m] = line.split(':',1)[1]
                    break
        
        # Compute image differences
        self.wait_proc([self.run_proc(['imdiff', 'input_0_sel.png', 
                'dmcswl1.png', 'diffdmcswl1.png'],
                stdout=None, stderr=None),
            self.run_proc(['imdiff', 'input_0_sel.png', 
                'bilinear.png', 'diffbilinear.png'],
                stdout=None, stderr=None)], timeout*0.1)
                        
        # Convert EPS to PDF
        if showcontours:
            try:
                self.wait_proc(self.run_proc(['/usr/bin/gs', 
                    '-dSAFER', '-q', '-P-', '-dCompatibilityLevel=1.4',
                    '-dNOPAUSE', '-dBATCH', '-sDEVICE=pdfwrite', 
                    '-sOutputFile=contours.pdf', '-c', '.setpdfwrite', 
                    '-f', 'contours.eps'],
                    stdout=stdout, stderr=stdout), timeout*0.1)
            except OSError:
                self.log("eps->pdf conversion failed,"
                        + " gs is probably missing on this system")
                showcontours = False
        
        # Resize for visualization (new size of the smallest dimension = 200)
        zoomfactor = int(max(1, ceil(200.0/min(cropsize[0], cropsize[1]))))
        (sizeX, sizeY) = (zoomfactor*cropsize[0], zoomfactor*cropsize[1])
        
        for filename in ['input_0_sel', 'mosaicked', 'dmcswl1', 'bilinear',
            'diffdmcswl1', 'diffbilinear']:
            im = image(self.work_dir + filename + '.png')
            im.resize((sizeX, sizeY), method='nearest')
            im.save(self.work_dir + filename + '_zoom.png')

        self.cfg['param']['displayheight'] = sizeY
        self.cfg['param']['zoomfactor'] = zoomfactor
        self.cfg['param']['showcontours'] = showcontours

