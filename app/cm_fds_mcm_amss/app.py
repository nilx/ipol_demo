"""
mcm_amss ipol demo web app
"""
# pylint: disable=C0103

from lib import base_app
from lib import index_dict
from lib import image
from lib import build
from lib import http
from lib.misc import get_check_key, ctime
import os.path
import time
import shutil
import cherrypy
from cherrypy import TimeoutError


class app(base_app):
    """ mcm_amss app """

    title = "Finite Difference Schemes for MCM and AMSS"

    input_nb = 1
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.tiff' # input image expected extension (ie file format)
    is_test = True

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

       # select the base_app steps to expose
        # index() is generic
        base_app.index.im_func.exposed = True
        # input_xxx() are modified from the template
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True


    def build(self):
        """
        program build/update
        """
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        # MCM
        # store common file path in variables
        mcm_tgz_file = self.dl_dir + "fds_mcm.tar.gz"
        mcm_tgz_url = \
            "http://www.ipol.im/pub/algo/cm_fds_mcm_amss/fds_mcm.tar.gz"
        mcm_prog_file = self.bin_dir + "mcm"
        mcm_log = self.base_dir + "build_mcm.log"
        # get the latest source archive
        build.download(mcm_tgz_url, mcm_tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(mcm_prog_file)
            and ctime(mcm_tgz_file) < ctime(mcm_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(mcm_tgz_file, self.src_dir)
            # build the program
            build.run("make -C %s mcm"
                      % (self.src_dir + os.path.join("fds_mcm", "mcm"))
                      + " CC='ccache cc'"
                      + " OMP=1 -j4", stdout=mcm_log)
            # save into bin dir
            shutil.copy(self.src_dir + os.path.join("fds_mcm", "mcm", "mcm"),
                        mcm_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        # AMSS
        # store common file path in variables
        amss_tgz_file = self.dl_dir + "fds_amss.tar.gz"
        amss_tgz_url = \
            "http://www.ipol.im/pub/algo/cm_fds_mcm_amss/fds_amss.tar.gz"
        amss_prog_file = self.bin_dir + "amss"
        amss_log = self.base_dir + "build_amss.log"
        # get the latest source archive
        build.download(amss_tgz_url, amss_tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(amss_prog_file)
            and ctime(amss_tgz_file) < ctime(amss_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(amss_tgz_file, self.src_dir)
            # build the program
            build.run("make -C %s amss"
                      % (self.src_dir + os.path.join("fds_amss", "amss"))
                      + " CC='ccache cc'"
                      + " OMP=1 -j4", stdout=amss_log)
            # save into bin dir
            shutil.copy(self.src_dir + os.path.join("fds_amss", "amss", "amss"),
                        amss_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #
    # PARAMETER HANDLING
    #


    def draw_grid(self, grid_step):
        """
        draw a grid on the input image
        """
        # TODO: rewrite as an image function

        print "input image path:", self.key_dir + 'input_0' + self.input_ext
        try:
            im = image(self.key_dir + 'input_0' + self.input_ext)
        except IOError:
            raise cherrypy.HTTPError(400, # Bad Request
                                         "Bad input file")

        if grid_step != 0 :
            #vertical lines
            y1 = 0
            y2 = im.size[1]
            for x1 in range(0, im.size[0], grid_step):
                im.draw_line((x1, y1, x1, y2))

            #horizontal lines
            x1 = 0
            x2 = im.size[0]
            for y1 in range(0, im.size[1], grid_step):
                im.draw_line((x1, y1, x2, y1))


        im.save(self.key_dir + 'input_1' + self.input_ext)
        im.save(self.key_dir + 'input_1.png')

    @cherrypy.expose
    @get_check_key
    def params(self, newrun=False, grid_step=0, msg=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        try:
            params_file = index_dict(self.key_dir)
            params_file['paramsGrid'] = {'grid_step' : int(grid_step)}
            params_file.save()
        except:
            return self.error(errcode='badparamsGrid',
                              errmsg="Wrong grid parameters")

        self.draw_grid(int(grid_step))
        return self.tmpl_out("params.html", msg=msg,
                             input=[self.key_url + 'input_1.png'
                                    + '?grid_step=%i' % int(grid_step)])

    #
    # EXECUTION AND RESULTS
    #

    # run() is defined here,
    # because the parameters validation depends on the algorithm
    @cherrypy.expose
    @get_check_key
    def run(self, scaleR="1.0", x=None, y=None):
        """
        params handling and run redirection
        """

        # read grid parameters
        params_file = index_dict(self.key_dir)
        gridStep = int(params_file['paramsGrid']['grid_step'])
 

        # save and validate the parameters
        if (x == None) or (y == None) :
            x = 0
            y = 0

        print "x=", x
        print "y=", y
        print "grid_step=", gridStep
        print "scaleR=", float(scaleR)

        try:
            params_file = index_dict(self.key_dir)
            params_file['params'] = {'scaler' : float(scaleR)}
            params_file.save()
        except:
            return self.error(errcode='badparams',
                              errmsg="Wrong input parameters")

        #Select image to process
        gridX = int(x)
        gridY = int(y)
        if (gridStep == 0) :
            #process whole image 
            #save input image as input_2
            im = image(self.key_dir + 'input_0' + self.input_ext)
            im.save(self.key_dir + 'input_2' + self.input_ext)
            im.save(self.key_dir + 'input_2.png')
        else :
            #select subimage 
            im = image(self.key_dir + 'input_0' + self.input_ext)
            x1 = (gridX / gridStep) * gridStep
            y1 = (gridY / gridStep) * gridStep
            x2 = x1 + gridStep
            if x2 > im.size[0] :
                x2 = im.size[0]
            y2 = y1+gridStep
            if y2 > im.size[1] :
                y2 = im.size[1]
            im.crop((x1, y1, x2, y2))
            #print "crop:", x1, y1, x2, y2
            #set default image size
            im.resize((400, 400), method="nearest")
            im.save(self.key_dir + 'input_2' + self.input_ext)
            im.save(self.key_dir + 'input_2.png')

        http.refresh(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html",
                             input=[self.key_url + 'input_2.png'])


    # run_algo() is defined here,
    # because it is the actual algorithm execution, hence specific
    # run_algo() is called from result(),
    # with the parameters validated in run()
    def run_algo(self, scaleR, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """             

        # process image
        p1 = self.run_proc(['mcm', str(scaleR),
                            self.key_dir + 'input_2' + self.input_ext,
                            self.key_dir + 'output_MCM' + self.input_ext])
        p2 = self.run_proc(['amss', str(scaleR),
                            self.key_dir + 'input_2' + self.input_ext, 
                            self.key_dir + 'output_AMSS' + self.input_ext]) 
        self.wait_proc([p1, p2], timeout)
        im = image(self.key_dir + 'output_MCM' + self.input_ext)
        im.save(self.key_dir + 'output_MCM.png')
        im = image(self.key_dir + 'output_AMSS' + self.input_ext)
        im.save(self.key_dir + 'output_AMSS.png')

    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # read the parameters
        params_file = index_dict(self.key_dir)
        # normalized scale
        scaleRnorm = float(params_file['params']['scaler'])
        # read grid parameters
        gridStep = int(params_file['paramsGrid']['grid_step'])

        #de-normalize scale
        zoomfactor = 1.0
        if gridStep != 0 :
            zoomfactor = 400.0 / gridStep
        scaleR = scaleRnorm*zoomfactor

       # run the algorithm
        stdout = open(self.key_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(scaleR, stdout=stdout)
            run_time = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')
        self.log("input processed")

        return self.tmpl_out("result.html",
                             input=[self.key_url + 'input_2.png'],
                             output=[self.key_url + 'output_MCM.png',
                                     self.key_url + 'output_AMSS.png'],
                             run_time="%0.2f" % run_time,
                             scaleRnorm="%2.2f" % scaleRnorm,
                             zoomfactor="%2.2f" % zoomfactor, 
			     sizeY="%i" % image(self.key_dir
                                                + 'input_2.png').size[1])
