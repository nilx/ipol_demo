"""
gamma correction ipol demo web app
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
import PIL.Image


class app(base_app):
    """ gamma correction app """

    title = "Gamma Correction"

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
            + "gl_gamma_correction/gamma_correction.tar.gz"
        tgz_file = self.dl_dir + "gamma_correction.tar.gz"
        prog_file = self.bin_dir + "gammacorrection"
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
            build.run("make -j4 -C %s gammacorrection"
                      % (self.src_dir + "gamma_correction"),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir 
                        + os.path.join("gamma_correction", "gammacorrection"), prog_file)
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

    def default_gamma(self, channel):
	"""
	compute the default gamma value for the channel
	with the formula: gamma=2^{(average(channel)-127.5)/127.5}
	"""
        #open the image
        im = image(self.work_dir + 'input_0.sel.png')
        # check image mode
        if im.im.mode not in ("L", "RGB"):
            raise ValueError("Unsuported image mode for histogram computation")

	avg=0.0
        pix = im.im.load()
        if im.im.mode == "RGB":
	    if channel == 'I':
              # compute grey level image: I = (R + G + B) / 3
              imgray = PIL.Image.new('L', im.size)
              pixgray = imgray.load()
              for y in range(0, im.size[1]):
                  for x in range(0, im.size[0]):
                      pixgray[x, y] = (pix[x, y][0] + pix[x, y][1] +
                                       pix[x, y][2]) / 3

	      #compute average value
              for y in range(0, im.size[1]):
                  for x in range(0, im.size[0]):
		      avg+=float(pixgray[x, y])
	    else:
	      ch = {"R":0, "G":1, "B":2}
	      #compute average value
              for y in range(0, im.size[1]):
                  for x in range(0, im.size[0]):
		      avg+=float(pix[x, y][ch[channel]])
	else:
	  #compute average value
          for y in range(0, im.size[1]):
              for x in range(0, im.size[0]):
		  avg+=float(pix[x, y])

	avg=avg/(float(im.size[0])*float(im.size[1]))	
	gamma=pow(2.0, (avg-127.5)/127.5)

	print "channel=%s avg=%2.2f gamma=%2.2f" % (channel, avg, gamma)

	return gamma
	
	

    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, gammaR=None, gammaG=None, gammaB=None, gammaI=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

        return self.tmpl_out("params1.html", msg=msg, gammaR=gammaR, gammaG=gammaG, gammaB=gammaB, gammaI=gammaI)

    @cherrypy.expose
    @init_app
    def params2(self, newrun=False, msg=None, x0=None, y0=None, x1=None, y1=None, gammaR=None, gammaG=None, gammaB=None, gammaI=None):
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
	if gammaR == None:
	  #compute default value
	  gammaR=self.default_gamma(channel='R')
	  #get two decimal precission
	  gammaR=int(gammaR*100)
	  gammaR=float(gammaR)*0.01
	else:
	  gammaR=float(gammaR)

	if gammaG == None:
	  #compute default value
	  gammaG=self.default_gamma(channel='G')
	  #get two decimal precission
	  gammaG=int(gammaG*100)
	  gammaG=float(gammaG)*0.01
	else:
	  gammaG=float(gammaG)

	if gammaB == None:
	  #compute default value
	  gammaB=self.default_gamma(channel='B')
	  #get two decimal precission
	  gammaB=int(gammaB*100)
	  gammaB=float(gammaB)*0.01
	else:
	  gammaB=float(gammaB)

	if gammaI == None:
	  #compute default value
	  gammaI=self.default_gamma(channel='I')
	  #get two decimal precission
	  gammaI=int(gammaI*100)
	  gammaI=float(gammaI)*0.01
	else:
	  gammaI=float(gammaI)

	
        return self.tmpl_out("params2.html", msg=msg, gammaR=gammaR, gammaG=gammaG, gammaB=gammaB, gammaI=gammaI)



    @cherrypy.expose
    @init_app
    def rectangle(self, action=None, x=None, y=None, x0=None, y0=None, gammaR=None, gammaG=None, gammaB=None, gammaI=None):
        """
        select a rectangle in the image
        """
        if action == 'continue':
	    #use whole image, go to the parameter page with the key
	    if (gammaR != None) and (gammaG != None) and (gammaB != None) and (gammaI != None):
              http.redir_303(self.base_url + "params2?key=%s&gammaR=%s&gammaG=%s&gammaB=%s&gammaI=%s" % (self.key, gammaR, gammaG, gammaB, gammaI))
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

                return self.tmpl_out("params1.html", x0=x, y0=y, gammaR=gammaR, gammaG=gammaG, gammaB=gammaB, gammaI=gammaI)
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
		if (gammaR != None) and (gammaG != None) and (gammaB != None) and (gammaI != None):
                  http.redir_303(self.base_url + "params2?key=%s&x0=%s&y0=%s&x1=%s&y1=%s&gammaR=%s&gammaG=%s&gammaB=%s&gammaI=%s" % (self.key, x0, y0, x1, y1, gammaR, gammaG, gammaB, gammaI))
		else:
                  http.redir_303(self.base_url + "params2?key=%s&x0=%s&y0=%s&x1=%s&y1=%s" % (self.key, x0, y0, x1, y1))
            return

    @cherrypy.expose
    @init_app
    def wait(self, gammaR=None, gammaG=None, gammaB=None, gammaI=None):
        """
        params handling 
        """
 	#save parameters
        try:
          self.cfg['param'] = {'gammar' : float(gammaR), 
			       'gammag' : float(gammaG),
			       'gammab' : float(gammaB),
			       'gammai' : float(gammaI)}
          self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                             errmsg="The parameters must be numeric.")

        """
        run redirection
        """
        http.refresh(self.base_url + 'run?key=%s' % (self.key))
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        # read the parameters
        gammaR = self.cfg['param']['gammar']
        gammaG = self.cfg['param']['gammag']
        gammaB = self.cfg['param']['gammab']
        gammaI = self.cfg['param']['gammai']
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(gammaR, gammaG, gammaB, gammaI, stdout=stdout, timeout=self.timeout)
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
            ar.add_info({"gammaR": gammaR})
            ar.add_info({"gammaR": gammaR})
            ar.add_info({"gammaR": gammaR})
            ar.add_info({"gammaI": gammaI})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, gammaR, gammaG, gammaB, gammaI, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

	#gamma correction of R, G and B channels
	option=1
        p1 = self.run_proc(['gammacorrection', 'input_0.sel.png', 'output_1.png', str(option), str(gammaR), str(gammaG), str(gammaB)],
                           stdout=stdout, stderr=None)

	#gamma correction of intensity channel
	option=2
        p2 = self.run_proc(['gammacorrection', 'input_0.sel.png', 'output_2.png', str(option), str(gammaI)],
                           stdout=stdout, stderr=None)
        self.wait_proc([p1, p2], timeout)

	
	#Compute histograms of images
        im1 = image(self.work_dir + 'input_0.sel.png')
        im2 = image(self.work_dir + 'output_1.png')
        im3 = image(self.work_dir + 'output_2.png')
        #compute maximum of histogram values
        maxH1=im1.max_histogram(option="all")
        maxH2=im2.max_histogram(option="all")
        maxH3=im3.max_histogram(option="all")
        maxH=max([maxH1, maxH2, maxH3])
        #draw all the histograms using the same reference maximum
        im1.histogram(option="all", maxRef=maxH)
        im1.save(self.work_dir + 'input_0_hist.png')
        im2.histogram(option="all", maxRef=maxH)
        im2.save(self.work_dir + 'output_1_hist.png')
        im3.histogram(option="all", maxRef=maxH)
        im3.save(self.work_dir + 'output_2_hist.png')



    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """

        # read the parameters
        gammaR = self.cfg['param']['gammar']
        gammaG = self.cfg['param']['gammag']
        gammaB = self.cfg['param']['gammab']
        gammaI = self.cfg['param']['gammai']
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

	sizeY=image(self.work_dir + 'input_0.sel.png').size[1]
	sizeYhist=image(self.work_dir + 'input_0_hist.png').size[1]
	#add 50 pixels to the histogram size to take margin into account
	sizeYmax=max(sizeY, sizeYhist+50)

        return self.tmpl_out("result.html", gammaR=gammaR, gammaG=gammaG, gammaB=gammaB, gammaI=gammaI,
 			     x0=x0, y0=y0, x1=x1, y1=y1, sizeY="%i" % sizeYmax)



