""""
Extraction of Connected Region Boundary in Multidimensional Images
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

    title = "Extraction of Connected Region Boundary in Multidimensional Images"
    xlink_article = 'http://www.ipol.im/pub/pre/74/'
    xlink_src = 'http://www.ipol.im/pub/pre/74/FrechetAndConnectedCompDemo.tgz'
    demo_src_filename = 'FrechetAndConnectedCompDemo.tgz'
    demo_src_dir = 'FrechetAndConnectedCompDemo'

    input_nb = 1 # number of input images
    input_max_pixels = 10000000 # max size (in pixels) of an input image
    input_max_weight = 3 * input_max_pixels #max size (in bytes) of an input file
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
                self.cfg['param']['startthreshold'] = float(kwargs[
                    'startthreshold'])
                self.cfg['param']['endthreshold'] = float(kwargs[
                    'endthreshold'])
                self.cfg['param']['thresholdstep'] = float(kwargs[
                    'thresholdstep'])
                self.cfg['param']['thresholdsingle'] = kwargs['thresholdtype'] \
                                                       == 'Single interval'
                self.cfg['param']['thresholdauto'] = kwargs['thresholdtype'] \
                                                      == 'Auto (Otsu)'
                self.cfg['param']['thresholdtype'] = kwargs['thresholdtype']

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
            an_archive.add_file("freemanChainContours.fc", 
                                info="resulting contours")
            an_archive.add_file("info.txt", info="computation info ")
            an_archive.add_file("commands.txt", info="commands")
            an_archive.add_info({"threshold type": 
                                 self.cfg['param']['thresholdtype']})
            if not self.cfg['param']['thresholdtype'] == 'Auto (Otsu)':
                if  self.cfg['param']['thresholdtype'] == 'Single interval':
                    an_archive.add_info({"min threshold":
                                         self.cfg['param']['minthreshold']})
                    an_archive.add_info({"max threshold":
                                         self.cfg['param']['maxthreshold']})
                else:
                    an_archive.add_info({"threshold end ":self.cfg['param']\
                                 ['startthreshold']})
                    an_archive.add_info({"threshold step":self.cfg['param']\
                                 ['thresholdstep']})
                    an_archive.add_info({"threshold max":self.cfg['param']\
                                 ['endthreshold']})
            an_archive.add_info({"interior adjacency": self.cfg['param']\
                         ['interioradjacency']})
            an_archive.save()
        return self.tmpl_out("run.html")

    def run_algo(self, para):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
          
        # by default 0=interior adjacency
        adjacency = 0
        if not self.cfg['param']['interioradjacency']:
            adjacency = 1

        if  not self.cfg['meta']['is3d']:
            # preparing input and conversion
            thStep = self.cfg['param']['thresholdstep']
            startTh = self.cfg['param']['startthreshold']
            endTh = self.cfg['param']['endthreshold']
            self.cfg['param']['sizex'] = image(self.work_dir + \
                                               'input_0_selection.png').size[0]
            self.cfg['param']['sizey'] = image(self.work_dir + \
                                         'input_0_selection.png').size[1]
            p = self.run_proc(['/usr/bin/convert', self.work_dir +\
                               'input_0_selection.png', \
                               self.work_dir +'input_0_selection.pgm'])
            self.wait_proc(p, timeout=self.timeout)
            transbg_cmd = ['/usr/bin/convert']+ ['+contrast', '+contrast', \
                                                 '+contrast', '+contrast', \
                                                 '+contrast'] +\
                          ['-modulate', '160,100,100']+ ['-type', 'grayscale', \
                                                         '-depth', '8']+\
                          ['input_0_selection.pgm']+\
                          ['input_0BG.png']

            fcommands = open(self.work_dir+"commands.txt", "w")
            self.commands = ' '.join(['"' + arg + '"' if ' ' in arg else arg
                 for arg in transbg_cmd ])
            p = self.run_proc(transbg_cmd)
            self.wait_proc(p, timeout=self.timeout)
          
            # Extracting all 2D contours with pgm2freeman
            #main command of the algorithm (used to exploit it in run and save)
            command_args = ['pgm2freeman']
   
            fcontoursFC = open(self.work_dir+"freemanChainContours.fc", "w")
            fInfo = open(self.work_dir+"info.txt", "w")
            command_args += ['-image', 'input_0_selection.pgm']
            command_args += ['-badj', str(adjacency)]
          
            if not self.cfg['param']['thresholdauto']:               
                if  self.cfg['param']['thresholdsingle']:
                    command_args += ['-minThreshold'] + \
                                    [str(para['minthreshold'])]
                    command_args += ['-maxThreshold'] + \
                                    [str(para['maxthreshold'])]
                else:
                    command_args += ['-thresholdRange']+[str(startTh)]+\
                                    [str(thStep)]+[str(endTh)]
              
        
            p = self.run_proc(command_args, stdout=fcontoursFC, \
                             stderr=fInfo, \
                              env={'LD_LIBRARY_PATH': self.bin_dir})
            self.wait_proc(p, timeout=self.timeout)
            fcontoursFC.close()
            if os.path.getsize(self.work_dir+"freemanChainContours.fc") == 0:
                raise ValueError

            command = ' '.join(['"' + arg + '"' if ' ' in arg else arg
                 for arg in command_args + ['>', 'freemanChainContours.fc']])
            self.commands += '\n'+ command


            #Display all contours with initial image as background:
            p = self.run_proc(['displayContours', '-fc', \
                               'freemanChainContours.fc'\
                               , '-outputFIG',\
                                self.work_dir +'imageContours.fig',\
                               '-backgroundImageXFIG', \
                               'input_0BG.png',\
                               str(self.cfg['param']['sizex']),\
                               str(self.cfg['param']['sizey'])], \
                              env={'LD_LIBRARY_PATH' : self.bin_dir})
            self.wait_proc(p, timeout=self.timeout)
            
            p = self.run_proc(['convertFig.sh', 'imageContours.fig', \
                               'resu.png'], stderr=fInfo, \
                              env={'LD_LIBRARY_PATH' : self.bin_dir})
            self.wait_proc(p, timeout=self.timeout)
            self.commands += '\ndisplayContours -fc reemanChainContours.fc '+\
                              '-outputFIG imageContours.fig '+ \
                              '-backgroundImageXFIG input_0BG.png '+\
                               str(self.cfg['param']['sizex'])+' '+\
                               str(self.cfg['param']['sizey'])+\
                              '\nfig2dev -L eps imageContours.fig resu.eps '+\
                              '\nconvert -density 50 resu.eps resu.png'

            fcommands.write(self.commands)
            fcommands.close()
            fInfo.close()

        

        else:
            p = self.run_proc(['extract3D', '-image', self.work_dir +\
                               'inputVol_0.vol', '-badj', str(adjacency), \
                               '-threshold', str(para['minthreshold']), \
                                str(para['maxthreshold']), \
                               '-output',\
                               'result.obj', '-exportSRC', 'src.obj'], \
                              env={'LD_LIBRARY_PATH' : self.bin_dir})
            self.wait_proc(p, timeout=self.timeout)
        return

    @cherrypy.expose
    @init_app
    def result(self, public=None):
        """
        display the algo results
        """
        return self.tmpl_out("result.html",
                             height=image(self.work_dir \
                                          + 'input_0_selection.png').size[1],\
                             width=image(self.work_dir\
                                          +'input_0_selection.png').size[0])
