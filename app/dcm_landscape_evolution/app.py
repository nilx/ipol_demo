"""
landscape_evolution ipol demo web app
"""

from lib import base_app, image, build, http
from lib.misc import ctime
from lib.base_app import init_app
import os.path
import time
import shutil
import cherrypy
from cherrypy import TimeoutError


class app(base_app):
    """ landscape_evolution app """

    title = "Landscape Evolution by Erosion and Sedimentation"

    input_nb = 1
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.tiff' # input image expected extension (ie file format)
    is_test = False

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

       # select the base_app steps to expose
        # index() is generic
        base_app.index.im_func.exposed = True
        # input_xxx() are modified from the template
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
            + "dcm_landscape_evolution/landscape_evolution.tar.gz"
        tgz_file = self.dl_dir + "landscape_evolution.tar.gz"
        prog_file = self.bin_dir + "landscape_evolution"
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
            build.run("make -j4 -C %s landscape_evolution"
                      % (self.src_dir + "landscape_evolution"),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir
                        + os.path.join("landscape_evolution", "landscape_evolution"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #
    # PARAMETER HANDLING
    #


    #
    # EXECUTION AND RESULTS
    #

    @cherrypy.expose
    @init_app
    def wait(self, time_step, rain, expm, erosione, erosioncreep, erosions, iteration,iterationw,waterlandcst,maxvarwater,percentageland):
        """
        params handling and run redirection
        """
        # read parameters
        try:
            self.cfg['param'] = {'time_step' : float(time_step),
                                 'rain' : float(rain),
                                 'expm' : float(expm),
                                 'erosione' : float(erosione),
                                 'erosioncreep' : float(erosioncreep),
                                 'erosions' : float(erosions),
                                 'iteration' : float(iteration),
                                 'iterationw' : float(iterationw),
                                 'waterlandcst' : float(waterlandcst),
                                 'maxvarwater' : float(maxvarwater),
                                 'percentageland' : float(percentageland)
                                 }
            self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="Wrong input parameters")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # read the parameters
        time_step = self.cfg['param']['time_step']
        expm = self.cfg['param']['expm']
        erosione = self.cfg['param']['erosione']
        erosioncreep = self.cfg['param']['erosioncreep']
        erosions = self.cfg['param']['erosions']
        iteration = self.cfg['param']['iteration']
        iterationw = self.cfg['param']['iterationw']
        waterlandcst = self.cfg['param']['waterlandcst']
        maxvarwater = self.cfg['param']['maxvarwater']
        percentageland = self.cfg['param']['percentageland']
        rain = self.cfg['param']['rain']

        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(time_step, rain, expm, erosione, erosioncreep, erosions, iteration, iterationw, waterlandcst, maxvarwater, percentageland, stdout=stdout, timeout=self.timeout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input.tiff", info="input")
            ar.add_file("result_l.tif", info="result_l")
            ar.add_file("result_w.tif", info="result_w")
            ar.add_file("result_orig.tif", info="result_orig")
            ar.add_file("result_w_only.tif", info="result_w_only")
            ar.add_file("result_c.tif", info="result_c")
            ar.add_info({'time_step' : self.cfg['param']['time_step'],
			 'expm' : self.cfg['param']['expm'],
        		 'erosione' : self.cfg['param']['erosione'],
        		 'erosioncreep' : self.cfg['param']['erosioncreep'],
        		 'erosions' : self.cfg['param']['erosions'],
        		 'iteration' : self.cfg['param']['iteration'],
        		 'iterationw' : self.cfg['param']['iterationw'],
        		 'waterlandcst' : self.cfg['param']['waterlandcst'],
        		 'maxvarwater' : self.cfg['param']['maxvarwater'],
        		 'percentageland' : self.cfg['param']['percentageland'],
        		 'rain' : self.cfg['param']['rain']})
            ar.save()


        return self.tmpl_out("run.html")

    def run_algo(self, time_step, rain, expm, erosione, erosioncreep, erosions, iteration, iterationw, waterlandcst, maxvarwater, percentageland, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        stdout = stdout
        # process image

        img = image(self.work_dir + 'input_0.png')
        img.save(self.work_dir + 'input' + self.input_ext)

        p1 = self.run_proc(['landscape_evolution',
                            self.work_dir + 'input' + self.input_ext,
                            self.work_dir + 'result',
                            str(time_step),
                            str(rain),
                            str(expm),
                            str(erosione),
                            str(erosioncreep),
                            str(erosions),
                            str(iteration),
                            str(iterationw),
                            str(waterlandcst),
                            str(maxvarwater),
                            str(percentageland)
                            ])
        self.wait_proc([p1], timeout)
        im = image(self.work_dir + 'result_l.tif')
        im.save(self.work_dir + 'result_l.png')
        im = image(self.work_dir + 'result_w.tif')
        im.save(self.work_dir + 'result_w.png')
        im = image(self.work_dir + 'result_orig.tif')
        im.save(self.work_dir + 'result_orig.png')
        im = image(self.work_dir + 'result_w_only.tif')
        im.save(self.work_dir + 'result_w_only.png')
        im = image(self.work_dir + 'result_c.tif')
        im.save(self.work_dir + 'result_c.png')
        im = image(self.work_dir + 'result_diff_landscape.tif')
        im.save(self.work_dir + 'result_diff_landscape.png')




    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # read the parameters
        time_step = self.cfg['param']['time_step']
        rain  = self.cfg['param']['rain']
        expm  = self.cfg['param']['expm']
        erosione  = self.cfg['param']['erosione']
        erosioncreep  = self.cfg['param']['erosioncreep']
        erosions  = self.cfg['param']['erosions']
        iteration  = self.cfg['param']['iteration']
        iterationw  = self.cfg['param']['iterationw']
        waterlandcst  = self.cfg['param']['waterlandcst']
        maxvarwater  = self.cfg['param']['maxvarwater']
        percentageland  = self.cfg['param']['percentageland']

        return self.tmpl_out("result.html",
                             time_step=time_step,
                             rain=rain,
                             expm=expm,
                             erosione=erosione,
                             erosioncreep=erosioncreep,
                             erosions=erosions,
                             iteration=iteration,
                             iterationw=iterationw,
                             waterlandcst=waterlandcst,
                             maxvarwater=maxvarwater,
                             percentageland=percentageland,
			     sizeY="%i" % image(self.work_dir
                                                + 'input_0.png').size[1])
