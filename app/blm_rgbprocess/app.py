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
        tgz_file = self.dl_dir + "rgbprocess.tar.gz"
        prog_file = self.bin_dir + "rgbprocess"
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
            build.run("make -C %s rgbprocess"
                      % (self.src_dir + "rgbprocess")
                      + " CXX='ccache c++' -j4", stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir 
                        + os.path.join("rgbprocess", "rgbprocess"), prog_file)
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
    def select_subimage_first(self, msg=None):
        """
        first step of the sub-image selection
        """
        # configure first point selection
        return self.tmpl_out("select_subimage_first.html", msg=msg,
                             input=[self.key_url + 'input_0.png'])


    @cherrypy.expose
    @get_check_key
    def select_subimage_second(self, msg=None, x=None, y=None):
        """
        second step of the sub-image selection
        """
        print "x=", x
        print "y=", y
        #save upper-left corner coordinates
        try:
            params_file = index_dict(self.key_dir)
            params_file['subimageFirst'] = {'firstx' : int(x),
                                            'firsty' : int(y)}
            params_file.save()
        except:
            return self.error(errcode='badFirstPoint',
                              errmsg="Wrong first point selection")

        # draw a white-red cross at the first subimage corner (upper-left)
        # on the input image
        try:
            im = image(self.key_dir + 'input_0.png')
        except IOError:
            raise cherrypy.HTTPError(400, # Bad Request
                                         "Bad input file")

	# draw white cross
        y1 = int(y)
        y2 = int(y)
        if int(x) >= 4 :
            x1 = int(x)-4
        else :
            x1 = 0
        if int(x)+4 < im.size[0] :
            x2 = int(x) + 4
        else :
            x2 = im.size[0]
 
        x3 = int(x)
        x4 = int(x)
        if int(y) >= 4 :
            y3 = int(y)-4
        else :
            y3 = 0
        if int(y) + 4 < im.size[1] :
            y4 = int(y) + 4
        else :
            y4 = im.size[1]

        im.draw_line((x1, y1, x2, y2), color="white")
        im.draw_line((x3, y3, x4, y4), color="white")

	# draw red cross
        y1 = int(y)
        y2 = int(y)
        if int(x) >= 2 :
            x1 = int(x)-2
        else :
            x1 = 0
        if int(x)+2 < im.size[0] :
            x2 = int(x) + 2
        else :
            x2 = im.size[0]
 
        x3 = int(x)
        x4 = int(x)
        if int(y) >= 2 :
            y3 = int(y)-2
        else :
            y3 = 0
        if int(y) + 2 < im.size[1] :
            y4 = int(y) + 2
        else :
            y4 = im.size[1]

        im.draw_line((x1, y1, x2, y2), color="red")
        im.draw_line((x3, y3, x4, y4), color="red")

        im.save(self.key_dir + 'input_0First.png')

        # configure second point selection
        return self.tmpl_out("select_subimage_second.html", msg=msg,
                             input=[self.key_url + 'input_0First.png'])

    @cherrypy.expose
    @get_check_key
    def wait(self, x=None, y=None):
        """
        params handling and run redirection
        """
        # crop subimage, if selected
        if (x == None) or (y == None):
            # no subimage selected
            im = image(self.key_dir + 'input_0.png')
            im.save(self.key_dir + 'input_00.png')
        else:
            # crop and resize
            im = image(self.key_dir + 'input_0.png')

            # read upper-left corner coordinates
            params_file = index_dict(self.key_dir)
            x1 = int(params_file['subimageFirst']['firstx'])
            y1 = int(params_file['subimageFirst']['firsty'])

            # crop
	    xmin=min(x1, int(x))
	    ymin=min(y1, int(y))
	    xmax=max(x1, int(x))
	    ymax=max(y1, int(y))
	    
            im.crop((xmin, ymin, xmax, ymax))

            # resize, if necessary
            if (im.size[0] < 400) and (im.size[1] < 400) :
                sX = 400
                sY = 400
                if im.size[0] > im.size[1] :
                    sY = int(float(im.size[1]) / float(im.size[0]) * 400)
                else :
                    sX = int(float(im.size[0]) / float(im.size[1]) * 400)
                im.resize((sX, sY), method="bilinear")

            # save result
            im.save(self.key_dir + 'input_00.png')

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html",
                             input=[self.key_url + 'input_00.png'])

    @cherrypy.expose
    @get_check_key
    def run(self, x=None, y=None):
        """
        algorithm execution
        """
        stdout = open(self.key_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(stdout=stdout)
            params_file = index_dict(self.key_dir)
            params_file['params'] = {}
            params_file['params']['run_time'] = time.time() - run_time
            params_file.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')
        self.log("input processed")


        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html")

    def run_algo(self, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        p1 = self.run_proc(['rgbprocess', 'rmisolated',
                            'input_00.png', 'input_1.png'],
                           stdout=stdout, stderr=stdout)
        p2 = self.run_proc(['rgbprocess', 'RGBviewsparams',
                            'RGBviewsparams.txt'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc([p1, p2], timeout)

        p3 = self.run_proc(['rgbprocess', 'filter',
                            'input_1.png', 'output_1.png'],
                           stdout=stdout, stderr=stdout)
        wOut = 300
        hOut = 300
        displayDensity = 0
        p4 = self.run_proc(['rgbprocess', 'RGBviews',
                            'input_1.png', 'RGBviewsparams.txt', 'inRGB', 
                            str(wOut), str(hOut), str(displayDensity)],
                           stdout=stdout, stderr=stdout)
        self.wait_proc([p3, p4], timeout)

        p5 = self.run_proc(['rgbprocess', 'RGBviews',
                            'output_1.png', 'RGBviewsparams.txt', 'outRGB', 
                            str(wOut), str(hOut), str(displayDensity)],
                           stdout=stdout, stderr=stdout)
        displayDensity = 1
        p6 = self.run_proc(['rgbprocess', 'RGBviews',
                            'output_1.png', 'RGBviewsparams.txt', 'dstyRGB', 
                           str(wOut), str(hOut), str(displayDensity)],
                           stdout=stdout, stderr=stdout)
        self.wait_proc([p5, p6], timeout)

        p7 = self.run_proc(['rgbprocess', 'combineviews',
                            'RGBviewsparams.txt',
                            'inRGB', 'outRGB', 'dstyRGB', 'view'], 
                           stdout=stdout, stderr=stdout)
        p8 = self.run_proc(['rgbprocess', 'mergeimages',
                            'output_1.png', 'input_00.png', 'output_2.png'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc([p7, p8], timeout)


    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        """
        params_file = index_dict(self.key_dir)

        return self.tmpl_out("result.html",
                             input=[self.key_url + 'input_00.png'],
                             output=[self.key_url + 'output_2.png'],
                             views=[self.key_url + 'view_%i.png' % i 
                                    for i in range(100, 127)],
                             run_time=float(params_file['params']['run_time']),
                             sizeY="%i" % image(self.key_dir 
                                                + 'input_00.png').size[1])
