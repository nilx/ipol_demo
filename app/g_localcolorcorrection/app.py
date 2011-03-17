"""
local color correction ipol demo web app
"""

from lib import base_app, build, http, image
from lib.misc import ctime
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
            and ctime(tgz_file) < ctime(prog_file)):
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
    def params(self, newrun=False, msg=None, r=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

        return self.tmpl_out("params1.html", msg=msg, r=r)

    @cherrypy.expose
    @init_app
    def params2(self, newrun=False, msg=None, x0=None, y0=None, x1=None, y1=None, r=None):
        """
        configure the algo execution
        """

        if newrun:
            self.clone_input()

	if not(x0) or not(y0) or not(x1) or not(y1):
	    #use whole image, go to the parameter page
            img = image(self.work_dir + 'input_0.png')
            img.save(self.work_dir + 'input_0.sel.png')
	else:
	    #save subimage corners
            try:
              self.cfg['subimage'] = {'x0' : x0,
			          'y0' : y0,
			          'x1' : x1,
			          'y1' : y1}
              self.cfg.save()
            except ValueError:
              return self.error(errcode='badparams',
                            errmsg="The parameters must be numeric.")

	    self.select_subimage(int(x0), int(y0), int(x1), int(y1))

	#go to parameter page
	sizeX=image(self.work_dir + 'input_0.sel.png').size[0];
	sizeY=image(self.work_dir + 'input_0.sel.png').size[1];
	if sizeX > sizeY:
	  rmax=sizeY//2-1;
	else:
	  rmax=sizeX//2-1;

	if not(r):
	  r=min(int(0.2*rmax), 40)
	else:
	  r=min(int(r), rmax)

        return self.tmpl_out("params2.html", msg=msg, rmax=rmax, r=r)



    @cherrypy.expose
    @init_app
    def rectangle(self, action=None, r=None, x=None, y=None, x0=None, y0=None):
        """
        select a rectangle in the image
        """
        if action == 'continue':
	    #use whole image, go to the parameter page with the key
	    if r:
              http.redir_303(self.base_url + "params2?key=%s&r=%s" % (self.key, r))
	    else:
              http.redir_303(self.base_url + "params2?key=%s" % (self.key))

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

                return self.tmpl_out("params1.html", x0=x, y0=y, r=r)
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
                # go to the parameter page, with the key and the subimage corners
		if r:
                  http.redir_303(self.base_url + "params2?key=%s&x0=%s&y0=%s&x1=%s&y1=%s&r=%s" % (self.key, x0, y0, x1, y1, r))
		else:
                  http.redir_303(self.base_url + "params2?key=%s&x0=%s&y0=%s&x1=%s&y1=%s" % (self.key, x0, y0, x1, y1))
            return

    @cherrypy.expose
    @init_app
    def wait(self, process=None, r=None, rmax=None):
        """
        params handling 
        """
        if process == 'run global':
	  #set parameter r to compute global color correction
	  r=2*int(rmax)

 	#save parameters
        try:
           self.cfg['param'] = {'r' : int(r),
				'rmax' : int(rmax)}
           self.cfg.save()
        except ValueError:
           return self.error(errcode='badparams',
                             errmsg="The parameters must be numeric.")

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
        rmax = self.cfg['param']['rmax']
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
            ar.add_info({"rmax": rmax})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, r, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

	#color correction of R, G and B channels
	option=1
        p1 = self.run_proc(['localcolorcorrection', 'input_0.sel.png', 'output_1.png', str(r), str(option)],
                           stdout=None, stderr=None)

	#color correction of intensity channel
	option=2
        p2 = self.run_proc(['localcolorcorrection', 'input_0.sel.png', 'output_2.png', str(r), str(option)],
                           stdout=None, stderr=None)
        self.wait_proc([p1, p2], timeout)


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """

        # read the parameters
        r = self.cfg['param']['r']
        rmax = self.cfg['param']['rmax']
        try:
          x0 = self.cfg['subimage']['x0']
        except KeyError:
	  x0=None
        try:
          y0 = self.cfg['subimage']['y0']
        except KeyError:
	  y0=None
        try:
          x1 = self.cfg['subimage']['x1']
        except KeyError:
	  x1=None
        try:
          y1 = self.cfg['subimage']['y1']
        except KeyError:
	  y1=None

	if (r <= rmax):
          return self.tmpl_out("result.html", r=r, x0=x0, y0=y0, x1=x1, y1=y1,
                             sizeY="%i" % image(self.work_dir 
                                                + 'input_0.sel.png').size[1])
	else:
          return self.tmpl_out("result.html", r=None, x0=x0, y0=y0, x1=x1, y1=y1,
                             sizeY="%i" % image(self.work_dir 
                                                + 'input_0.sel.png').size[1])



