"""
Malvar-He-Cutler Linear Image Demosaicking ipol demo web app
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
from math import ceil


class app(base_app):
    """ Malvar-He-Cutler Linear Image Demosaicking app """

    title = 'Malvar-He-Cutler Linear Image Demosaicking'

    input_nb = 1
    input_max_pixels = 700 * 700        # max size (in pixels) of input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False
    default_param = {'pattern': 'RGGB', # default parameters
             'x0': None,
             'y0': None,
             'x' : None,
             'y' : None}

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
            + 'g_malvar_he_cutler_linear_image_demosaicking/src.tar.gz'
        tgz_file = self.dl_dir + 'src.tar.gz'
        progs = ['dmmalvar', 'dmbilinear', 'mosaic', 'imdiff']
        sub_dir = 'dmmalvar-src'
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
        
        self.cfg.save()
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
        # Run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
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
            ar.add_file("mosaiced.png", 
                info="mosaiced image")
            ar.add_file("malvar.png", 
                info="Malvar demosaiced image")
            ar.add_file("diffmalvar.png", 
                info="difference image for Malvar")
            ar.add_file("bilinear.png", 
                info="bilinear demosaiced image")
            ar.add_file("diffbilinear.png", 
                info="difference image for bilinear")
            ar.add_info({"pattern": self.cfg['param']['pattern']})
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

        # Mosaic image
        self.wait_proc(self.run_proc(['mosaic', '-p', pattern, 
            'input_0_sel.png', 'mosaiced.png'],
            stdout=stdout, stderr=stdout), timeout*0.2)

        # Demosaic image
        self.wait_proc([ 
            self.run_proc(['dmmalvar', '-p', pattern, 
                'mosaiced.png', 'malvar.png'],
                stdout=stdout, stderr=stdout),
            self.run_proc(['dmbilinear', '-p', pattern, 
                'mosaiced.png', 'bilinear.png'],
                stdout=stdout, stderr=stdout)], timeout*0.6)

        # Compute image differences
        self.wait_proc([
            self.run_proc(['imdiff', 'input_0_sel.png', 
                'malvar.png', 'diffmalvar.png'],
                stdout=stdout, stderr=stdout),
            self.run_proc(['imdiff', 'input_0_sel.png', 
                'bilinear.png', 'diffbilinear.png'],
                stdout=stdout, stderr=stdout)], timeout*0.2)
        
        # Resize for visualization (new size of the smallest dimension = 200)
        (sizeX, sizeY) = image(self.work_dir + 'input_0_sel.png').size        
        zoomfactor = max(1, int(ceil(200.0/min(sizeX, sizeY))))
        (sizeX, sizeY) = (zoomfactor*sizeX, zoomfactor*sizeY)

        for filename in ['input_0_sel', 'mosaiced', 'malvar', 'bilinear',
            'diffmalvar', 'diffbilinear']:
            im = image(self.work_dir + filename + '.png')
            im.resize((sizeX, sizeY), method='nearest')
            im.save(self.work_dir + filename + '_zoom.png')

        self.cfg['param']['displayheight'] = sizeY
        self.cfg['param']['zoomfactor'] = zoomfactor
        self.cfg.save()

