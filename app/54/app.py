"""
Enhanced PLE Inpainting ipol demo web app
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
from math import floor
from PIL import Image
import ImageDraw


class app(base_app):
    """ EPLE Inpainting app """

    title = 'E-PLE: an Algorithm for Image Inpainting'

    xlink_article = 'http://www.ipol.im/pub/pre/54/'
    input_nb = 1
    input_max_pixels = 400 * 400        # max size (in pixels) of input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False    
    default_param = {'patchsize': 8,
                     'overlap': 7,
                     'iteration': 1,    
                     'pensize': 5,
                     'maskingratio': 0.5,       
                     'pencolor':'yellow'}
    pencolors = {'yellow'   : [255, 255, 0], 
            'blue'          : [0, 0, 255], 
            'black'         : [0, 0, 0]}

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
        archive = 'eple_20130131'
        tgz_url = 'http://www.ipol.im/pub/pre/54/eple_20130131.tgz'
        tgz_file = self.dl_dir + 'eple_20130131.tgz'
        progs = ['inpaintEPLE', 'randmask']
        src_bin = dict([(self.src_dir 
            + os.path.join(archive, prog),
            self.bin_dir + prog) for prog in progs])
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
            build.run('make OMP=1 -j4 -C %s -f makefile'
                % (self.src_dir + archive),
                stdout=log_file)
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

    #
    # PARAMETER HANDLING
    #
    
    def readcommandlist(self):
        """
        Read the drawing commandlist from maskcomands.txt
        """
                
        try:
            ifile = file(self.work_dir + 'maskcommands.txt', 'r')
            commandlist = [tuple([int(t) for t in line.split(' ')]) \
                for line in ifile.readlines()]
            ifile.close()
        except IOError:
            commandlist = []
        
        return commandlist
    
    
    def rendermask(self):
        """
        Render the drawing commandlist into the mask 
        """        
        
        commandlist = self.readcommandlist()
        size = image(self.work_dir + 'input_0.png').size
        self.cfg['param']['viewbox_width'] = size[0]
        self.cfg['param']['viewbox_height'] = size[1]
        
        mask = Image.new('P', size, 0)   # Create a grayscale image
        draw = ImageDraw.Draw(mask)
    
        for (t, x, y) in commandlist:
            draw.ellipse((x - t, y - t, x + t + 1, y + t + 1), fill=255)
        
        mask.putpalette([128, 128, 128] + [0, 0, 0] * 254
            + self.pencolors[self.cfg['param']['pencolor']])
        mask.save(self.work_dir + 'mask.gif', transparency=0)
        
    
    @cherrypy.expose
    @init_app
    def editmask(self, **kwargs):
        """
        Edit the inpainting mask
        """      
        
        commandlist = self.readcommandlist()
        
        if 'action' in kwargs:
            if kwargs['action'] == 'undo':
                if commandlist:
                    commandlist.pop()
            elif kwargs['action'] == 'clear':
                commandlist = []
            elif kwargs['action'] == 'random text':
                self.wait_proc(self.run_proc(['randmask', 'text', 
                self.work_dir + 'input_0.png', 'mask.png'],
                stdout=None, stderr=None), None)
                
                if os.path.isfile(self.work_dir + 'maskcommands.txt'):
                    os.remove(self.work_dir + 'maskcommands.txt')
                
                mask = Image.open(self.work_dir + 'mask.png')
                mask = mask.convert('L')
                mask = mask.convert('P')
                mask.putpalette([128, 128, 128] + [0, 0, 0] * 254 
                    + self.pencolors[self.cfg['param']['pencolor']])
                mask.save(self.work_dir + 'mask.gif', transparency=0)
                                
                return self.tmpl_out('params.html')
            elif kwargs['action'] == 'random dots':
                self.wait_proc(self.run_proc(['randmask', 'dots:3', 
                self.work_dir + 'input_0.png', 'mask.png'],
                stdout=None, stderr=None), None)
                
                if os.path.isfile(self.work_dir + 'maskcommands.txt'):
                    os.remove(self.work_dir + 'maskcommands.txt')
                
                mask = Image.open(self.work_dir + 'mask.png')
                mask = mask.convert('L')
                mask = mask.convert('P')
                mask.putpalette([128, 128, 128] + [0, 0, 0] * 254 
                    + self.pencolors[self.cfg['param']['pencolor']])
                mask.save(self.work_dir + 'mask.gif', transparency=0)
                                
                return self.tmpl_out('params.html')
            elif kwargs['action'] == 'random scribble':
                self.wait_proc(self.run_proc(['randmask', 'scribble:1', 
                self.work_dir + 'input_0.png', 'mask.png'],
                stdout=None, stderr=None), None)
                
                if os.path.isfile(self.work_dir + 'maskcommands.txt'):
                    os.remove(self.work_dir + 'maskcommands.txt')
                
                mask = Image.open(self.work_dir + 'mask.png')
                mask = mask.convert('L')
                mask = mask.convert('P')
                mask.putpalette([128, 128, 128] + [0, 0, 0] * 254 
                    + self.pencolors[self.cfg['param']['pencolor']])
                mask.save(self.work_dir + 'mask.gif', transparency=0)
                                
                return self.tmpl_out('params.html')
            elif kwargs['action'] == 'Bernoulli mask':
                if 'maskingratio' in kwargs:
                    maskarg = 'Bernoulli' + ':' + str(kwargs['maskingratio'])
                else:
                    maskarg = 'Bernoulli:'+str(self.cfg['param']['maskingratio'])

                self.wait_proc(self.run_proc(['randmask', maskarg, 
                self.work_dir + 'input_0.png', 'mask.png'],
                stdout=None, stderr=None), None)
                
                if os.path.isfile(self.work_dir + 'maskcommands.txt'):
                    os.remove(self.work_dir + 'maskcommands.txt')
                
                mask = Image.open(self.work_dir + 'mask.png')
                mask = mask.convert('L')
                mask = mask.convert('P')
                mask.putpalette([128, 128, 128] + [0, 0, 0] * 254 
                    + self.pencolors[self.cfg['param']['pencolor']])
                mask.save(self.work_dir + 'mask.gif', transparency=0)
                                
                return self.tmpl_out('params.html')
        elif 'pencolor_yellow' in kwargs:
            self.cfg['param']['pencolor'] = 'yellow'
            
            mask = Image.open(self.work_dir + 'mask.gif')
            mask.putpalette([128, 128, 128] + [0, 0, 0] * 254 
                + self.pencolors[self.cfg['param']['pencolor']])
            mask.save(self.work_dir + 'mask.gif', transparency=0)
            
            return self.tmpl_out('params.html')
        elif 'pencolor_blue' in kwargs:
            self.cfg['param']['pencolor'] = 'blue'
            
            mask = Image.open(self.work_dir + 'mask.gif')
            mask.putpalette([128, 128, 128] + [0, 0, 0] * 254 
                + self.pencolors[self.cfg['param']['pencolor']])
            mask.save(self.work_dir + 'mask.gif', transparency=0)
            
            return self.tmpl_out('params.html')
        elif 'pencolor_black' in kwargs:
            self.cfg['param']['pencolor'] = 'black'
            
            mask = Image.open(self.work_dir + 'mask.gif')
            mask.putpalette([128, 128, 128] + [0, 0, 0] * 254 
                + self.pencolors[self.cfg['param']['pencolor']])
            mask.save(self.work_dir + 'mask.gif', transparency=0)
            
            return self.tmpl_out('params.html')
        else:
            commandlist.append((int(kwargs['pensize']), \
                int(kwargs['x']), int(kwargs['y'])))
        
        f = file(self.work_dir + 'maskcommands.txt', 'w')
        #f.write('This is a test\n')
        f.writelines('%i %i %i\n' % (t, x, y)  \
                    for (t, x, y) in commandlist )
        f.close()
        
        # Generate a new timestamp
        self.timestamp = int(100*time.time())
                
        self.cfg['param']['pensize'] = int(kwargs['pensize'])
        # Set undefined parameters to default values
        self.cfg['param'] = dict(self.default_param, **self.cfg['param'])
        
        self.rendermask()
        return self.tmpl_out('params.html')

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
            # Also need to clone maskcommands.txt to keep the mask
            if os.path.isfile(old_work_dir + 'maskcommands.txt'):
                shutil.copy(old_work_dir + 'maskcommands.txt',
                    self.work_dir + 'maskcommands.txt')
        
        # Set undefined parameters to default values
        self.cfg['param'] = dict(self.default_param, **self.cfg['param'])
        # Generate a new timestamp
        self.timestamp = int(100*time.time())
        
        self.rendermask()
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
        
        # Open image and inpainting domain mask
        img = Image.open(self.work_dir + 'input_0.png').convert('RGB')
        mask = Image.open(self.work_dir + 'mask.gif')
        
        # Extract alpha
        alpha = mask.copy()
        alpha.putpalette([0, 0, 0]*255 + [255, 255, 255])
        alpha = alpha.convert('L')
        
        # Extract mask palette for display
        lut = mask.resize((256, 1))
        lut.putdata(range(256))
        lut = lut.convert('RGB').getdata()
        
        # Save binary PNG version of the mask
        mask.putpalette([0, 0, 0]*255 + [255, 255, 255])
        mask.save(self.work_dir + 'mask.png')
        
        # Save image + mask composited version for display
        img.paste(lut[255], alpha)
        img.save(self.work_dir + 'composite.png')
        
        # Save another composite where mask is gray for computation
        img.paste((128, 128, 128), alpha)
        img.save(self.work_dir + 'u0.png')
        
        # Generate a new timestamp
        self.timestamp = int(100*time.time())
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
            ar.add_file("input_0.png", 
                info="original image")
            ar.add_file("composite.png", 
                info="input") 
            ar.add_file("inpainted.png", 
                info="inpainting result") 
            ar.add_file("patchmap.png", 
                info="patch map")
            ar.add_info({"maskingratio": '%.1f' % float(self.cfg['param']['maskingratio'])}) 
            ar.add_info({"overlap": '%i' % int(self.cfg['param']['overlap'])})
            ar.add_info({"patchsize": '%i' % int(self.cfg['param']['patchsize'])})  
            ar.add_info({"iteration": '%i' % int(self.cfg['param']['iteration'])}) 
            ar.save()

        return self.tmpl_out("run.html")


    def run_algo(self, stdout=None):
        """
        The core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        
        timeout = False
        
        # Get image size
        size = image(self.work_dir + 'input_0.png').size
        
        # Run eple: EPLE is allowed to iterate just once because of the its speed
        # PLE, even slower, isn't fit for the demo. 
        self.wait_proc(self.run_proc(['inpaintEPLE', 'u0.png', 'mask.png',
            'inpainted.png', str(self.cfg['param']['iteration']) ], stdout=stdout, stderr=stdout), timeout)
        
        zoomfactor = int(max(1, floor(550.0/max(size[0], size[1]))))
        size = (zoomfactor*size[0], zoomfactor*size[1])
        
        for filename in ['input_0', 'composite', 'inpainted']:
            img = image(self.work_dir + filename + '.png')
            img.resize(size, method='nearest')
            img.save(self.work_dir + filename + '_zoom.png')
        
        self.cfg['param']['displayheight'] = max(200, size[1])
        self.cfg['param']['zoomfactor'] = zoomfactor
        self.cfg['param']['zoomwidth'] = size[0]
        self.cfg['param']['zoomheight'] = size[1]
        self.cfg['param']['stdout'] = \
            open(self.work_dir + 'stdout.txt', 'r').read()
