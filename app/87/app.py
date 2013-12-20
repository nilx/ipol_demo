"""
Gaussian Convolution ipol demo web app
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

class app(base_app):
    """ Gaussian Convolution app """

    title = 'A Survey of Gaussian Convolution Algorithms'

    input_nb = 1
    input_max_pixels = 700 * 700        # max size (in pixels) of input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False
    xlink_article = "http://www.ipol.im/pub/pre/87/"

    algos = ['fir', 'dct',
            'box-3', 'box-4', 'box-5',
            'ebox-3', 'ebox-4', 'ebox-5',
            'sii-3', 'sii-4', 'sii-5',
            'am-3', 'am-4', 'am-5',
            'deriche-2', 'deriche-3', 'deriche-4',
            'vyv-3', 'vyv-4', 'vyv-5']
    
    default_param = {'sigma': '5.0',    # default parameters
        'algo' : 'fir dct',
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
        archive = 'gaussian_20131215'
        tgz_url = 'http://www.ipol.im/pub/art/2013/87/' + archive + '.tgz'
        tgz_file = self.dl_dir + archive + '.tgz'
        progs = ['gaussian_demo', 'imdiff']
        src_bin = dict([(self.src_dir + os.path.join(archive, prog),
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
                % (self.src_dir + archive, " ".join(progs))
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
        self.timestamp = int(100 * time.time())
        
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
        self.timestamp = int(100 * time.time())
        
        if not isinstance(self.cfg['param']['algo'], basestring):
          self.cfg['param']['algo'] = ' '.join(self.cfg['param']['algo'])
        
        self.cfg['param']['sigma'] = \
            str(max(float(self.cfg['param']['sigma']), 0.5))
        
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

            for algo in self.cfg['param']['algo'].split():
                ar.add_file('output-' + algo + '.png',
                    info='output ' + algo)
            
            ar.add_info({'sigma': self.cfg['param']['sigma']})
            ar.add_info({'algorithm': self.cfg['param']['algo']})
            ar.save()

        return self.tmpl_out("run.html")


    def run_algo(self, stdout=None):
        """
        The core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        
        timeout = False
        p = []
        algo_list = [algo for algo in self.cfg['param']['algo'].split() 
                     if algo in self.algos]

        if len(algo_list) == 0:
            algo_list = self.default_param['algo'].split()
        
        sigma = float(self.cfg['param']['sigma'])
        if sigma <= 2.0:
          exact_algo = 'fir'
          self.cfg['param']['exact_algo'] = (
              'FIR, <i>tol</i>=10<sup>&minus;15</sup>,')
        else:
          exact_algo = 'dct'
          self.cfg['param']['exact_algo'] = 'DCT'
        
        p.append(self.run_proc(['gaussian_demo',
                '-s', str(sigma),
                '-a', exact_algo,
                '-t1e-15',
                'input_0_sel.png', 'output-exact.png'],
                stdout=stdout, stderr=stdout))
        
        for algo in algo_list:
            s = algo.split('-')
            a = s[0]
            K = '3'
            
            if len(s) == 2:
                K = s[1]
            
            p.append(self.run_proc(['gaussian_demo',
                    '-s', str(sigma),
                    '-a' + a,
                    '-K' + K,
                    'input_0_sel.png', 'output-' + algo + '.png'],
                    stdout=stdout, stderr=stdout))
        
        self.wait_proc(p, timeout)
        
        # Compute metrics
        self.wait_proc(
            [self.run_proc(['imdiff',
                'output-exact.png', 'output-' + algo + '.png'],
                stdout=open(self.work_dir 
                    + 'metrics_' + algo + '.txt', 'w'), stderr=stdout)
                for algo in algo_list], timeout)
        
        # Read the metrics_*.txt files
        for algo in algo_list:
            try:
                f = open(self.work_dir 
                    + 'metrics_' + algo + '.txt', 'r')
                self.cfg['param'][algo + '_maxdiff'] = \
                    float(f.readline().split(':',1)[1])
                self.cfg['param'][algo + '_rmse'] = \
                    float(f.readline().split(':',1)[1])
                self.cfg['param'][algo + '_psnr'] = \
                    float(f.readline().split(':',1)[1])
                f.close()
            except:
                self.cfg['param'][algo + '_maxdiff'] = -1
                self.cfg['param'][algo + '_rmse'] = -1
                self.cfg['param'][algo + '_psnr'] = -1
        
        self.cfg['param']['algo'] = ' '.join(algo_list)
        self.cfg['param']['displayheight'] = max(50 + 40 * len(algo_list), \
            image(self.work_dir + 'input_0_sel.png').size[1])
        self.cfg.save()
    
    @cherrypy.expose
    @init_app
    def result(self, public=None):
        """
        Display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        return self.tmpl_out("result.html",
            stdout = open(self.work_dir + 'stdout.txt', 'r').read())
