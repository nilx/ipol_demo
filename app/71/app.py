"""
Interactive segmentation based on component-trees
"""

from lib import base_app, build, http, image
from lib.misc import  app_expose, ctime
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
    """ Interactive segmentation based on component-trees """

    title = 'Interactive segmentation based on component-trees'
    xlink_article = 'http://www.ipol.im/pub/pre/71/' 
    xlink_src =  'http://www.ipol.im/pub/pre/71/ctseg_2.zip'
    demo_src_filename  = 'ctseg_2.zip'

    input_nb = 1
    input_max_pixels = 500 * 500        # max size (in pixels) of input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False    
    default_param = {'lambda': 0.1,  # default parameters
                     'pensize': 5,
                     'pencolor':'yellow'}
    pencolors = {'yellow'   : [255, 255, 0]}

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
        tgz_file = self.dl_dir + self.demo_src_filename
        prog_names = ["ctseg"];
        script_names = ["convert.sh", "applyCT.sh"];
        prog_bin_files = [];
        
        for f in prog_names:
            prog_bin_files.append(self.bin_dir+ f)            

        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(self.xlink_src, tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_bin_files[0])
            and ctime(tgz_file) < ctime(prog_bin_files[0])):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)            
            print ("extract done \n")
                        
            # build the program
            build.run("cd %s; make " %(self.src_dir+"ctseg_2"), stdout=log_file) 
            
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)

            for i in range(0, len(prog_bin_files)) :
                shutil.copy(self.src_dir + os.path.join("ctseg_2", prog_names[i]), prog_bin_files[i])

            for f in script_names :
                shutil.copy(self.src_dir + os.path.join("ctseg_2", f), self.bin_dir)

            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        
        return


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
        
        mask.putpalette([128, 128, 128] + [0, 0, 0]*254
            + self.pencolors[self.cfg['param']['pencolor']])
        mask.save(self.work_dir + 'mask.gif', transparency=0)
        
    
    @cherrypy.expose
    @init_app
    def editmask(self, **kwargs):
        """
        Edit the inpainting mask
        """
        
        generate_options = {
            'random text' : 'text',
            'random dots' : 'dots:3',
            'random scribble' : 'scribble:3',
            'random Bernoulli' : 'Bernoulli:0.5'
            }
        commandlist = self.readcommandlist()
        
        if 'action' in kwargs:
            if kwargs['action'] == 'undo':
                if commandlist:
                    commandlist.pop()
            elif kwargs['action'] == 'clear':
                commandlist = []
            elif kwargs['action'] in generate_options.keys():
                self.wait_proc(self.run_proc(['randmask', 
                    generate_options[kwargs['action']],
                    self.work_dir + 'input_0.png', 'mask.png'],
                    stdout=None, stderr=None), None)
                
                if os.path.isfile(self.work_dir + 'maskcommands.txt'):
                    os.remove(self.work_dir + 'maskcommands.txt')
                
                mask = Image.open(self.work_dir + 'mask.png')
                mask = mask.convert('L')
                mask = mask.convert('P')
                mask.putpalette([128,128,128] + [0,0,0]*254 
                    + self.pencolors[self.cfg['param']['pencolor']])
                mask.save(self.work_dir + 'mask.gif', transparency=0)
                                
                return self.tmpl_out('params.html')
        elif 'pencolor_yellow' in kwargs:
            self.cfg['param']['pencolor'] = 'yellow'
            
            mask = Image.open(self.work_dir + 'mask.gif')
            mask.putpalette([128,128,128] + [0,0,0]*254 
                + self.pencolors[self.cfg['param']['pencolor']])
            mask.save(self.work_dir + 'mask.gif', transparency=0)
            
            return self.tmpl_out('params.html')
        elif 'pencolor_blue' in kwargs:
            self.cfg['param']['pencolor'] = 'blue'
            
            mask = Image.open(self.work_dir + 'mask.gif')
            mask.putpalette([128,128,128] + [0,0,0]*254 
                + self.pencolors[self.cfg['param']['pencolor']])
            mask.save(self.work_dir + 'mask.gif', transparency=0)
            
            return self.tmpl_out('params.html')
        elif 'pencolor_black' in kwargs:
            self.cfg['param']['pencolor'] = 'black'
            
            mask = Image.open(self.work_dir + 'mask.gif')
            mask.putpalette([128,128,128] + [0,0,0]*254 
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

        self.cfg['param']['negate'] = 'negate' in kwargs; 
            
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
            ar.add_file("mask.png", 
                info="mask image")
            ar.add_file("composite.png", 
                info="input")
            ar.add_file("result.png", 
                info="result result")
            ar.add_info({"alpha":  float(self.cfg['param']['lambda'])})
            ar.add_info({"negate image": self.cfg['param']['negate']})
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

        p = self.run_proc(['convert.sh', 'input_0.png', 'input_0.pgm'])
        self.wait_proc(p, timeout=self.timeout)

        p = self.run_proc(['convert.sh', 'mask.png', 'mask.pgm'])
        self.wait_proc(p, timeout=self.timeout)
      
        # Run ct tree
        if self.cfg['param']['negate']:
            self.wait_proc(self.run_proc(['ctseg', 'input_0.pgm',  'mask.pgm',
                                          str(self.cfg['param']['lambda']),'negate'],
                                         stdout=stdout, stderr=stdout), timeout)
        else:
            self.wait_proc(self.run_proc(['ctseg', 'input_0.pgm',  'mask.pgm',
                                          str(self.cfg['param']['lambda'])],
                                         stdout=stdout, stderr=stdout), timeout)

        p = self.run_proc(['convert.sh', 'result.pgm', 'result.png'])
        self.wait_proc(p, timeout=self.timeout)

        
        zoomfactor = int(max(1, floor(550.0/max(size[0], size[1]))))
        size = (zoomfactor*size[0], zoomfactor*size[1])
        
        for filename in ['input_0',  'result', 'mask']:
            img = image(self.work_dir + filename + '.png')
            img.resize(size, method='nearest')
            img.save(self.work_dir + filename + '_zoom.png')
        

        self.cfg['param']['displayheight'] = max(200, size[1])
        self.cfg['param']['zoomfactor'] = zoomfactor
        self.cfg['param']['zoomwidth'] = size[0]
        self.cfg['param']['zoomheight'] = size[1]

    
