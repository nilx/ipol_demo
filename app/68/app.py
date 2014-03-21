""""
Demo of paper: A Streaming Distance Transform Algorithm for \
                Neighborhood-Sequence Distances
Demo editors: N. Normand and B. Kerautret
"""

from lib import base_app, build, http, image
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import subprocess

class app(base_app):
    """ template demo app """

    title = "A Streaming Distance Transform Algorithm for \
              Neighborhood-Sequence Distances"
    xlink_article = 'http://www.ipol.im/pub/pre/68/'
    xlink_src =  'http://www.ipol.im/pub/pre/68/' + \
                 'LUTBasedNSDistanceTransform.tgz'

    input_nb = 1 # number of input images
    input_max_pixels = 500000 # max size (in pixels) of an input image
    input_max_weight = 1 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = False      # switch to False for deployment


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
        tgz_file = self.dl_dir + "LUTBasedNSDistanceTransform.tgz"
        prog_names = ["LUTBasedNSDistanceTransform"];
        script_names = ["convert.sh"];
        prog_bin_files=[];

        for f in prog_names:
            prog_bin_files.append(self.bin_dir+ f)

        log_file = self.base_dir + "build.log"
        # get the latest source archive
        print ("Starting download \n")
        build.download(self.xlink_src, tgz_file)
        print ("download ended... \n")
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_bin_files[0])
            and ctime(tgz_file) < ctime(prog_bin_files[0])):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("mkdir %s;  " %(self.src_dir+\
                     "LUTBasedNSDistanceTransform/build")   , stdout=log_file)
            build.run("cd %s; cmake .. -DWITH_PNG=true -DWITH_NETPBM=false ;\
             make -j 4" %(self.src_dir+"LUTBasedNSDistanceTransform/build"), \
                            stdout=log_file)

            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for i in range(0, len(prog_bin_files)) :
                shutil.copy(self.src_dir + \
                        os.path.join("LUTBasedNSDistanceTransform/build", \
                                      prog_names[i]), prog_bin_files[i])
            for f in script_names :
                shutil.copy(self.src_dir + \
                    os.path.join("LUTBasedNSDistanceTransform/ScriptDemoIPOL", \
                                f), self.bin_dir)

            # cleanup the source dir
            shutil.rmtree(self.src_dir)



        return



    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        # save and validate the parameters
        try:
            self.cfg['param'] = {
                'distance_def' : kwargs['distancedef'],
                'centered'     : 'centered' in kwargs,
                'sequence'     : ''.join([c for c in kwargs['sequence'] if c \
                                                                    in "12 ,"]),
                'ratio'        : ''.join([c for c in kwargs['ratio'] if c \
                                                            in "/0123456789"]),
            }
        except RuntimeError:
            return self.error(errcode='badparams',
                              errmsg="Unable to handle form inputs.")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # read the parameters
        distance_def = self.cfg['param']['distance_def']
        sequence = self.cfg['param']['sequence']
        ratio = sequence = self.cfg['param']['ratio']

        # run the algorithm
        try:
            self.run_algo(**self.cfg['param'])
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')
        except ValueError as e:
            return self.error(errcode='returncode',
                              errmsg='\n\n'+str(e))

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.png", "original.png", info="uploaded")
            ar.add_file("resu_r.png", info="output")
            ar.add_file("resu_n.png", info="output (normalized)")
            if distance_def == 'd4':
                ar.add_info({"distance": " city block"})
            elif distance_def == 'd8':
                ar.add_info({"distance": " chessboard"})
            elif distance_def == 'ratio':
                ar.add_info({"distance": " neighborhood ratio distance with\
                             %s ratio" % ratio})
            elif distance_def == 'sequence':
                ar.add_info({"distance": ' neighborhood sequence distance with \
                            "%s" sequence' % sequence})
            ar.add_file("commands.txt", info="commands")
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, distance_def, centered = False, sequence = '1 2', \
                ratio = '1/2'):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        self.cfg['param']['sizex']=image(self.work_dir + 'input_0.png').size[0]
        self.cfg['param']['sizey']=image(self.work_dir + 'input_0.png').size[1]
        p = self.run_proc(['convert.sh', 'input_0.png', 'tmp.png'])
        self.wait_proc(p, timeout=self.timeout)
        f=open(self.work_dir+"resu_r.png", "w")
        fcommands=open(self.work_dir+"commands.txt", "w")

        commandargs = ['LUTBasedNSDistanceTransform']

        print(type(distance_def), distance_def)

        if centered:
            commandargs += ['-c']

        if distance_def == 'd4':
            commandargs += ['-4']
        elif distance_def == 'd8':
            commandargs += ['-8']
        elif distance_def == 'ratio':
            commandargs += ['-r', str(ratio)]
        elif distance_def == 'sequence':
            commandargs += ['-s', str(sequence)]

        commandargs += ['-f', 'tmp.png']
        commandargs += ['-t', 'png']

        p = self.run_proc(commandargs, stdout=f, stderr=subprocess.PIPE)
        if p.wait() != 0:
            raise ValueError(p.communicate()[1])
        self.commands = ' '.join(['"' + arg + '"' if ' ' in arg else arg
            for arg in commandargs + ['>', 'resu_r.png']])
        self.commands += '\nconvert -normalize resu_r.png resu_n.png'
        self.commands += '\nconvert resu_r.png resu_r.png'
        fcommands.write(self.commands)
        fcommands.close()
        f.close()
        self.wait_proc(p, timeout=self.timeout)
        p = self.run_proc(['convert.sh', '-normalize', 'resu_r.png', \
                           'resu_n.png'])
        self.wait_proc(p, timeout=self.timeout)
        p = self.run_proc(['convert.sh', 'resu_r.png', 'resu_r.png'])
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
                                          + 'input_0.png').size[1],
                             commands=self.commands)
