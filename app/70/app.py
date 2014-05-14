""""
Demonstration of paper:  A near-linear time guaranteed algorithm for digital \
                         curve simplification under the Frechet distance
demo editor: Bertrand Kerautret
"""

from lib import base_app, build, http, image, config
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil

class app(base_app):
    """ template demo app """

    title = "A Near-Linear Time Guaranteed Algorithm for Digital Curve Simpli"+\
            "fication Under the Fr&eacute;chet Distance"
    xlink_article = 'http://www.ipol.im/pub/pre/70/'
    xlink_src =  'http://www.ipol.im/pub/pre/70/FrechetAndConnectedCompDemo.tgz'
    demo_src_filename  = 'FrechetAndConnectedCompDemo.tgz'
    demo_src_dir  = 'FrechetAndConnectedCompDemo'

    input_nb = 1 # number of input images
    input_max_pixels = 500000 # max size (in pixels) of an input image
    input_max_weight = 1 * 2048 * 2048 # max size (in bytes) of an input file
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

        m = self.cfg['param']['m']
        e = self.cfg['param']['e']

        # run the algorithm
        self.list_commands = ""

        try:
            self.run_algo({})
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
            ar.add_file("output.png", info="result.png")
            ar.add_file("commands.txt", info="commands")
            ar.add_file("inputPolygon.txt", info="input polygons")
            ar.add_file("outputPolygon.txt", info="output polygons")
            ar.add_info({"tmin": self.cfg['param']['tmin'],
            			 "tmax": self.cfg['param']['tmax'], "m": m, "e": e, \
                        "width only": self.cfg['param']['w']})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, params):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        ##  -------
        ## process 1: transform input file
        ## ---------
        command_args = ['convert.sh', 'input_0.png', 'inputNG.pgm' ]
        self.runCommand(command_args)

        ##  -------
        ## process 2: extract contour files
        ## ---------
        f = open(self.work_dir+"inputPolygon.txt", "w")
        fInfo = open(self.work_dir+"algoLog.txt", "w")
        command_args = ['pgm2freeman']+\
				       ['-min_size', str(self.cfg['param']['m']), '-image',\
				        'inputNG.pgm']+\
        			   ['-outputSDPAll' ]
        if not self.cfg['param']['autothreshold']:
            command_args += ['-maxThreshold', str(self.cfg['param']['tmax'])]+ \
           					['-minThreshold', str(self.cfg['param']['tmin'])]

        cmd = self.runCommand(command_args, f, fInfo, \
                              comp = ' > inputPolygon.txt')

        if os.path.getsize(self.work_dir+"inputPolygon.txt") == 0:
            raise ValueError
        fInfo.close()
        fInfo = open(self.work_dir+"algoLog.txt", "r")

        #Recover otsu max value from output
        if self.cfg['param']['autothreshold']:
            lines = fInfo.readlines()
            line_cases = lines[0].replace(")", " ").split()
            self.cfg['param']['tmax'] = int(line_cases[17])

        contoursList = open (self.work_dir+"tmp.dat", "w")
        contoursList.write("# Polygon contour obtained from the pgm2freeman"+\
        					" program with the following options: \n"+\
       						"# "+ cmd + "\n"+\
       					   "# Each line corresponds to an resulting polygon. "+\
        	               "All vertices (xi yi) are given in the same line: "+\
        	               " x0 y0 x1 y1 ... xn yn \n")
        index = 0
        f.close()
        f = open(self.work_dir+"inputPolygon.txt", "r")

        for contour in f:
            contoursList.write("# contour number: "+ str(index) + "\n")
            contoursList.write(contour+"\n")
            index = index + 1
        contoursList.close()
        f.close()
        shutil.copy(self.work_dir+'tmp.dat', self.work_dir+'inputPolygon.txt')


        ##  -------
        ## process 3: apply algorithm
        ## ---------
        inputWidth = image(self.work_dir + 'input_0.png').size[0]
        inputHeight = image(self.work_dir + 'input_0.png').size[1]
        command_args = ['frechetSimplification'] + \
                       ['-imageSize', str(inputWidth), str(inputHeight)] + \
                       ['-error', str(self.cfg['param']['e']), '-sdp',
                        'inputPolygon.txt' ]+\
                       ['-allContours']
        f = open(self.work_dir+"algoLog.txt", "a")
        if self.cfg['param']['w']:
            command_args += ['-w']

        cmd = self.runCommand(command_args)
        contoursList = open (self.work_dir+"tmp.dat", "w")
        contoursList.write("# Set of resulting polygons obtained from the " +\
        		            "frechetSimplification algorithm. \n"+\
        		            "# Each line corresponds to an resulting polygon."+\
        					" All vertices (xi yi) are given in the same line:"+
        					"  x0 y0 x1 y1 ... xn yn \n"+\
        					"# Command to reproduce the result of the "+\
				        	"algorithm:\n")
        contoursList.write("#"+ cmd+'\n')
        f = open (self.work_dir+"output.txt", "r")
        index = 0
        for line in f:
            contoursList.write("# contour number: "+ str(index) + "\n")
            contoursList.write(line+"\n")
            index = index +1
        contoursList.close()
        f.close()
        shutil.copy(self.work_dir+'tmp.dat', self.work_dir+'outputPolygon.txt')


        ## ---------
        ## process 4: converting to output result
        ## ---------
        command_args = ['convert.sh', '-background', '#FFFFFF', '-flatten', \
                        'output.eps', 'output.png']
        self.runCommand(command_args)

        ## ----
        ## Final step: save command line
        ## ----
        f = open(self.work_dir+"commands.txt", "w")
        f.write(self.list_commands)
        f.close()
        return

    @cherrypy.expose
    @init_app
    def result(self, public=None):
        """
        display the algo results
        """
        resultHeight = image(self.work_dir + 'input_0.png').size[1]
        imageHeightResized = min (600, resultHeight)
        resultHeight = max(300, resultHeight)
        return self.tmpl_out("result.html", height=resultHeight, \
        					 heightImageDisplay=imageHeightResized)


    def runCommand(self, command, stdOut=None, stdErr=None, comp=None):
        """
        Run command and update the attribute list_commands
        """
        p = self.run_proc(command, stderr=stdErr, stdout=stdOut, \
        				  env={'LD_LIBRARY_PATH' : self.bin_dir})
        self.wait_proc(p, timeout=self.timeout)
        index = 0
        # transform convert.sh in it classic prog command (equivalent)
        for arg in command:
            if arg == "convert.sh" :
                command[index] = "convert"
            index = index + 1
        command_to_save = ' '.join(['"' + arg + '"' if ' ' in arg else arg
                 for arg in command ])
        if comp is not None:
            command_to_save += comp
        self.list_commands +=  command_to_save + '\n'
        return command_to_save

    def make_archive(self):
        """
        create an archive bucket HACK!
        This overloaded verion of the empty_app function
        first deletes the entry and its directory so that the 
        new one is correcly stored.
        """
        # First delete the key from the archive if it exist
        from lib import archive
        archive.index_delete(self.archive_index, self.key)
        entrydir = self.archive_dir + archive.key2url(self.key)
        if os.path.isdir(entrydir):
            shutil.rmtree(entrydir)

        # Then insert the new data
        ar = archive.bucket(path=self.archive_dir,
                            cwd=self.work_dir,
                            key=self.key)
        ar.cfg['meta']['public'] = self.cfg['meta']['public']

        def hook_index():
            """
            create an archive bucket
            """
            return archive.index_add(self.archive_index,
                                     bucket=ar,
                                     path=self.archive_dir)
        ar.hook['post-save'] = hook_index
        return ar

