""""
Demonstration of paper:  A near-linear time guaranteed algorithm for digital \
                         curve simplification under the Frechet distance
"""

from lib import base_app, build, http, image
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil

class app(base_app):
    """ template demo app """ 
    
    title = "A near-linear time guaranteed algorithm for digital curve simpli"+\
            "fication under the Frechet distance"
    xlink_article = 'http://www.ipol.im/pub/pre/70/'
    xlink_src =  'http://www.ipol.im/pub/pre/70/FrechetAndConnectedCompDemo.tgz'
    demo_src_filename  = 'FrechetAndConnectedCompDemo.tgz'
    demo_src_dir  = 'FrechetAndConnectedCompDemo'

    input_nb = 1 # number of input images
    input_max_pixels = 500000 # max size (in pixels) of an input image
    input_max_weight = 1 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = False      # switch to False for deployment
    list_commands = ""


    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() is generic
        app_expose(base_app.index)
        app_expose(base_app.input_select)
        app_expose(base_app.input_upload)
        # params() is modified from the template
        app_expose(base_app.params)
        # run() and result() must be defined here

    def build(self):
        """
        program build/update
        """
        # store common file path in variables
        tgz_file = self.dl_dir + self.demo_src_filename
        prog_names = ["frechetSimplification"]
        script_names = ["convert.sh"]
        prog_bin_files = []
        
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
            # build the program
            os.mkdir(self.src_dir+ self.demo_src_dir+ "/build")
            build.run("cd %s; cmake .. -DBUILD_EXAMPLES=false \
                -DCMAKE_BUILD_TYPE=Release  \
                -DDGTAL_BUILD_TESTING=false ; \
                make -j 4" %(self.src_dir+ self.demo_src_dir + "/build"), \
                stdout=log_file) 
            
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for i in range(0, len(prog_bin_files)) :
                shutil.copy(self.src_dir +  os.path.join(self.demo_src_dir, \
                    "build", "demoIPOL_FrechetSimplification", prog_names[i]), \
                prog_bin_files[i])

            # copy supplementary files from specific folders: "displayContours",
            # "pgm2freeman"
            shutil.copy(self.src_dir + self.demo_src_dir+\
                        "/build/demoIPOL_ExtrConnectedReg/pgm2freeman", \
              self.bin_dir+"pgm2freeman")
            shutil.copy(self.src_dir + self.demo_src_dir+ \
                        "/build/demoIPOL_ExtrConnectedReg/displayContours", \
                         self.bin_dir+"displayContours")

            # copy script files
            for f in script_names :
                shutil.copy(self.src_dir + os.path.join(self.demo_src_dir, \
                 "demoIPOL_FrechetSimplification", f), self.bin_dir)
            # copy Dynamic lib
            shutil.copy(self.src_dir +self.demo_src_dir+ \
                "/build/src/libDGtal.so", self.bin_dir)
            shutil.copy(self.src_dir +self.demo_src_dir+ \
                "/build/src/libDGtalIO.so", self.bin_dir)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
       
        
        return


    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        if 'w' in kwargs:
            x = True
        else:
            x = False

        # save and validate the parameters
        try:
            self.cfg['param'] = {'tmin' : float(kwargs['tmin']),
                                 'tmax' : float(kwargs['tmax']),
                                 'm' : float(kwargs['m']),
                                 'e' : float(kwargs['e']),
                                 'w': bool(x)}
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")
        self.cfg['param']['autothreshold'] =  kwargs['thresholdtype'] == 'True' 
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # read the parameters
        tmin = self.cfg['param']['tmin']
        tmax = self.cfg['param']['tmax']

        m = self.cfg['param']['m']
        e = self.cfg['param']['e']
        w = self.cfg['param']['w']        
        autothreshold = self.cfg['param']['autothreshold'] 
        # run the algorithm
        try:
            self.run_algo(tmin, tmax, m, e, w, autothreshold)
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')    
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters given produce no contours,\
                                      please change them.")

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.png", "original.png", info="uploaded")
            ar.add_file("output.png", info="output")
            ar.add_file("commands.txt", info="commands")
            ar.add_file("inputContour.dat", info="polygon input")
            ar.add_file("output.txt", info="polygon result")
            ar.add_file("info.txt", info="computation info ")
            ar.add_info({"tmin": tmin, "tmax": tmax, "m": m, "e": e, \
                        "width only": w})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, tmin, tmax, m, e, w, autothreshold):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        self.list_commands = ""
    
        ##  -------
        ## process 1: transform input file 
        ## ---------
        command_args = ['convert.sh', 'input_0.png', 'tmp.pgm' ]
        p = self.run_proc(command_args)
        self.wait_proc(p, timeout=self.timeout)
        self.saveCommand(command_args)

        ##  -------
        ## process 2: extract contour files 
        ## ---------
        f = open(self.work_dir+"inputContour.dat", "w") 
        fInfo = open(self.work_dir+"info.txt", "w")
        command_args = ['pgm2freeman']
        command_args += ['-min_size', str(m), '-image', 'tmp.pgm']
        command_args += ['-outputSDPAll' ]
        if not autothreshold:
            command_args += ['-maxThreshold', str(tmax)]
            command_args += ['-minThreshold', str(tmin)]


        p = self.run_proc(command_args, stdout=f, \
                            stderr=fInfo, \
                            env={'LD_LIBRARY_PATH' : self.bin_dir} )
        self.wait_proc(p, timeout=self.timeout)
        if os.path.getsize(self.work_dir+"inputContour.dat") == 0: 
            raise ValueError
        f.close()
        fInfo.close()
        fInfo = open(self.work_dir+"info.txt", "r") 

        # Recover otsu max value from output
        if autothreshold:
            lines = fInfo.readlines()
            line_cases = lines[0].replace(")", " ").split()
            self.cfg['param']['tmax'] = int(line_cases[17])

        command_args += ['>', 'inputContour.dat']
        self.saveCommand(command_args)

        ##  -------
        ## process 3: apply algorithm
        ## ---------
        command_args = ['frechetSimplification']
        command_args +=  ['-error', str(e), '-sdp','inputContour.dat' ]
        command_args += ['-allContours']
        f = open(self.work_dir+"info.txt", "a")
        if w: 
            command_args += ['-w']
        p = self.run_proc(command_args, env={'LD_LIBRARY_PATH' : self.bin_dir})
        self.wait_proc(p, timeout=self.timeout)        
        self.saveCommand(command_args)

        ##  -------
        ## process 4: converting to output result
        ## ---------
        command_args = ['convert.sh', '-background', '#FFFFFF', '-flatten']
        command_args += ['output.eps', 'output.png']
        p = self.run_proc(command_args)
        self.wait_proc(p, timeout=self.timeout)
        self.saveCommand(command_args)   

        ## ----
        ## Final step: save command line
        #----
        f_commands = open(self.work_dir+"commands.txt", "w")
        f_commands.write(self.list_commands)
        f_commands.close()
        return

    @cherrypy.expose
    @init_app
    def result(self, public=None):
        """
        display the algo results
        """
        return self.tmpl_out("result.html", 
                             height=image(self.work_dir
                                          + 'input_0.png').size[1])


    def saveCommand(self, command):
        """
        Simple transform to update the attribute list_commands
        """
        command_to_save = ' '.join(['"' + arg + '"' if ' ' in arg else arg
                 for arg in command ])
        self.list_commands +=  command_to_save + '\n'


