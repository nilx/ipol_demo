""""
Meaningful Scales Detection: an Unsupervised Noise Detection Algorithm for \
Digital Contours
Demo Editor: B. Kerautret
"""

from lib import base_app, build, http, image, config
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import time


class app(base_app):
    """ template demo app """
    title = "Meaningful Scales Detection: an Unsupervised Noise "+\
            "Detection Algorithm for Digital Contours"
    xlink_article = 'http://www.ipol.im/pub/pre/75/'
    xlink_src =  'http://www.ipol.im/pub/pre/75/meaningfulscaleDemo.tgz'
    demo_src_filename  = 'meaningfulscaleDemo.tgz'
    demo_src_dir  = 'meaningfulscaleDemo'

    input_nb = 1 # number of input images
    input_max_pixels = 4096 * 4096 # max size (in pixels) of an input image
    input_max_weight = 1 * 4096 * 4096  # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = False      # switch to False for deployment
    list_commands = []

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
        prog_names = ["meaningfulScaleEstim"]
        script_names = ["applyMS.sh", "convert.sh", "convertFig.sh", \
                        "transformBG.sh"]
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
            build.run("mkdir %s;" %(self.src_dir+ self.demo_src_dir+"/build"), \
                      stdout=log_file)
            build.run("cd %s; cmake ..  -DCMAKE_BUILD_TYPE=Release \
                     -DBUILD_TESTING=false  ; make -j 4" %(self.src_dir+ \
                                                          self.demo_src_dir+\
                                                          "/build"),
                                                          stdout=log_file)

            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir + self.demo_src_dir + \
                        "/build/demoIPOL/meaningfulScaleEstim",  self.bin_dir)
            for f in script_names :
                shutil.copy(self.src_dir + os.path.join(self.demo_src_dir, \
                            "demoIPOL", f), self.bin_dir)

            # copy annex file : pgm2freeman (extraction of contours)
            shutil.copy(self.src_dir + self.demo_src_dir+ \
                        "/build/bin/pgm2freeman",  self.bin_dir)

            # copy Dynamic lib
            shutil.copy(self.src_dir + self.demo_src_dir+ \
                        "/build/src/libImaGene.so", self.bin_dir)

            # cleanup the source dir
            shutil.rmtree(self.src_dir)

        return

    @cherrypy.expose
    @init_app
    def input_select(self, **kwargs):
        """
        use the selected available input images
        """
        self.init_cfg()
        #kwargs contains input_id.x and input_id.y
        input_id = kwargs.keys()[0].split('.')[0]
        assert input_id == kwargs.keys()[1].split('.')[0]
        # get the images
        input_dict = config.file_dict(self.input_dir)
        fnames = input_dict[input_id]['files'].split()
        for i in range(len(fnames)):
            shutil.copy(self.input_dir + fnames[i],
                        self.work_dir + 'input_%i' % i)
        msg = self.process_input()
        self.log("input selected : %s" % input_id)
        self.cfg['meta']['original'] = False
        self.cfg.save()
        # jump to the params page
        return self.params(msg=msg, key=self.key)

    #---------------------------------------------------------------------------
    # Parameter handling (an optional crop).
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None):
        """Parameter handling (optional crop)."""

        # if a new experiment on the same image, clone data
        if newrun:
            self.clone_input()

        # save the input image as 'input_0_selection.png', the one to be used
        img = image(self.work_dir + 'input_0.png')
        img.save(self.work_dir + 'input_0_selection.png')
        img.save(self.work_dir + 'input_0_selection.pgm')

        # initialize subimage parameters
        self.cfg['param'] = {'x1':-1, 'y1':-1, 'x2':-1, 'y2':-1}
        self.cfg.save()
        return self.tmpl_out('params.html')



    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        # save and validate the parameters
        # handle image crop if used
        if not 'action' in kwargs:
            # read click coordinates
            x = kwargs['click.x']
            y = kwargs['click.y']
            x1 = self.cfg['param']['x1']
            y1 = self.cfg['param']['y1']
            img = image(self.work_dir + 'input_0.png')
            # check if the click is inside the image
            if int(x) >= 0 and int(y) >= 0 and \
                 int(x) < img.size[0] and int(y) < img.size[1]:
                if int(x1) < 0 or int(y1) < 0 :  # first click
                    # update (x1,y1)
                    self.cfg['param']['x1'] = int(x)
                    self.cfg['param']['y1'] = int(y)
                    self.cfg.save()

                    # draw cross
                    img.convert('3x8i')
                    img.draw_cross((int(x), int(y)), size=9, color="red")
                    img.save(self.work_dir + 'input_0_selection.png')
                elif int(x1) != int(x) and int(y1) != int(y) :  # second click
                    # update (x2,y2)
                    self.cfg['param']['x2'] = int(x)
                    self.cfg['param']['y2'] = int(y)
                    self.cfg.save()

                    # order points such that (x1,y1) is the lower left corner
                    (x1, x2) = sorted((int(x1), int(x)))
                    (y1, y2) = sorted((int(y1), int(y)))
                    assert (x2 - x1) > 0 and (y2 - y1) > 0

                    # crop the image
                    img.crop((x1, y1, x2+1, y2+1))
                    img.save(self.work_dir + 'input_0_selection.png')
                    img.save(self.work_dir + 'input_0_selection.pgm')
            return self.tmpl_out('params.html')


        try:
            self.cfg['param'] = {'tmax' : float(kwargs['tmax']),
                                 'm' : float(kwargs['m'])}
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
        self.list_commands = ""

        # read the parameters
        t = self.cfg['param']['tmax']
        m = self.cfg['param']['m']
        autothreshold = self.cfg['param']['autothreshold']
        # run the algorithm
        try:
            self.run_algo({'t':t, 'm':m, 'autothreshold':autothreshold})
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
            ar.add_file("input_0_selection.png","selection.png")
            ar.add_file("resu.png", info="output")
            ar.add_file("noiseLevels.txt", info="noise levels")
            ar.add_file("inputContourFC.txt", info="polygon input")
            ar.add_file("commands.txt", info="commands")
            ar.add_file("resu.eps", info="result in eps format")
            ar.add_info({"threshold auto": autothreshold})
            ar.add_info({"threshold tmax": self.cfg['param']['tmax']})
            ar.add_info({"contour min size m": m})
            try:
                version_file = open(self.work_dir + "version.txt", "w")
                p = self.run_proc(["meaningfulScaleEstim", "-version"], \
                                  stdout=version_file, \
                                  env={'LD_LIBRARY_PATH' : self.bin_dir})
                self.wait_proc(p)
                version_file.close()
                version_file = open(self.work_dir + "version.txt", "r")
                version_info = version_file.readline()
                version_file.close()
            except Exception:
                version_info = "unknown"
            ar.add_info({"meaningfulScaleEstim version " : version_info})
            ar.add_info({"#contours" : self.cfg['info']['num_contours']})
            ar.add_info({"run time (s)" : self.cfg['info']['run_time']})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, params):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        # t, m, autothreshold
        self.cfg['param']['sizex'] = image(self.work_dir + \
                                           'input_0.png').size[0]
        self.cfg['param']['sizey'] = image(self.work_dir + \
                                            'input_0.png').size[1]
        ##  -------
        ## process 1: transform input file
        ## ---------
        command_args = ['/usr/bin/convert', 'input_0_selection.png',  \
                        'input_0_selection.pgm' ]
        self.runCommand(command_args)


        ##  -------
        ## process 2: Extract 2D contours
        ## ---------
        command_args = ['pgm2freeman']
        if not params['autothreshold']:
            command_args += ['-threshold', str(params['t']) ]
        command_args += ['-min_size', str(params['m']) ]

        fInput = open(self.work_dir+'input_0_selection.pgm', "r")
        f =  open(self.work_dir+'inputContour.txt', "w")
        fInfo =  open(self.work_dir+'info.txt', "w")
        cntExtractionCmd = self.runCommand(command_args, stdIn=fInput, \
                                           stdOut=f, stdErr=fInfo, \
                        comp = ' < input_0.pgm > inputContour.txt')
        fInput.close()
        f.close()
        fInfo.close()
        sizeContour = os.path.getsize(self.work_dir+"inputContour.txt")
        if sizeContour == 0 :
            raise ValueError

        #Recover otsu max value from log
        fInfo =  open(self.work_dir+'info.txt', "r")
        if self.cfg['param']['autothreshold']:
            lines = fInfo.readlines()
            line_cases = lines[0].split('=')
            self.cfg['param']['tmax'] = float(line_cases[1])
        fInfo.close()

        self.commentsResultContourFile(cntExtractionCmd, self.work_dir+\
                                       'inputContourFC.txt')
        ##  -------
        ## process 3: Convert background image
        ## ---------
        command_args = ['/usr/bin/convert', '-brightness-contrast', '40x-40' ]
        command_args += ['input_0_selection.png', 'input_0BG.png']
        self.runCommand(command_args)


        ##  -------
        ## process 4:
        ## ---------
        foutput = open(self.work_dir+'noiseLevels.txt', "w")
        fLog = open(self.work_dir+'logMS.txt', "w")
        fInput = open(self.work_dir+'inputContour.txt', "r")
        command_args = ['meaningfulScaleEstim', '-enteteXFIG']+\
                       ['-drawXFIGNoiseLevel', '-setFileNameFigure']+\
                       ['noiseLevel.fig', '-drawContourSRC', '4', '1']+\
                       ['-afficheImage', 'input_0BG.png']+\
                       [str(image(self.work_dir + 'input_0BG.png').size[0])] +\
                       [str(image(self.work_dir + 'input_0BG.png').size[1])] +\
                       ['-setPosImage', '1', '1', '-printNoiseLevel'] + \
                       ['-processAllContours']
        try:
            self.cfg['info']['run_time'] = time.time()
            num_lines = sum(1 for line in open(self.work_dir + \
                                               'inputContour.txt'))
 
            self.cfg['info']['num_contours'] = num_lines
            self.runCommand(command_args, stdIn=fInput, stdOut=foutput, \
                            stdErr=fLog,\
                            comp="< inputContour.txt > noiseLevels.txt")
        except (OSError, RuntimeError):
            fLog.write("Some contours were not processed.")
        self.cfg['info']['run_time'] = time.time() - \
                                       self.cfg['info']['run_time']   
        fInput.close()
        fLog.close()
        p = self.run_proc(['convertFig.sh','noiseLevel.fig'])
        self.wait_proc(p, timeout=self.timeout)


        ## ----
        ## Final step: save command line
        ## ----
        fcommands = open(self.work_dir+"commands.txt", "w")
        fcommands.write(self.list_commands)
        fcommands.close()
        return


    @cherrypy.expose
    @init_app
    def result(self, public=None):
        """
        display the algo results
        """
        resultHeight = image(self.work_dir + 'input_0_selection.png').size[1]
        imageHeightResized = min (600, resultHeight)
        resultHeight = max(200, resultHeight)
        return self.tmpl_out("result.html", height=resultHeight, \
                             heightImageDisplay=imageHeightResized, \
                             width=image(self.work_dir\
                                           +'input_0_selection.png').size[0])


    def runCommand(self, command, stdIn=None, stdOut=None, stdErr=None, \
                   comp=None, outFileName=None):
        """
        Run command and update the attribute list_commands
        """
        p = self.run_proc(command, stdin=stdIn, stderr=stdErr, stdout=stdOut, \
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
        if outFileName is not None:
            command_to_save += ' > ' + outFileName

        self.list_commands +=  command_to_save + '\n'
        return command_to_save

    def commentsResultContourFile(self, command, fileStrContours):
        """
        Add comments in the resulting contours (command line producing the file,
        or file format info)
        """

        contoursList = open (self.work_dir+"tmp.dat", "w")
        contoursList.write("# Set of resulting contours obtained from the " +\
                            "pgm2freeman algorithm. \n")
        contoursList.write( "# Each line corresponds to a digital "  + \
                                "contour " +  \
                                " given with the first point of the digital "+ \
                                "contour followed  by its freeman code "+ \
                                "associated to each move from a point to "+ \
                                "another (4 connected: code 0, 1, 2, and 3).\n")
        contoursList.write( "# Command to reproduce the result of the "+\
                            "algorithm:\n")

        contoursList.write("# "+ command+'\n \n')
        f = open (self.work_dir+'inputContour.txt', "r")
        index = 0
        for line in f:
            contoursList.write("# contour number: "+ str(index) + "\n")
            contoursList.write(line+"\n")
            index = index +1
        contoursList.close()
        f.close()
        shutil.copy(self.work_dir+'tmp.dat', fileStrContours)
        os.remove(self.work_dir+'tmp.dat')
