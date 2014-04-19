""""
Demonstration of paper:  Extraction of Connected Region Boundary in
                         Multidimensional Images
demo editor: Bertrand Kerautret
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

    title = "Extraction of Connected Region Boundary in Multidimensional Images"
    xlink_article = 'http://www.ipol.im/'
    xlink_src = 'http://www.ipol.im/pub/art/2014/74/'+\
                'FrechetAndConnectedCompDemo.tgz'
    demo_src_filename = 'FrechetAndConnectedCompDemo.tgz'
    demo_src_dir = 'FrechetAndConnectedCompDemo'

    input_nb = 1 # number of input images
    input_max_pixels = 4096 * 4096 # max size (in pixels) of an input image
    input_max_weight = 1 * 4096 * 4096  # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = False      # switch to False for deployment
    commands = []
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
        prog_names = ["pgm2freeman", "displayContours", "extract3D"]
        script_names = ["convert.sh", "convertFig.sh", "transformBG.sh"]
        prog_bin_files = []

        for a_prog in prog_names:
            prog_bin_files.append(self.bin_dir+ a_prog)

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
                       -DCMAKE_BUILD_TYPE=Release \
                       -DDGTAL_BUILD_TESTING=false;\
                       make -j 4"%(self.src_dir+ self.demo_src_dir + "/build")\
                      , stdout=log_file)

            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for i in range(0, len(prog_bin_files)):
                shutil.copy(self.src_dir +
                            os.path.join(self.demo_src_dir,
                                         "build",
                                         "demoIPOL_ExtrConnectedReg",
                                         prog_names[i]),
                            prog_bin_files[i])
            for s_name in script_names:
                shutil.copy(self.src_dir+
                            os.path.join(self.demo_src_dir,
                                         "demoIPOL_ExtrConnectedReg",
                                         s_name), self.bin_dir)
            # copy Dynamic lib
            shutil.copy(self.src_dir +self.demo_src_dir+
                        "/build/src/libDGtal.so", self.bin_dir)
            shutil.copy(self.src_dir +self.demo_src_dir+
                        "/build/src/libDGtalIO.so", self.bin_dir)
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
        if input_dict[input_id]['type'] == "3d":
            fnames = input_dict[input_id]['volume'].split()
            for i in range(len(fnames)):
                shutil.copy(self.input_dir + fnames[i],
                            self.work_dir + 'inputVol_%i' % i +'.vol')
        msg = self.process_input()
        self.log("input selected : %s" % input_id)
        self.cfg['meta']['original'] = False
        self.cfg['meta']['is3d'] = input_dict[input_id]['type'] == "3d"
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
            # Specific manual clone  for vol file (3d case only):
            if self.cfg['meta']['is3d'] :
                oldPath = self.work_dir + 'inputVol_0.vol'
                self.clone_input()
                shutil.copy(oldPath, self.work_dir + 'inputVol_0.vol')
            else:
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

        if not 'is3d' in  self.cfg['meta']:
            self.cfg['meta']['is3d'] = False

        try:
            self.cfg['param'] = {'minthreshold' : float(kwargs['minthreshold']),
                                 'maxthreshold' : float(kwargs['maxthreshold']),
                                 'interioradjacency':
                                 kwargs['adjacency'] == 'interior'}
            if not self.cfg['meta']['is3d']:
                self.cfg['param']['minimalsize'] = float(kwargs[\
                    'minimalsize'])
                self.cfg['param']['startthreshold'] = float(kwargs[\
                    'startthreshold'])
                self.cfg['param']['endthreshold'] = float(kwargs[\
                    'endthreshold'])
                self.cfg['param']['thresholdstep'] = float(kwargs[\
                    'thresholdstep'])
                self.cfg['param']['thresholdsingle'] = kwargs['thresholdtype'] \
                                                       == 'Single interval'
                self.cfg['param']['thresholdauto'] = kwargs['thresholdtype'] \
                                                      == 'Auto (Otsu)'
                self.cfg['param']['thresholdtype'] = kwargs['thresholdtype']
                self.cfg['param']['outputformat'] = kwargs['outputformat']

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
        self.commands = ""
        # run the algorithm
        try:
            self.run_algo({'minthreshold': self.cfg['param']['minthreshold'],
                           'maxthreshold': self.cfg['param']['maxthreshold']})
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="Try again with simpler images.")
        except RuntimeError:
            return self.error(errcode='runtime',
                              errmsg="Something went wrong with the program.")
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters given produce no contours,\
                              please change them.")

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            an_archive = self.make_archive()
            an_archive.add_file("input_0.png", "original.png", info="uploaded")
            an_archive.add_file("input_0_selection.png","selection.png")
            an_archive.add_file("resu.png", info="output")
            an_archive.add_file("resu.eps", info="output in eps format")
            an_archive.add_file("outputContoursFreemanCode.txt",
                                info="resulting contours (Freeman code format)")
            if self.cfg['param']['outputformat'] == 'sdp':
                an_archive.add_file("outputContoursListPoints.txt",
                                info="resulting contours (sequence of points)")
            an_archive.add_file("commands.txt", info="commands")
            an_archive.add_info({"interior adjacency": self.cfg['param']\
                         ['interioradjacency']})
            an_archive.add_info({"minimal contour size:": \
                                self.cfg['param']['minimalsize']})
            an_archive.add_info({"threshold type": \
                                 self.cfg['param']['thresholdtype']})
            if  (self.cfg['param']['thresholdtype'] == 'Single interval') or \
                self.cfg['param']['thresholdtype'] == 'Auto (Otsu)':
                an_archive.add_info({"min/max threshold": \
                                     "%i/%i"%(self.cfg['param']['minthreshold']\
                                        ,self.cfg['param']['maxthreshold'])})

            else:
                an_archive.add_info({"threshold start":self.cfg['param']\
                             ['startthreshold']})
                an_archive.add_info({"threshold step":self.cfg['param']\
                             ['thresholdstep']})
                an_archive.add_info({"threshold end":self.cfg['param']\
                             ['endthreshold']})
            try:
                version_file = open(self.work_dir + "version.txt", "w")
                p = self.run_proc(["pgm2freeman", "-version"], \
                                    stdout=version_file, \
                                    env={'LD_LIBRARY_PATH' : self.bin_dir})
                self.wait_proc(p)
                version_file.close()
                version_file = open(self.work_dir + "version.txt", "r")
                version_info = version_file.readline()
                version_file.close()
            except RuntimeError :
                version_info = "unknown"
            an_archive.add_info({"pgm2freeman version " : version_info})
            an_archive.add_info({"run time (s):":self.cfg['info']['run_time']})

            an_archive.save()
        return self.tmpl_out("run.html")

    def run_algo(self, params):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        # by default 0=interior adjacency
        adjacency = 0
        if not self.cfg['param']['interioradjacency']:
            adjacency = 1

        #----------
        # 2D case
        #----------

        if  not self.cfg['meta']['is3d']:
            # preparing input and conversion

            self.cfg['param']['sizex'] = image(self.work_dir + \
                                               'input_0_selection.png').size[0]
            self.cfg['param']['sizey'] = image(self.work_dir + \
                                         'input_0_selection.png').size[1]
            ##  -------
            ## process 1: transform input file
            ## ---------
            command_args = ['/usr/bin/convert', 'input_0_selection.png', \
                            'input_0_selection.pgm' ]
            self.runCommand(command_args)

            ##  -------
            ## process 2: generate background image
            ## ---------

            cmd = ['/usr/bin/convert']+ ['+contrast', '+contrast', \
                                                 '+contrast', '+contrast', \
                                                 '+contrast'] +\
                          ['-modulate', '160,100,100']+ ['-type', 'grayscale', \
                                                         '-depth', '8']+\
                          ['input_0_selection.pgm']+\
                          ['input_0BG.png']

            self.runCommand(cmd)

            ##  -------
            ## process 3: Extracting all 2D contours with pgm2freeman
            ## main command of the algorithm
            ## ---------

            fcontoursFC = open(self.work_dir + \
                               'outputContoursFreemanCodeTMP.txt', "w")
            fInfo = open(self.work_dir+"info.txt", "w")
            command_args = ['pgm2freeman', '-image', 'input_0_selection.pgm'] +\
                           ['-badj', str(adjacency)] + \
                           ['-min_size', str(self.cfg['param']['minimalsize'])]

            if not self.cfg['param']['thresholdauto']:
                if  self.cfg['param']['thresholdsingle']:
                    command_args += ['-minThreshold'] + \
                                    [str(params['minthreshold'])] +\
                                    ['-maxThreshold'] + \
                                    [str(params['maxthreshold'])]
                else:
                    command_args += ['-thresholdRange']+\
                                    [str(self.cfg['param']['startthreshold'])]+\
                                    [str(self.cfg['param']['thresholdstep'])]+ \
                                    [str(self.cfg['param']['endthreshold'])]

            self.cfg['info']['run_time'] = time.time()
            cmd = self.runCommand(command_args, \
                                  stdErr=fInfo, stdOut=fcontoursFC, \
                                  outFileName='outputContoursFreemanCode.txt')
            self.cfg['info']['run_time'] = time.time() - \
                                            self.cfg['info']['run_time']
            fcontoursFC.close()
            if os.path.getsize(self.work_dir+\
                               "outputContoursFreemanCodeTMP.txt") == 0:
                raise ValueError

            fInfo.close()
            fInfo = open(self.work_dir+"info.txt", "r")

            #Recover otsu max value from output
            if self.cfg['param']['thresholdauto']:
                lines = fInfo.readlines()
                line_cases = lines[0].replace(")", " ").split()
                self.cfg['param']['maxthreshold'] = float(line_cases[17])
                self.cfg['param']['minthreshold'] = 0.0

            self.commentsResultContourFile(cmd, self.work_dir+ \
                                           'outputContoursFreemanCodeTMP.txt', \
                                           self.work_dir+ \
                                           'outputContoursFreemanCode.txt', \
                                            False )

            ##  -------
            ## process 3 bis: Extract contours in sdp format
            ## ---------
            if self.cfg['param']['outputformat'] == 'sdp':
                fcontoursSDP = open(self.work_dir+'outputCntTMP.sdp', "w")
                command_args += ['-outputSDPAll']
                command_args = self.runCommand(command_args, stdErr=fInfo, \
                                               stdOut=fcontoursSDP, \
                                               outFileName = \
                                               'outputContoursListPoints.txt')
                fcontoursSDP.close()
                self.commentsResultContourFile(command_args, self.work_dir+ \
                                               'outputCntTMP.sdp', \
                                               self.work_dir+ \
                                               'outputContoursListPoints.txt', \
                                                True)


            ##  -------
            ## process 4: Display resulting contours
            ## ---------

            #Display all contours with initial image as background:
            command_args = ['displayContours'] +  \
                           ['-fc', 'outputContoursFreemanCode.txt'] \
                          +[ '-outputFIG', 'imageContours.fig',\
                            '-backgroundImageXFIG', 'input_0BG.png', \
                            str(self.cfg['param']['sizex']),\
                            str(self.cfg['param']['sizey'])]
            self.runCommand(command_args)

            p = self.run_proc(['convertFig.sh', 'imageContours.fig', \
                               'resu.png'], stderr=fInfo, \
                              env={'LD_LIBRARY_PATH' : self.bin_dir})
            self.wait_proc(p, timeout=self.timeout)
            self.commands +=  'fig2dev -L eps imageContours.fig resu.eps '+\
                              '\nconvert -density 50 resu.eps resu.png'


            fInfo.close()

        #----------
        # 3D case
        #----------

        else:
            command_args = ['extract3D', '-image', 'inputVol_0.vol',  \
                            '-badj', str(adjacency) ] + \
                            ['-threshold', str(params['minthreshold'])] + \
                            [str(params['maxthreshold']), '-output']  + \
                            ['result.obj', '-exportSRC', 'src.obj']
            self.runCommand(command_args)

        fcommands = open(self.work_dir+"commands.txt", "w")
        fcommands.write(self.commands)
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


    def runCommand(self, command, stdOut=None, stdErr=None, comp=None,
                   outFileName=None):
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
        if outFileName is not None:
            command_to_save += ' > ' + outFileName

        self.commands +=  command_to_save + '\n'
        return command_to_save


    def commentsResultContourFile(self, command, fileStrContours, fileStrRes,
                                 sdp):
        """
        Add comments in the resulting contours (command line producing the file,
        or file format info)
        """

        contoursList = open (self.work_dir+"tmp.dat", "w")
        contoursList.write("# Set of resulting contours obtained from the " +\
                            "pgm2freeman algorithm. \n")
        if not sdp:
            contoursList.write( "# Each line corresponds to a digital "  + \
                                "contour " +  \
                                " given with the first point of the digital "+ \
                                "contour followed  by its freeman code "+ \
                                "associated to each move from a point to "+ \
                                "another (4 connected: code 0, 1, 2, and 3).\n")
        else:
            contoursList.write("# Each line represents a resulting polygon.\n"+\
                            "# All vertices (xi yi) are given in the same "+
                            " line: x0 y0 x1 y1 ... xn yn \n")
        contoursList.write( "# Command to reproduce the result of the "+\
                            "algorithm:\n")

        contoursList.write("# "+ command+'\n \n')
        f = open (fileStrContours, "r")
        index = 0
        for line in f:
            contoursList.write("# contour number: "+ str(index) + "\n")
            contoursList.write(line+"\n")
            index = index +1
        contoursList.close()
        f.close()
        shutil.copy(self.work_dir+'tmp.dat', fileStrRes)
        os.remove(self.work_dir+'tmp.dat')
