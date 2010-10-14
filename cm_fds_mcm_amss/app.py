"""
mcm_amss ipol demo web app
"""

from base_demo import app as base_app
from lib import get_check_key, http_redirect_303
from lib import TimeoutError, index_dict
from lib import index_dict
from lib import image
import os.path
import time
import shutil
import cherrypy


class app(base_app):
    """ mcm_amss app """

    title = "MCM-AMSS"
    description = "Image filtering with MCM and AMSS EDPs"

    input_nb = 1
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.tiff' # input image expected extension (ie file format)
    display_ext = '.png' # displayed image extention (ie. file format)
    is_test = True;

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # TODO : simplify
        # index() is generic
        base_app.index.im_func.exposed = True
        # input_xxx() are modified from the template
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True


    #
    # INPUT STEP
    #

    # input_select() is defined here,
    # because it calls to a non-standard params function (params_grid())
    def input_select(self, input_id, **kwargs):
        """
        use the selected available input images
        """
        self.new_key()
        input_dict = index_dict(self.path('input'))
        fnames = input_dict[input_id]['files'].split()
        for i in range(len(fnames)):
            shutil.copy(self.path('input', fnames[i]),
                        self.path('tmp', 'input_%i' % i))
        msg = self.process_input()
        self.log("input selected : %s" % input_id)
        # jump to the params page
        return self.params_grid(key=self.key, grid_step="150", msg=msg)
    input_select.exposed = True

    # input_upload() is defined here,
    # because it calls to a non-standard params function (params_grid())
    def input_upload(self, **kwargs):
        """
        use the uploaded input images
        """
        self.new_key()
        for i in range(self.input_nb):
            file_up = kwargs['file_%i' % i]
            file_save = file(self.path('tmp', 'input_%i' % i), 'wb')
            if '' == file_up.filename:
                # missing file
                raise cherrypy.HTTPError(400, # Bad Request
                                         "Missing input file")
            size = 0
            while True:
                # TODO : larger data size
                data = file_up.file.read(128)
                if not data:
                    break
                size += len(data)
                if size > self.input_max_weight:
                    # file too heavy
                    raise cherrypy.HTTPError(400, # Bad Request
                                             "File too large, " +
                                             "resize or use better compression")
                file_save.write(data)
            file_save.close()
        msg = self.process_input()
        self.log("input uploaded")
        # jump to the params page
        return self.params_grid(key=self.key, grid_step="150", msg=msg)
    input_upload.exposed = True

    #
    # PARAMETER HANDLING
    #


    def draw_grid(self, grid_step):
        """
        draw a grid on the input image
        """

	print "input image path:", self.path('tmp', 'input_0' + self.input_ext)
        try:
            im = image(self.path('tmp', 'input_0' + self.input_ext))
        except IOError:
            raise cherrypy.HTTPError(400, # Bad Request
                                         "Bad input file")

	#vertical lines
	y1=0
	y2=im.size[1]
	for x1 in range(0, im.size[0], grid_step):
	  im.draw_line((x1, y1, x1, y2))

	#horizontal lines
	x1=0
	x2=im.size[0]
	for y1 in range(0, im.size[1], grid_step):
	  im.draw_line((x1, y1, x2, y1))

        im.save(self.path('tmp', 'input_1' + self.input_ext))
        im.save(self.path('tmp', 'input_1' + self.display_ext))



    @get_check_key
    def params_grid(self, newrun=False, grid_step="150", msg=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

	self.draw_grid(int(grid_step))

        urld = {'run' : self.url('run'),
		'params_grid' : self.url('params_grid'),
                'input' : [self.url('tmp', 'input_1' + self.display_ext)]}
        return self.tmpl_out("params.html", urld=urld, msg=msg)
    params_grid.exposed = True

    #
    # EXECUTION AND RESULTS
    #

    # run() is defined here,
    # because the parameters validation depends on the algorithm
    @get_check_key
    def run(self, scaleR="1.0", grid_step="150", x=None, y=None):
        """
        params handling and run redirection
        """
        # save and validate the parameters
	if (x == None) or (y == None) :
	  x=0
	  y=0

	print "x=", x
	print "y=", y
	print "grid_step=", int(grid_step)
	print "scaleR=", float(scaleR)

        try:
            params_file = index_dict(self.path('tmp'))
            params_file['params'] = {'scaler' : float(scaleR),
                                     'grid_step' : int(grid_step),
				     'gridx' : int(x),
				     'gridy' : int(y)}
            params_file.save()
        except:
            return self.error(errcode='badparams',
                              errmsg="Wrong input parameters")

	#Select image to process
	gridX=int(x)
	gridY=int(y)
	gridStep=int(grid_step)
	if (gridX == 0) and (gridY == 0) :
	  #process whole image 
	  #save input image as input_2
          im = image(self.path('tmp', 'input_0' + self.input_ext))
          im.save(self.path('tmp', 'input_2' + self.input_ext))
          im.save(self.path('tmp', 'input_2' + self.display_ext))
	else :
	  #select subimage 
          im = image(self.path('tmp', 'input_0' + self.input_ext))
	  x1=(gridX/gridStep)*gridStep
	  y1=(gridY/gridStep)*gridStep
	  x2=x1+gridStep
	  if x2 > im.size[0] :
	    x2=im.size[0]
	  y2=y1+gridStep
	  if y2 > im.size[1] :
	    y2=im.size[1]
	  im.crop((x1, y1, x2, y2))
	  #print "crop:", x1, y1, x2, y2
	  #set default image size
	  im.resize((600, 600), method="nearest")
          im.save(self.path('tmp', 'input_2' + self.input_ext))
          im.save(self.path('tmp', 'input_2' + self.display_ext))


        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'next_step' : self.url('result'),
                'input' : [self.url('tmp', 'input_2' + self.display_ext)]}
        return self.tmpl_out("run.html", urld=urld)
    run.exposed = True

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

	#Process image
	p1=self.run_proc(['mcm', str(scaleR), self.path('tmp', 'input_2' + self.input_ext), self.path('tmp', 'output_MCM' + self.input_ext)])
	p2=self.run_proc(['amss', str(scaleR), self.path('tmp', 'input_2' + self.input_ext), self.path('tmp', 'output_AMSS' + self.input_ext)])
	self.wait_proc([p1, p2])
        im = image(self.path('tmp', 'output_MCM' + self.input_ext))
        im.save(self.path('tmp', 'output_MCM' + self.display_ext))
        im = image(self.path('tmp', 'output_AMSS' + self.input_ext))
        im.save(self.path('tmp', 'output_AMSS' + self.display_ext))


    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # read the parameters
        params_file = index_dict(self.path('tmp'))
        scaleR = float(params_file['params']['scaler'])
        grid_step = int(params_file['params']['grid_step'])
        gridX = int(params_file['params']['gridx'])
        gridY = int(params_file['params']['gridy'])
 
       # run the algorithm
        stdout = open(self.path('tmp', 'stdout.txt'), 'w')
        try:
            run_time = time.time()
            self.run_algo(scaleR, stdout=stdout)
            run_time = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')
        self.log("input processed")

        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_2' + self.display_ext)],
                'output' : [self.url('tmp', 'output_MCM' + self.display_ext), self.url('tmp', 'output_AMSS' + self.display_ext)]
		}


        return self.tmpl_out("result.html", urld=urld, run_time="%0.2f" % run_time)
    result.exposed = True

