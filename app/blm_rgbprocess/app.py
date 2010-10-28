"""
rgbprocess ipol demo web app
"""
# pylint: disable=C0103

from lib import base_app
from lib import build
from lib import http
from lib import index_dict
from lib import image
from lib.misc import get_check_key, ctime
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time

class app(base_app):
    """ rgbprocess app """

    title = "RGB process"

    input_nb = 1
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = True

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
            + "blm_color_dimensional_filtering/rgbprocess.tar.gz"
        tgz_file = os.path.join(self.dl_dir, "rgbprocess.tar.gz")
        prog_file = os.path.join(self.bin_dir, "rgbprocess")
        log_file = os.path.join(self.base_dir, "build.log")
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
            build.run("make -C %s rgbprocess"
                      % os.path.join(self.src_dir, "rgbprocess")
                      + " CXX='ccache c++' -j4", stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(os.path.join(self.src_dir, 
                                     "rgbprocess", "rgbprocess"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #
    # PARAMETER HANDLING
    #

    @cherrypy.expose
    @get_check_key
    def params(self, newrun=False, msg=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

        return self.tmpl_out("params.html", msg=msg,
                             input=[self.key_url + 'input_0.png'])
 

    @cherrypy.expose
    @get_check_key
    def select_subimage_first(self, newrun=False, msg=None):
        
        # configure first point selection

        return self.tmpl_out("select_subimage_first.html", msg=msg,
                             input=[self.key_url + 'input_0.png'])


    @cherrypy.expose
    @get_check_key
    def select_subimage_second(self, newrun=False, msg=None, x=None, y=None):
 
	print "x=", x
	print "y=", y
	#save upper-left corner coordinates
        try:
            params_file = index_dict(self.key_dir)
            params_file['subimageFirst'] = {'firstx' : int(x), 'firsty' : int(y)}
            params_file.save()
        except:
            return self.error(errcode='badFirstPoint',
                              errmsg="Wrong first point selection")

	# draw a red cross at the first subimage corner (upper-left)
        # on the input image
        try:
            im = image(os.path.join(self.key_dir, 'input_0.png'))
        except IOError:
            raise cherrypy.HTTPError(400, # Bad Request
                                         "Bad input file")

	y1=int(y)
	y2=int(y)
	if int(x) >= 2 :
	  x1=int(x)-2
	else :
	  x1=0
	if int(x)+2 < im.size[0] :
	  x2=int(x)+2
	else :
	  x2=im.size[0]
 
	x3=int(x)
	x4=int(x)
	if int(y) >= 2 :
	  y3=int(y)-2
	else :
	  y3=0
	if int(y)+2 < im.size[1] :
	  y4=int(y)+2
	else :
	  y4=im.size[1]

	im.draw_line((x1, y1, x2, y2), color="red")
	im.draw_line((x3, y3, x4, y4), color="red")


        im.save(os.path.join(self.key_dir, 'input_0First.png'))


	# configure second point selection
        return self.tmpl_out("select_subimage_second.html", msg=msg,
                             input=[self.key_url + 'input_0First.png'])

    # run() is defined here,
    # because the parameters validation depends on the algorithm
    @cherrypy.expose
    @get_check_key
    def run(self, x=None, y=None):
        """
        params handling and run redirection
        as a special case, we have no parameter to check and pass
        """

	#crop subimage, if selected
        if (x == None) or (y == None) :
	  #no subimage selected
           im = image(os.path.join(self.key_dir, 'input_0.png'))
           im.save(os.path.join(self.key_dir, 'input_00.png'))
	else :
	  #crop and resize
           im = image(os.path.join(self.key_dir, 'input_0.png'))

	   #read upper-left corner coordinates
           params_file = index_dict(self.key_dir)
           x1 = int(params_file['subimageFirst']['firstx'])
           y1 = int(params_file['subimageFirst']['firsty'])

	   #crop
           im.crop((x1, y1, int(x), int(y)))

	   #resize, if necessary
	   if (im.size[0] < 400) and (im.size[1] < 400) :
	     sX=400
	     sY=400
 	     if im.size[0] > im.size[1] :
		sY=int(float(im.size[1])/float(im.size[0])*400)
	     else :
		sX=int(float(im.size[0])/float(im.size[1])*400)
             im.resize((sX, sY), method="bilinear")

	   # save result
           im.save(os.path.join(self.key_dir, 'input_00.png'))



        http.refresh(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html",
                             input=[self.key_url + 'input_00.png'])

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
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        """
        Version 1

        p = self.run_proc(['rgbprocess', 'filter',
                           'input_0.png', 'output.png'])
        p2 = self.run_proc(['rgbprocess', 'rmisolated',
                            'input_0.png', 'output_0.png'])
        self.wait_proc(p2)
        wOut=256
        hOut=256
        #p3 = self.run_proc(['rgbprocess', 'pcaviews',
        #                    'output_0.png', 'output_0.png',
        #                    'view12.png', 'view13.png', 'view23.png',
        #                    str(wOut), str(hOut)])
        p3 = self.run_proc(['rgbprocess', 'pcaviewsB',
                            'output_0.png', 'output_0.png',
                            'view123.png', str(wOut), str(hOut)])
        self.wait_proc(p)
        p4 = self.run_proc(['rgbprocess', 'rmisolated',
                            'output.png', 'output_1.png'])
        self.wait_proc(p4)
        #p5 = self.run_proc(['rgbprocess', 'pcaviews',
        #                    'output_1.png', 'input_0.png',
        #                    'outview12.png', 'outview13.png', 'outview23.png',
        #                    str(wOut), str(hOut)])
        p5 = self.run_proc(['rgbprocess', 'pcaviewsB',
                            'output_1.png', 'output_0.png',
                            'outview123.png', str(wOut), str(hOut)])
        p6 = self.run_proc(['rgbprocess', 'density',
                            'output_1.png', 'output_0.png',
                            'dstview123.png', str(wOut), str(hOut)])
        self.wait_proc(p3)
        self.wait_proc(p5)
        self.wait_proc(p6)
        return
        """

        """
        Version 2

        p = self.run_proc(['rgbprocess', 'rmisolated',
                           'input_0.png', 'input_1.png'],
                          stdout=stdout, stderr=stdout)
        self.wait_proc(p, timeout)
        wOut = 256
        hOut = 256
        p2 = self.run_proc(['rgbprocess', 'pcaviewsB',
                            'input_1.png', 'input_1.png', 'view123.png',
                            str(wOut), str(hOut)], stdout=stdout, stderr=stdout)
        p3 = self.run_proc(['rgbprocess', 'filter',
                            'input_1.png', 'output_1.png'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc(p3, timeout)
        p4 = self.run_proc(['rgbprocess', 'pcaviewsB', 
                            'output_1.png', 'input_1.png', 'outview123.png',
                            str(wOut), str(hOut)], stdout=stdout, stderr=stdout)
        p5 = self.run_proc(['rgbprocess', 'density',
                            'output_1.png', 'input_1.png', 'dstview123.png',
                            str(wOut), str(hOut)], stdout=stdout, stderr=stdout)
        p6 = self.run_proc(['rgbprocess', 'combineimages',
                            'output_1.png', 'input_0.png', 'output_2.png'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc([p2, p4, p5, p6], timeout)
	"""

	""" 
	Version 3

	"""

	print "remove isolated"
        p1 = self.run_proc(['rgbprocess', 'rmisolated', 'input_00.png', 'input_1.png'], stdout=stdout, stderr=stdout)

	print "view parameters"
        p2 = self.run_proc(['rgbprocess', 'RGBviewsparams', 'RGBviewsparams.txt'], stdout=stdout, stderr=stdout)
        self.wait_proc([p1, p2], timeout)

	print "LLP2"
        p3 = self.run_proc(['rgbprocess', 'filter', 'input_1.png', 'output_1.png'],
                           stdout=stdout, stderr=stdout)
        wOut = 256
        hOut = 256
	displayDensity=0
	print "original views"
        p4 = self.run_proc(['rgbprocess', 'RGBviews', 'input_1.png', 'RGBviewsparams.txt', 'inRGB', 
			   str(wOut), str(hOut), str(displayDensity)], stdout=stdout, stderr=stdout)
        self.wait_proc([p3, p4], timeout)


	print "filtered views"
        p5 = self.run_proc(['rgbprocess', 'RGBviews', 'output_1.png', 'RGBviewsparams.txt', 'outRGB', 
			   str(wOut), str(hOut), str(displayDensity)], stdout=stdout, stderr=stdout)
 	displayDensity=1

	print "density views"
        p6 = self.run_proc(['rgbprocess', 'RGBviews', 'output_1.png', 'RGBviewsparams.txt', 'dstyRGB', 
			   str(wOut), str(hOut), str(displayDensity)], stdout=stdout, stderr=stdout)
        self.wait_proc([p5, p6], timeout)

 	print "combine views"
        p7 = self.run_proc(['rgbprocess', 'combineviews', 'RGBviewsparams.txt', 'inRGB', 'outRGB', 'dstyRGB', 'view'], 
			   stdout=stdout, stderr=stdout)

	print "merge images"
        p8 = self.run_proc(['rgbprocess', 'mergeimages', 'output_1.png', 'input_00.png', 'output_2.png'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc([p7, p8], timeout)


    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # run the algorithm
        stdout = open(os.path.join(self.key_dir, 'stdout.txt'), 'w')
        try:
            run_time = time.time()
            self.run_algo(stdout=stdout)
            run_time = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')
        self.log("input processed")

        """
        Version 1

        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png')],
                #'inputViews' : [self.url('tmp', 'view12.png'),
                #self.url('tmp', 'view13.png'),
                #self.url('tmp', 'view23.png')],
                'inputViews' : [self.url('tmp', 'view123.png')],
                'output' : [self.url('tmp', 'output.png')],
                #'outputViews' : [self.url('tmp', 'outview12.png'),
                #                 self.url('tmp', 'outview13.png'),
                #                 self.url('tmp', 'outview23.png')]
                #'outputViews' : [self.url('tmp', 'outview123.png')]
                'outputViews' : [self.url('tmp', 'outview123.png'),
                                 self.url('tmp', 'dstview123.png')]
                }
        """

        """
        Version 2

        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')],
                'inputViews' : [self.url('tmp', 'view123.png')],
                'output' : [self.url('tmp', 'output_2.png')],
                'outputViews' : [self.url('tmp', 'outview123.png'),
                                 self.url('tmp', 'dstview123.png')]
                }

	"""

        """
        Version 3
	"""

        return self.tmpl_out("result3.html",
                             input=[self.key_url + 'input_00.png'],
                             output=[self.key_url + 'output_2.png'],
                             views=[self.key_url + 'view_%i.png' % i 
                                    for i in range(100, 127)],
                            run_time="%0.2f" % run_time, 
			    sizeY="%i" \
                                 % image(os.path.join(self.key_dir,
                                                      'input_00.png')).size[1])
