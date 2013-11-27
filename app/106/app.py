"""
Automatic Lens Distortion Correction Using One Parameter Division Models (demo webpp)
"""
from lib import base_app, build, http
from lib.misc import ctime
from lib.base_app import init_app
from lib.config import cfg_open
import shutil

import cherrypy
from cherrypy import TimeoutError

import os.path
import time

#
# INTERACTION
#
class NoMatchError(RuntimeError):
    """ NoMatchError function """  
    pass



class app(base_app):
    """ Automatic Lens Distortion Correction Using One Parameter Division Models app """

    title = 'Automatic Lens Distortion Correction Using One-Parameter Division Model'
    description = ''

    input_nb = 1                 # number of input files
    input_max_pixels = 1024000   # max size (in pixels) of an input image
    input_max_weight = 5242880   # max size (in bytes) of an input file
    input_dtype = '3x8i'         # input image expected data type
    input_ext = '.png'           # input image expected extention
    is_test = False

    xlink_article = 'http://www.ipol.im/pub/pre/106/'
     
    # Default parameters
    default_param = {
             'high_threshold_canny'                  : 0.8, 
             'initial_distortion_parameter'          : 0.0, 
             'final_distortion_parameter'            : 3.0, 
             'distance_point_line_max_hough'         : 3.0, 
             'angle_point_orientation_max_difference': 2.0
                      }



    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
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

        # run() is defined in local.py
        from local import run_algo as local_run
        # redefine app.run()
        app.run_algo = local_run




    def build(self):
        """
        program build/update
        """
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir) 
            
        if not os.path.isdir(self.dl_dir):
            os.mkdir(self.dl_dir) 

        # store common file path in variables
        progs = [ 'lens_distortion_correction_division_model_1p' ]

        sub_dir = ''
        src_bin = dict([(self.src_dir + os.path.join(sub_dir, prog),
                         self.bin_dir + prog)
                        for prog in progs])

        # store common file path in variables
        tgz_url = "http://www.ipol.im/pub/pre/106/" \
                + "ldm_q1p.zip"
        tgz_file = self.dl_dir   + "ldm_q1p.zip"
        log_file = self.base_dir + "build_ldm_q1p.zip.log"
        
        # Get the latest source archive
        build.download(tgz_url, tgz_file) 
        # Test if any dest file is missing, or too old
        if all([(os.path.isfile(bin_file) and ctime(tgz_file) < ctime(bin_file))
            for bin_file in src_bin.values()]):
            cherrypy.log("not rebuild needed", context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)

            # Build the programs 
            make_command = "make" + " -j4 -C  %s %s "
            build.run(make_command % (self.src_dir + sub_dir, \
                      " ".join(progs)), stdout=log_file)

            # Save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for (src, dst) in src_bin.items():
                shutil.copy(src, dst)

            # cleanup the source dir
            shutil.rmtree(self.src_dir) 
        return




    #
    # PARAMETER HANDLING
    #
    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None):
        """
        configure the algo execution
        """
        
        # Set undefined parameters to default values
        self.cfg['param'] = dict(self.default_param, **self.cfg['param'])

        if newrun:
            old_work_dir = self.work_dir
            self.clone_input()
            
            # Keep old parameters
            self.cfg['param'] = cfg_open( old_work_dir + 'index.cfg', 'rb')['param']

        return self.tmpl_out("params.html")

   




    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """

        # save and validate the parameters
        try:
            
            self.cfg['param']['high_threshold_canny'] = float(kwargs['high_threshold_canny'])
            self.cfg['param']['initial_distortion_parameter'] = float(kwargs['initial_distortion_parameter'])
            self.cfg['param']['final_distortion_parameter'] = float(kwargs['final_distortion_parameter'])
            self.cfg['param']['distance_point_line_max_hough'] = float(kwargs['distance_point_line_max_hough'])
            self.cfg['param']['angle_point_orientation_max_difference'] = float(kwargs['angle_point_orientation_max_difference'])
            
            self.cfg.save()
            
        except ValueError:
            return self.error(errcode='badparams', errmsg="Wrong input parameters.")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html" )

        




    @cherrypy.expose
    @init_app
    def run(self): ##, **kwargs):
        """
        algorithm execution
        """
        stdout = open(self.work_dir + 'stdout.txt', 'w')

        try:
            run_time = time.time()
            self.run_algo( stdout=stdout, timeout=self.timeout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="Try again with simpler images.")
        except NoMatchError:
            http.redir_303(self.base_url + 'result?key=%s&error_nomatch=1' % \
                           self.key)
        except RuntimeError:
            return self.error(errcode='runtime')
            
        stdout.close()
        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive() 
            ar.add_file("input_0.png", info="", compress=False ) 
            ar.add_info( {'high_threshold_canny' : self.cfg['param']['high_threshold_canny'] } ) 
            ar.add_info( {'initial_distortion_parameter' : self.cfg['param']['initial_distortion_parameter'] } ) 
            ar.add_info( {'final_distortion_parameter' : self.cfg['param']['final_distortion_parameter'] } ) 
            ar.add_info( {'distance_point_line_max_hough' : self.cfg['param']['distance_point_line_max_hough'] } ) 
            ar.add_info( {'angle_point_orientation_max_difference' : self.cfg['param']['angle_point_orientation_max_difference'] } ) 
            ar.add_file("output_canny.png", info="Canny", compress=False ) 
            ar.add_file("output_hough.png", info="Hough", compress=False ) 
            ar.add_file("output_corrected_image.png", info="Output", compress=False ) 
            ar.add_file("input_0.png", info="Input", compress=False ) 
            ar.add_info( {'od1' : self.cfg['param']['od1'] } ) 
            ar.add_info( {'od2' : self.cfg['param']['od2'] } ) 
            ar.add_info( {'od3' : self.cfg['param']['od3'] } ) 
            ar.add_info( {'od4' : self.cfg['param']['od4'] } ) 
            ar.add_info( {"run time" : self.cfg['info']['run_time']} )
            ar.save()

        return self.tmpl_out("run.html")



    @cherrypy.expose
    @init_app
    def result(self, error_nomatch=None):
        """
        display the algo results
        """
        if error_nomatch:
            return self.tmpl_out("result_nomatch.html")
        else:             return self.tmpl_out("result.html" )
