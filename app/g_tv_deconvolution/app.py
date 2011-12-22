"""
Total Variation Deconvolution using Split-Bregman ipol demo web app
"""

from lib import base_app, build, http, image
from lib.misc import ctime, prod
from lib.base_app import init_app
from lib.config import cfg_open
import shutil
import tarfile
import cherrypy
from cherrypy import TimeoutError
import os.path
import time
import math


class app(base_app):
    """ Total Variation Deconvolution using Split-Bregman app """

    title = \
    'Total Variation Deconvolution using Split-Bregman'

    input_nb = 1
    input_max_pixels = 700 * 700        # max size (in pixels) of input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False
    default_param = {'kernel': 'disk',  # default parameters
        'kernelsize': '2.0', 
        'noiselevel': '2',
        'maxiter': '120',
        'action': 'Deconvolve',
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
        program build/update
        """
        
        # store common file path in variables
        tgz_urls = ['http://www.ipol.im/pub/algo/' + f + '.tar.gz' for f in \
            ['g_tv_denoising/tvreg', 'g_tv_deconvolution/imutils-src']]
        tgz_files = [self.dl_dir 
            + tgz_name for tgz_name in ['tvreg.tar.gz', 'imutils-src.tar.gz']]
        src_bin = dict([(os.path.join(self.src_dir, subdir, prog),
                         os.path.join(self.bin_dir, prog))
                        for (subdir, prog) in [
                            ('tvreg','tvrestore'),
                            ('imutils-src','imblur'), 
                            ('imutils-src','imdiff')]])
        log_file = self.base_dir + 'build.log'        
        
        # get the latest source archives
        for tgz_url, tgz_file in zip(tgz_urls, tgz_files):
            build.download(tgz_url, tgz_file)
            
        # test if any dest file is missing, or too old
        if all([(os.path.isfile(bin_file)
                 and ctime(tgz_file) < ctime(bin_file))
                for bin_file in src_bin.values() for tgz_file in tgz_files]):
            cherrypy.log('not rebuild needed',
                         context='BUILD', traceback=False)
        else:
            # extract the archives
            build.extract(tgz_files[0], self.src_dir)
            tarfile.open(tgz_files[1]).extractall(self.src_dir)
            
            # build the programs
            build.run("make -C %s %s"
                % (os.path.join(self.src_dir, 'tvreg'), 'tvrestore')
                + " --makefile=makefile.gcc"
                + " CXX='ccache c++' -j4", stdout=log_file)
            for p in ['imblur', 'imdiff']:
                build.run("make -C %s %s"
                    % (os.path.join(self.src_dir, 'imutils-src'), p)
                    + " --makefile=makeimutils.gcc"
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
            ar.add_info({'action': self.cfg['param']['action']})
            ar.add_info({'kernel': self.cfg['param']['kernel'] 
                + ' of size ' + str(self.cfg['param']['kernelsize'])})
            ar.add_info({'noise level': self.cfg['param']['noiselevel']})
            ar.add_info({'lambda': '%g' % float(self.cfg['param']['lambda'])})
            
            if self.cfg['param']['action'] == self.default_param['action']:
                ar.add_file('input_0_sel.png', info='input image')
                ar.add_file('tvdeconv.png', info='deconvolved image')
            else:
                ar.add_file('input_0_sel.png', info='exact image')
                ar.add_file('blurry.png', info='input (PNSR ' 
                    + self.cfg['param']['psnr_blurry'] + ')')
                ar.add_file('tvdeconv.png', info='deconvolved (PNSR '
                    + self.cfg['param']['psnr_tvdeconv'] + ')')
                ar.add_file('diff_blurry.png', info='input difference')
                ar.add_file('diff_tvdeconv.png', info='deconvolved difference')
            
            ar.save()

        return self.tmpl_out('run.html')


    def run_algo(self, stdout=None):
        """
        The core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        
        timeout = False
        
        # Check that the image dimensions are not too large
        img = image(self.work_dir + 'input_0_sel.png')
        (sizeX, sizeY) = img.size
        cropsize = (min(sizeX, 450), min(sizeY, 450))
        
        if (sizeX, sizeY) != cropsize:
            (x0, y0) = (int(math.floor((sizeX - cropsize[0])/2)),
                int(math.floor((sizeY - cropsize[1])/2)))
            img.crop((x0, y0, x0 + cropsize[0], y0 + cropsize[1]))
            img.save(self.work_dir + 'input_0_sel.png')

        # Compute lambda from empirical formula
        r = float(self.cfg['param']['kernelsize'])
        s = max(1.0/3, float(self.cfg['param']['noiselevel']))        
        
        if self.cfg['param']['kernel'] == self.default_param['kernel']:
            Kopt = 'disk:' + str(r)
            self.cfg['param']['lambda'] = r*(427.9/s + 466.4/(s*s))
        else:
            Kopt = 'gaussian:' + str(r/2)
            self.cfg['param']['lambda'] = r*(117.0/s + 4226.3/(s*s))
        
        files = ['input_0_sel', 'tvdeconv']
        
        if self.cfg['param']['action'] == self.default_param['action']:
            self.wait_proc(self.run_proc(['tvrestore', 'K:' + Kopt,
                    'lambda:' + str(self.cfg['param']['lambda']),
                    'maxiter:' + self.default_param['maxiter'],
                    'input_0_sel.png', 'tvdeconv.png'],
                    stdout=stdout, stderr=None), timeout*0.9)
        else:
            files += ['blurry', 'diff_blurry', 'diff_tvdeconv']
            self.wait_proc(self.run_proc(['imblur', 'K:' + Kopt,
                    'noise:Gaussian:' + str(self.cfg['param']['noiselevel']),
                    'input_0_sel.png', 'blurry.png'],
                    stdout=stdout, stderr=None), timeout*0.1)            
            self.wait_proc([self.run_proc(['tvrestore', 'K:' + Kopt,
                    'lambda:' + str(self.cfg['param']['lambda']),
                    'maxiter:' + self.default_param['maxiter'],
                    'blurry.png', 'tvdeconv.png'],
                    stdout=stdout, stderr=stdout),
                self.run_proc(['imdiff', '-mpsnr',
                    'input_0_sel.png', 'blurry.png'],
                    stdout=open(self.work_dir 
                    + 'psnr_blurry.txt', 'w'), stderr=None),
                self.run_proc(['imdiff', '-D40', 'input_0_sel.png', 
                    'blurry.png', 'diff_blurry.png'],
                    stdout=None, stderr=None)], timeout*0.8)
            self.wait_proc(
                [self.run_proc(['imdiff', '-mpsnr',
                    'input_0_sel.png', 'tvdeconv.png'],
                    stdout=open(self.work_dir 
                    + 'psnr_tvdeconv.txt', 'w'), stderr=None),
                self.run_proc(['imdiff', '-D40', 'input_0_sel.png', 
                    'tvdeconv.png', 'diff_tvdeconv.png'],
                    stdout=None, stderr=None)], timeout*0.1)
            
            # Read the psnr_*.txt files
            for m in ['blurry', 'tvdeconv']:
                f = open(self.work_dir + 'psnr_' + m + '.txt', 'r')
                self.cfg['param']['psnr_' + m] = '%.2f' % float(f.readline())
                f.close()
        
        # Resize for visualization (always zoom by at least 2x)
        (sizeX, sizeY) = image(self.work_dir + 'input_0_sel.png').size        
        zoomfactor = max(2, int(math.ceil(480.0/max(sizeX, sizeY))))
        (sizeX, sizeY) = (zoomfactor*sizeX, zoomfactor*sizeY)

        files.append('input_0_sel')

        for filename in files:
            im = image(self.work_dir + filename + '.png')
            im.resize((sizeX, sizeY), method='nearest')
            im.save(self.work_dir + filename + '_zoom.png')
        
        self.cfg['param']['zoomfactor'] = zoomfactor
        self.cfg['param']['displayheight'] = max(200, zoomfactor*cropsize[1])
        self.cfg['param']['stdout'] = \
            open(self.work_dir + 'stdout.txt', 'r').read()
    
