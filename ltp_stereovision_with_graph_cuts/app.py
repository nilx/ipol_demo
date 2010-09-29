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

    # run() is defined here,
    # because the parameters validation depends on the algorithm
    @get_check_key
    def run(self, **kwargs):
        """
        params handling and run redirection
        """
        
        # save and validate the parameters
        try:
            params_file = index_dict(self.path('tmp'))
            
            params_file['params'] = {'method' : str(kwargs['method']),  
                                     'x_min' : float(kwargs['x_min']),
                                     'y_min' : float(kwargs['y_min']),
                                     'x_max' : float(kwargs['x_max']),
                                     'y_max' : float(kwargs['y_max']),
                                     'iter_max' : int(kwargs['iter_max']),
                                     'K' : float(kwargs['K']),
                                     'lambda' : float(kwargs['lambd']),
                                     'randomize_every_iteration' : str(kwargs['randomize_every_iteration']),
                                     'x_dispmap' : kwargs['x_dispmap'],
                                     'y_dispmap' : kwargs['y_dispmap']}
            params_file.save()
        except:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        # no parameters
        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')]}
        return self.tmpl_out("run.html", urld=urld)
    run.exposed = True

    # run_algo() is defined here,
    # because it is the actual algorithm execution, hence specific
    # run_algo() is called from result(),
    # with the parameters validated in run()
    def run_algo(self, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        params_file = index_dict(self.path('tmp'))
            

        # Create autoKconf file automaticaly
        kfile = open(self.path('tmp', 'autoKconf'),'w')
        kfile.write("LOAD_COLOR " + self.path('tmp', 'input_0.ppm') + " " 
                                  + self.path('tmp', 'input_1.ppm') + "\n")
        kfile.write("SET disp_range " + str(params_file['params']['x_min']) + " " 
                                      + str(params_file['params']['y_min']) + " " 
                                      + str(params_file['params']['x_max']) + " " 
                                      + str(params_file['params']['y_max']) + " \n")
        kfile.close()

        
        p = self.run_proc(['autoK', 'autoKconf'],
                          stdout=stdout, stderr=stdout)
                         
        self.wait_proc(p, timeout)


##        print "\n\n*********************************\n\n"
        
        istream = open(self.path('tmp', 'stdout.txt'), 'r')
        params_file['params']['K'] = istream.read()
        params_file.save()
##        print params_file['params']['K']

##        print "\n\n*********************************\n\n"

# split the input images
        nproc = 6   # Number of splitted images
        m = 6       # Overlap  

# ............ Then we split the input.png image into 'nproc' parts input_split.__00__.png, input_split.__01__.png, ...
                                      
        input0_img = image( self.path('tmp', 'input_0.ppm') )
        input0_fnames = input0_img.split(nproc, margin=m,
                                       fname=self.path('tmp', 'input0_split.ppm'))

        input1_img = image( self.path('tmp', 'input_1.ppm') )
        input1_fnames = input1_img.split(nproc, margin=m,
                                       fname=self.path('tmp', 'input1_split.ppm'))                                       

# ............ input_fnames is the list of the input file names. Let's also create output_fnames, the list of the output file names.

        outputX_fnames = [self.path('tmp', fname='outputX_split.__%0.2i.png' % n)
                         for n in range(nproc)]

        outputY_fnames = [self.path('tmp', fname='outputY_split.__%0.2i.png' % n)
                         for n in range(nproc)]

# ............ Now we can run the 'nproc' processes in parallel, using once again a list construct.


## # Creating the  settings FILE (one per process)

        for n in range(nproc):
              print n
              
              conf_file = open(self.path('tmp', 'settings' + str(n) ),'w')
              conf_file.write("LOAD_COLOR " + self.path('tmp', input0_fnames[n]) + " " 
                                      + self.path('tmp', input1_fnames[n]) + "\n")
              conf_file.write("SET disp_range " + str(params_file['params']['x_min']) + " " 
                                          + str(params_file['params']['y_min']) + " " 
                                          + str(params_file['params']['x_max']) + " " 
                                          + str(params_file['params']['y_max']) + " \n")                                      
              conf_file.write("SET iter_max " + str(params_file['params']['iter_max']) + " \n")


              if (params_file['params']['randomize_every_iteration'] == ""):
                     conf_file.write("UNSET randomize_every_iteration\n")
              else:
                     conf_file.write("SET randomize_every_iteration\n")

              conf_file.write("SET K " + str(params_file['params']['K']) ) # + " \n")
              conf_file.write("SET lambda " + str(params_file['params']['lambda']) + " \n")
              conf_file.write( params_file['params']['method'] + "\n")

              conf_file.write("SAVE_X_SCALED " +  outputX_fnames[n] + " \n")
              conf_file.write("SAVE_Y_SCALED " +  outputY_fnames[n] + " \n")        
              #conf_file.write("SET lambda       AUTO")
              conf_file.close()              
              
        else:
	      print 'The for loop is over'



        plist = [self.run_proc(['match', 'settings' + str(n)], stdout=stdout, stderr=stdout) 
                 for n in range(nproc)]


# ............ Then we need to wait until all of these processes have finished. We use the wait_proc() flexibility explained in the previous chapter.

        self.wait_proc(plist, timeout)


#All the processes are over, we can now join all the partial results into a global one

        outputX_img_list = [image(outputX_fnames[n]) for n in range(nproc)]
        outputX_img = image()
        outputX_img.join(outputX_img_list, margin=m)
        outputX_img.save(self.path('tmp', fname=params_file['params']['x_dispmap']))

        outputY_img_list = [image(outputY_fnames[n]) for n in range(nproc)]
        outputY_img = image()
        outputY_img.join(outputY_img_list, margin=m)
        outputY_img.save(self.path('tmp', fname=params_file['params']['y_dispmap']))



        #outputX_img_list = [image(input0_fnames[n]) for n in range(nproc)]
        #outputX_img = image()
        #outputX_img.join(outputX_img_list, margin=m)
        #outputX_img.save(self.path('tmp', fname='imagen0joined.ppm'))

        #outputY_img_list = [image(input1_fnames[n]) for n in range(nproc)]
        #outputY_img = image()
        #outputY_img.join(outputY_img_list, margin=m)
        #outputY_img.save(self.path('tmp', fname='imagen1joined.ppm'))

        return

    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # no parameters
        stdout = open(self.path('tmp', 'stdout.txt'), 'w')
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout, stdout=stdout)
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
        
        
        #im = image(self.path('tmp', 'dispmap.ppm'))
        #im.save(self.path('tmp', 'dispmap.png'))        
        
        params_file = index_dict(self.path('tmp'))

        im = image(self.path('tmp', params_file['params']['x_dispmap']))
        im.save(self.path('tmp', 'x_dispmap.png'))
        
        im = image(self.path('tmp', params_file['params']['y_dispmap']))
        im.save(self.path('tmp', 'y_dispmap.png'))        
        
        urld = {#'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')],
                'output' : [self.url('tmp', 'x_dispmap.png'),
                           self.url('tmp', 'y_dispmap.png')]}
                           
                #'output' : self.url('tmp', 'dispmap.png')}
                
                
        stdout = open(self.path('tmp', 'stdout.txt'), 'r')
        return self.tmpl_out("result.html", urld=urld,
                             run_time="%0.2f" % run_time,
                             stdout=stdout.read())
    result.exposed = True

