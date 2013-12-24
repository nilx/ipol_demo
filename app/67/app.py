"""
Digital Level Layers for Digital Curve Decomposition and Vectorization
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
    
    title = "Digital Level Layers for Digital Curve Decomposition and Vectorization"
    xlink_article = 'http://www.ipol.im/'
    xlink_src = 'http://www.ipol.im/pub/pre/67/gjknd_1.1.tgz'
    demo_src_filename  = 'gjknd_1.1.tgz'


    input_nb = 1 # number of input images
    input_max_pixels = 500000 # max size (in pixels) of an input image
    input_max_weight = 1 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = True       # switch to False for deployment


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
        prog_names = ["dll_decomposition", "dll_sequence", "testBoundaries", "testDecomposition", "testOtsu"];
        prog_bin_files=[];
        
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
            build.run("mkdir %s;  " %(self.src_dir+"gjknd_1.1/build")   , stdout=log_file)
            build.run("cd %s; cmake .. ; make -j 4" %(self.src_dir+"gjknd_1.1/build"),stdout=log_file) 
            
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for i in range(0, len(prog_bin_files)) :
                shutil.copy(self.src_dir + os.path.join("gjknd_1.1/build/src", prog_names[i]), prog_bin_files[i])

            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        
        return



    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        if 'b' in kwargs:
            x= True
        else:
            x= False

        # save and validate the parameters
        try:
            self.cfg['param']['typeprimitive']= kwargs['typeprimitive']
            self.cfg['param']['b']=x; 
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # read the parameters
        typeprimitive = self.cfg['param']['typeprimitive']
        b= self.cfg['param']['b']
        # run the algorithm
        try:
            self.run_algo(typeprimitive)
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')    
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters given produce no contours, please change them.")

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.png", "original.png", info="uploaded")
            ar.add_file("info.txt", info="info.txt")
            ar.add_file(typeprimitive+"_out_input_0.png", info="output")
            ar.add_info({"type primitive": typeprimitive})
            ar.add_info({"use black background": b})

            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, typeprimitive):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        if self.cfg['param']['b']:
            with open(self.work_dir+"info.txt", "w") as f:
                p = self.run_proc(['dll_decomposition', '-b','-v',  '-d', typeprimitive,'input_0.png' ],stdout=f)
                self.wait_proc(p, timeout=self.timeout)
        else:
            with open(self.work_dir+"info.txt", "w") as f:
                p = self.run_proc(['dll_decomposition', '-v', '-d', typeprimitive,'input_0.png' ],stdout=f)
                self.wait_proc(p, timeout=self.timeout)
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        return self.tmpl_out("result.html", 
                             height=image(self.work_dir
                                          + 'input_0.png').size[1])
