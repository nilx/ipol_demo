"""
local color correction ipol demo web app
"""
# pylint: disable=C0103

from lib import base_app, build, http, image
from lib.misc import mtime
from lib.misc import prod
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time

class app(base_app):
    """ local color correction app """

    title = "Local Color Correction"

    input_nb = 1
    input_max_pixels = 700 * 700 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = False

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

    def build(self):
        """
        program build/update
        """
        # store common file path in variables
        tgz_url = "https://edit.ipol.im/edit/algo/" \
            + "g_localcolorcorrection/LCC.tar.gz"
        tgz_file = self.dl_dir + "LCC.tar.gz"
        prog_file = self.bin_dir + "localcolorcorrection"
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and mtime(tgz_file) < mtime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s localcolorcorrection"
                      % (self.src_dir + "LCC"),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir 
                        + os.path.join("LCC", "localcolorcorrection"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


    #
    # PARAMETER HANDLING
    #


    def select_subimage(self, x0, y0, x1, y1):
	"""
	cut subimage from original image
	"""
        # draw selected rectangle on the image
        imgS = image(self.work_dir + 'input_0.png')
        imgS.draw_line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], color="red")
        imgS.draw_line([(x0+1, y0+1), (x1-1, y0+1), (x1-1, y1-1), (x0+1, y1-1), (x0+1, y0+1)], color="white")
        imgS.save(self.work_dir + 'input_0s.png')
        # crop the image
	# try cropping from the original input image (if different from input_0)
	im0 = image(self.work_dir + 'input_0.orig.png')
	(dx0, dy0) = im0.size
        img = image(self.work_dir + 'input_0.png')
        (dx, dy) = img.size
	if (dx != dx0) :
           z=float(dx0)/float(dx)
           im0.crop((int(x0*z), int(y0*z), int(x1*z), int(y1*z)))
           # resize if cropped image is too big
           if self.input_max_pixels and prod(im0.size) > (self.input_max_pixels):
              im0.resize(self.input_max_pixels, method="antialias")
           img=im0
	else :
           img.crop((x0, y0, x1, y1))
	# save result
        img.save(self.work_dir + 'input_0.sel.png')
	return


    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, x0=None, y0=None, x1=None, y1=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
	if x0:
	  self.select_subimage(int(x0), int(y0), int(x1), int(y1))
        return self.tmpl_out("params.html", msg=msg, x0=x0, y0=y0, x1=x1, y1=y1)


    @cherrypy.expose
    @init_app
    def rectangle(self, action=None, r=None, x=None, y=None, x0=None, y0=None):
        """
        params handling 
        """
        # save and validate the parameters
	if (int(r) < 0) or (int(r) > 1000) :
	  return self.error(errcode='badparams',
                              errmsg="r must be an integer value between 0 and 1000")

        """
        select a rectangle in the image
        """
        if action == 'run':
	    if x == None:
	        #save parameter
                try:
                  self.cfg['param'] = {'r' : int(r)}
                  self.cfg.save()
                except ValueError:
                  return self.error(errcode='badparams',
                                    errmsg="The parameters must be numeric.")
	    else:
		#save parameters
        	try:
            	  self.cfg['param'] = {'r' : int(r), 
				       'x0' : int(x0),
				       'y0' : int(y0),
				       'x1' : int(x),
				       'y1' : int(y)}
            	  self.cfg.save()
        	except ValueError:
            	  return self.error(errcode='badparams',
                                    errmsg="The parameters must be numeric.")
	
            # use the whole image if no subimage is available
            try:
                img = image(self.work_dir + 'input_0.sel.png')
            except IOError:
                img = image(self.work_dir + 'input_0.png')
                img.save(self.work_dir + 'input_0.sel.png')

            # go to the wait page, with the key
            http.redir_303(self.base_url + "wait?key=%s" % self.key)
            return
        else:
            # use a part of the image
            if x0 == None:
                # first corner selection
                x = int(x)
                y = int(y)
                # draw a cross at the first corner
                img = image(self.work_dir + 'input_0.png')
                img.draw_cross((x, y), size=4, color="white")
                img.draw_cross((x, y), size=2, color="red")
                img.save(self.work_dir + 'input.png')
                return self.tmpl_out("params.html", r=r, x0=x, y0=y)
            else:
                # second corner selection
                x0 = int(x0)
                y0 = int(y0)
                x1 = int(x)
                y1 = int(y)
                # reorder the corners
                (x0, x1) = (min(x0, x1), max(x0, x1))
                (y0, y1) = (min(y0, y1), max(y0, y1))
                assert (x1 - x0) > 0
                assert (y1 - y0) > 0
		#save parameters
        	try:
            	  self.cfg['param'] = {'r' : int(r), 
				       'x0' : x0,
				       'y0' : y0,
				       'x1' : x1,
				       'y1' : y1}
            	  self.cfg.save()
        	except ValueError:
            	  return self.error(errcode='badparams',
                                    errmsg="The parameters must be numeric.")
 		#select subimage
		self.select_subimage(x0, y0, x1, y1)
                # go to the wait page, with the key
                http.redir_303(self.base_url + "wait?key=%s" % self.key)
            return

    @cherrypy.expose
    @init_app
    def wait(self):
        """
        run redirection
        """
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        # read the parameters
        r = self.cfg['param']['r']
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(r, stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
	    print "Run time error"
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="uploaded image")
 	    if (os.path.isfile(self.work_dir + 'input_0s.png') == True) :
		ar.add_file("input_0s.png", info="sub-image selection")
            ar.add_file("input_0.sel.png", info="processed image")
            ar.add_file("output_1.png", info="result image 1 (RGB)")
            ar.add_file("output_2.png", info="result image 2 (I)")
            ar.add_info({"r": r})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, r, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

	print "Start process 1"
	#color correction of R, G and B channels
	option=1
        p1 = self.run_proc(['localcolorcorrection', 'input_0.sel.png', 'output_1.png', str(r), str(option)],
                           stdout=None, stderr=None)

	print "Start process 2"
	#color correction of intensity channel
	option=2
        p2 = self.run_proc(['localcolorcorrection', 'input_0.sel.png', 'output_2.png', str(r), str(option)],
                           stdout=None, stderr=None)
        self.wait_proc([p1, p2], timeout)

	print "End of processing"

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
	print "Display results"

        # read the parameters
        r = self.cfg['param']['r']
        try:
          x0 = self.cfg['param']['x0']
        except KeyError:
	  x0=None
        try:
          y0 = self.cfg['param']['y0']
        except KeyError:
	  y0=None
        try:
          x1 = self.cfg['param']['x1']
        except KeyError:
	  x1=None
        try:
          y1 = self.cfg['param']['y1']
        except KeyError:
	  y1=None

        return self.tmpl_out("result.html", r=r, x0=x0, y0=y0, x1=x1, y1=y1,
                             sizeY="%i" % image(self.work_dir 
                                                + 'input_0.sel.png').size[1])



