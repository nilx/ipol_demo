# -*- coding: utf-8 -*-
"""
Computing Visual Correspondence with Occlusions using Graph Cuts demo interaction script
"""

from base_demo import app as base_app
from lib import get_check_key, http_redirect_303, app_expose, index_dict, image
from lib import TimeoutError
import os.path
import time

class app(base_app):
    """ template demo app """
    
    title = "Computing Visual Correspondence with Occlusions using Graph Cuts"
    description = """V. Kolmogorov and R. Zabih's method tries to minimize an 
    energy defined on all possible configurations.<br />
    Please select two images; color images will be converted into gray
    level."""

    input_nb = 2 # number of input images
    input_max_pixels = None # max size (in pixels) of an input image
    input_max_method = 'zoom'
    input_dtype = '3x8i' # input image expected data type    
    input_ext = '.ppm'   # input image expected extension (ie file format)    
    is_test = True       # switch to False for deployment
    allow_upload = False

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

    @get_check_key
    def run(self, **kwargs):
        """
        params handling and run redirection
        """
        # save and validate the parameters
        try:
            params_file = index_dict(self.path('tmp'))
            params_file['params'] = {}
#            params_file['params'] = {'_K' : float(kwargs['K']),
#                                     '_lambda' : float(kwargs['lambda']) }
            params_file.save()
        except:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        # redirect to the result page
        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')]}
        return self.tmpl_out("run.html", urld=urld)
    run.exposed = True

    def run_algo(self, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        params_file = index_dict(self.path('tmp'))
        if 'K_auto' not in params_file['params']:
            # create autoK.conf file
            kfile = open(self.path('tmp', 'autoK.conf'),'w')
            kfile.write("LOAD_COLOR input_0.ppm input_1.ppm\n")
            kfile.write("SET disp_range -15 0 0 0\n")
            kfile.close()

            # run autoK
            stdout = open(self.path('tmp', 'stdout.txt'), 'w')
            p = self.run_proc(['autoK', 'autoK.conf'],
                              stdout=stdout, stderr=stdout)
            self.wait_proc(p, timeout)
            stdout.close()
        
            # get K from stdout
            stdout = open(self.path('tmp', 'stdout.txt'), 'r')
            K_auto = float(stdout.readline()) 
            stdout.close()
            params_file = index_dict(self.path('tmp'))
            params_file['params']['K_auto'] = K_auto
            params_file.save()

        # split the input images
        nproc = 6   # number of slices
        margin = 6  # overlap margin 

        input0_img = image(self.path('tmp', 'input_0.ppm') )
        input0_fnames = input0_img.split(nproc, margin=margin,
                                         fname=self.path('tmp', 
                                                         'input0_split.ppm'))
        input1_img = image( self.path('tmp', 'input_1.ppm') )
        input1_fnames = input1_img.split(nproc, margin=margin,
                                         fname=self.path('tmp', 
                                                         'input1_split.ppm'))
        output_fnames = ['output_split.__%0.2i__.png' % n
                         for n in range(nproc)]
        plist = []
        for n in range(nproc):
            # creating the conf files (one per process)
            conf_file = open(self.path('tmp', 'match_%i.conf' % n),'w')
            conf_file.write("LOAD_COLOR %s %s\n"
                            % (input0_fnames[n], input1_fnames[n]))
            conf_file.write("SET disp_range -15 0 0 0\n")
            conf_file.write("SET iter_max 30\n")
            conf_file.write("SET randomize_every_iteration\n")
            if 'K' in params_file['params']:
                conf_file.write("SET K %f\n"
                                % float(params_file['params']['K']))
            else:
                conf_file.write("SET K %f\n"
                                % float(params_file['params']['K_auto']))
            if 'lambda' in params_file['params']:
                conf_file.write("SET lambda %f\n"
                                % float(params_file['params']['lambda']))
            else:
                conf_file.write("SET lambda %f\n" 
                                % float(params_file['params']['K_auto'] / 5))
            conf_file.write("KZ2\n")
            conf_file.write("SAVE_X_SCALED %s\n" % output_fnames[n])
            conf_file.close()
            # run each process
            plist.append(self.run_proc(['match', 'match_%i.conf' %n]))
        self.wait_proc(plist, timeout)

        # join all the partial results into a global one
        output_img_list = [image(self.path('tmp', output_fnames[n]))
                           for n in range(nproc)]
        output_img = image()
        output_img.join(output_img_list, margin=margin)
        output_img.save(self.path('tmp', fname='disp_output.ppm'))

        # delete the strips
        for fname in input0_fnames + input1_fnames:
            os.unlink(fname)
        for fname in output_fnames:
            os.unlink(self.path('tmp', fname))
        return

    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # no parameters
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout)
            run_time = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="""
The algorithm took more than %i seconds and had to be interrupted.
Try again with simpler images.""" % self.timeout)
        except RuntimeError:
            return self.error(errcode='retime',
                              errmsg="""
The program ended with a failure return code,
something must have gone wrong""")
        self.log("input processed")
        
        params_file = index_dict(self.path('tmp'))

        im = image(self.path('tmp', 'disp_output.ppm'))
        im.save(self.path('tmp', 'dispmap.png'))
        
        urld = {'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')],
                'output' : [self.url('tmp', 'dispmap.png')]}
                
        return self.tmpl_out("result.html", urld=urld,
                             run_time="%0.2f" % run_time)
    result.exposed = True

