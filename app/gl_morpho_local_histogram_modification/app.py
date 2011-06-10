"""
shape preserving local histogram equalization ipol demo web app
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
from math import ceil

class app(base_app):
    """ shape preserving local histogram equalization ipol demo """

    title = "Shape preserving local histogram equalization"

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
            + "gl_morpho_local_histogram_modification/mlocalhistogram.tar.gz"
        tgz_file = self.dl_dir + "mlocalhistogram.tar.gz"
        progs = ["mlocalhistogram"]
        src_bin = dict([(self.src_dir + os.path.join("mlocalhistogram", prog),
                         self.bin_dir + prog)
                        for prog in progs])
        log_file = self.base_dir + "build.log"

        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if any dest file is missing, or too old
        if all([(os.path.isfile(bin_file)
                 and ctime(tgz_file) < ctime(bin_file))
                for bin_file in src_bin.values()]):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the programs
            build.run("make -j4 -C %s %s"
                      % (self.src_dir + "mlocalhistogram", " ".join(progs)),
                      stdout=log_file)
            # save into bin dir
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


    def select_subimage(self, x0, y0, x1, y1):
        """
        cut subimage from original image
        """
        # draw selected rectangle on the image
        imgS = image(self.work_dir + 'input_0.png')
        imgS.draw_line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], 
                       color="red")
        imgS.draw_line([(x0+1, y0+1), (x1-1, y0+1), (x1-1, y1-1), (x0+1, y1-1), 
                       (x0+1, y0+1)], color="white")
        imgS.save(self.work_dir + 'input_0s.png')
        # crop the image
        # try cropping from the original input image (if different from input_0)
        im0 = image(self.work_dir + 'input_0.orig.png')
        dx0 = im0.size[0]
        img = image(self.work_dir + 'input_0.png')
        dx = img.size[0]
        if (dx != dx0) :
            z = float(dx0)/float(dx)
            im0.crop((int(x0*z), int(y0*z), int(x1*z), int(y1*z)))
            # resize if cropped image is too big
            if self.input_max_pixels and prod(im0.size) > self.input_max_pixels:
                im0.resize(self.input_max_pixels, method="antialias")
            img = im0
        else :
            img.crop((x0, y0, x1, y1))
	# save result
        img.save(self.work_dir + 'input_0.sel.png')
        return


    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, x0=None, y0=None, 
               x1=None, y1=None, level="0"):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

        if x0:
            self.select_subimage(int(x0), int(y0), int(x1), int(y1))

        return self.tmpl_out("params.html", msg=msg, x0=x0, y0=y0, 
                             x1=x1, y1=y1, level=level)

    @cherrypy.expose
    @init_app
    def rectangle(self, action=None, level=None, 
                  x=None, y=None, x0=None, y0=None):
        """
        select a rectangle in the image
        """
        if action == 'run':
            if x == None:
	        #save parameter
                try:
                    self.cfg['param'] = {'level' : level}
                    self.cfg.save()
                except ValueError:
                    return self.error(errcode='badparams',
                                      errmsg="Incorrect level parameter.")
            else:
	        #save parameters
                try:
                    self.cfg['param'] = {'level' : level, 
				         'x0' : int(x0),
				         'y0' : int(y0),
				         'x1' : int(x),
				         'y1' : int(y)}
                    self.cfg.save()
                except ValueError:
                    return self.error(errcode='badparams',
                                      errmsg="Incorrect parameters.")
	
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
                return self.tmpl_out("params.html", level=level, x0=x, y0=y)
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
                    self.cfg['param'] = {'level' : level, 
                                         'x0' : x0,
                                         'y0' : y0,
                                         'x1' : x1,
                                         'y1' : y1}
                    self.cfg.save()
                except ValueError:
                    return self.error(errcode='badparams',
                                      errmsg="Incorrect parameters.")
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
        level = self.cfg['param']['level']
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(level, stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        stdout.close()

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="uploaded image")
            # save processed image (if different from uploaded)
            im0 = image(self.work_dir + 'input_0.orig.png')
            dx0 = im0.size[0]
            img = image(self.work_dir + 'input_0.png')
            dx = img.size[0]
            imgsel = image(self.work_dir + 'input_0.sel.png')
            dxsel = imgsel.size[0]
            if (dx != dx0) or (dxsel != dx):
              ar.add_file("input_0.sel.png", info="original input image")
            ar.add_file("output.png", info="processed image")
            ar.add_info({"level": level})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, level, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        amin=40
        rmax=3.0
        use_recursiveCC=0
	#process image
        p = self.run_proc(['mlocalhistogram', 'input_0.sel.png', 'output.png', 
                           str(level), str(amin), str(rmax), str(use_recursiveCC)],
                           stdout=None, stderr=None)
        self.wait_proc(p, timeout)

        #Compute histograms of images
        im1 = image(self.work_dir + 'input_0.sel.png')
        im2 = image(self.work_dir + 'output.png')
        #compute maximum of histogram values
        maxH1=im1.max_histogram(option="all")
        maxH2=im2.max_histogram(option="all")
        maxH=max([maxH1, maxH2])
        #draw all the histograms using the same reference maximum
        im1.histogram(option="all", maxRef=maxH)
        im1.save(self.work_dir + 'input_hist.png')
        im2.histogram(option="all", maxRef=maxH)
        im2.save(self.work_dir + 'output_hist.png')

	
    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """

        # read the parameters
        level = self.cfg['param']['level']
        try:
            x0 = self.cfg['param']['x0']
        except KeyError:
            x0 = None
        try:
            y0 = self.cfg['param']['y0']
        except KeyError:
            y0 = None
        try:
            x1 = self.cfg['param']['x1']
        except KeyError:
            x1 = None
        try:
            y1 = self.cfg['param']['y1']
        except KeyError:
            y1 = None

        (sizeX, sizeY)=image(self.work_dir + 'input_0.sel.png').size
        # Resize for visualization (new size of the smallest dimension = 200)
        zoom_factor = None
        if (sizeX < 200) or (sizeY < 200):
            if sizeX > sizeY:
                zoom_factor = int(ceil(200.0/sizeY))
            else:
                zoom_factor = int(ceil(200.0/sizeX))

            sizeX = sizeX*zoom_factor
            sizeY = sizeY*zoom_factor

            im = image(self.work_dir + 'input_0.sel.png')
            im.resize((sizeX, sizeY), method="pixeldup")
            im.save(self.work_dir + 'input_0_zoom.sel.png')

            im = image(self.work_dir + 'output.png')
            im.resize((sizeX, sizeY), method="pixeldup")
            im.save(self.work_dir + 'output_zoom.png')

        sizeY2=image(self.work_dir + 'input_hist.png').size[1]
        sizeYmax=max([sizeY, sizeY2])


        return self.tmpl_out("result.html", level=level, 
                             x0=x0, y0=y0, x1=x1, y1=y1,
                             sizeY=sizeYmax, zoom_factor=zoom_factor)



