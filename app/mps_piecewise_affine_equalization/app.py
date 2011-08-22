"""
piecewise affine equalization ipol demo web app
"""

from lib import base_app, build, http, image
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time

class app(base_app):
    """ piecewise affine equalization app """

    title = "Piecewise Affine Equalization"

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
            + "mps_piecewise_affine_equalization/piecewise_eq.tar.gz"
        tgz_file = self.dl_dir + "piecewise_eq.tar.gz"
        progs = ["piecewise_equalization"]
        src_bin = dict([(self.src_dir + 
                         os.path.join("piecewise_eq", prog),
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
                      % (self.src_dir + "piecewise_eq", 
                      " ".join(progs)),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for (src, dst) in src_bin.items():
		#print "copy %s to %s" % (src, dst) 
                shutil.copy(src, dst)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)

        return


    #
    # PARAMETER HANDLING
    #
    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, s1="0.5", s2="3.0"):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

        return self.tmpl_out("params.html", msg=msg, s1=s1, s2=s2)

    @cherrypy.expose
    @init_app
    def wait(self, s1="0.5", s2="3.0"):
        """
        params handling and run redirection
        """
        # save the parameters
        try:
            self.cfg['param'] = {'s1' : float(s1), 
				 's2' : float(s2)}
            self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        # read the parameters
        s1 = self.cfg['param']['s1']
        s2 = self.cfg['param']['s2']
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(s1, s2, stdout=stdout, timeout=self.timeout)
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
            ar.add_file("input_0.orig.png", info="uploaded image")
            ar.add_file("input_0.png", info="original image")
            ar.add_file("output_1.png", info="result image 1 (RGB)")
            ar.add_file("output_2.png", info="result image 2 (I)")
            ar.add_info({"smin": s1})
            ar.add_info({"smax": s2})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, s1, s2, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

	N=1
        p1 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N), 'input_0.png',
                            'output_1_N1.png', 'output_2_N1.png', 'pointsN1.txt'],
                           stdout=None, stderr=None)

	N=2
        p2 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N), 'input_0.png',
                            'output_1_N2.png', 'output_2_N2.png', 'pointsN2.txt'],
                           stdout=None, stderr=None)

	N=3
        p3 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N), 'input_0.png',
                            'output_1_N3.png', 'output_2_N3.png', 'pointsN3.txt'],
                           stdout=None, stderr=None)

	N=4
        p4 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N), 'input_0.png',
                            'output_1_N4.png', 'output_2_N4.png', 'pointsN4.txt'],
                           stdout=None, stderr=None)

	N=9
        p5 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N), 'input_0.png',
                            'output_1_N9.png', 'output_2_N9.png', 'pointsN9.txt'],
                           stdout=None, stderr=None)


        self.wait_proc([p1, p2, p3, p4, p5], timeout)


        #Compute histograms of images
        im0 = image(self.work_dir + 'input_0.png')
        im1N1 = image(self.work_dir + 'output_1_N1.png')
        im1N2 = image(self.work_dir + 'output_1_N2.png')
        im1N3 = image(self.work_dir + 'output_1_N3.png')
        im1N4 = image(self.work_dir + 'output_1_N4.png')
        im1N9 = image(self.work_dir + 'output_1_N9.png')
        im2N1 = image(self.work_dir + 'output_2_N1.png')
        im2N2 = image(self.work_dir + 'output_2_N2.png')
        im2N3 = image(self.work_dir + 'output_2_N3.png')
        im2N4 = image(self.work_dir + 'output_2_N4.png')
        im2N9 = image(self.work_dir + 'output_2_N9.png')
        #compute maximum of histogram values
        #maxH0=im0.max_histogram(option="all")
        #maxH1N1=im1N1.max_histogram(option="all")
        #maxH1N2=im1N2.max_histogram(option="all")
        #maxH1N3=im1N3.max_histogram(option="all")
        #maxH1N4=im1N4.max_histogram(option="all")
        #maxH1N9=im1N9.max_histogram(option="all")
        #maxH2N1=im2N1.max_histogram(option="all")
        #maxH2N2=im2N2.max_histogram(option="all")
        #maxH2N3=im2N3.max_histogram(option="all")
        #maxH2N4=im2N4.max_histogram(option="all")
        #maxH2N9=im2N9.max_histogram(option="all")
        #maxH=max([maxH0, maxH1N1, maxH1N2, maxH1N3, 
        #          maxH1N4, maxH1N9, maxH2N1, maxH2N2, 
        #          maxH2N3, maxH2N4, maxH2N9])
        maxH=im0.max_histogram(option="all")
        #draw all the histograms using the same reference maximum
        im0.histogram(option="all", maxRef=maxH)
        im0.save(self.work_dir + 'input_0_hist.png')
        im1N1.histogram(option="all", maxRef=maxH)
        im1N1.save(self.work_dir + 'output_1_N1_hist.png')
        im1N2.histogram(option="all", maxRef=maxH)
        im1N2.save(self.work_dir + 'output_1_N2_hist.png')
        im1N3.histogram(option="all", maxRef=maxH)
        im1N3.save(self.work_dir + 'output_1_N3_hist.png')
        im1N4.histogram(option="all", maxRef=maxH)
        im1N4.save(self.work_dir + 'output_1_N4_hist.png')
        im1N9.histogram(option="all", maxRef=maxH)
        im1N9.save(self.work_dir + 'output_1_N9_hist.png')
        im2N1.histogram(option="all", maxRef=maxH)
        im2N1.save(self.work_dir + 'output_2_N1_hist.png')
        im2N2.histogram(option="all", maxRef=maxH)
        im2N2.save(self.work_dir + 'output_2_N2_hist.png')
        im2N3.histogram(option="all", maxRef=maxH)
        im2N3.save(self.work_dir + 'output_2_N3_hist.png')
        im2N4.histogram(option="all", maxRef=maxH)
        im2N4.save(self.work_dir + 'output_2_N4_hist.png')
        im2N9.histogram(option="all", maxRef=maxH)
        im2N9.save(self.work_dir + 'output_2_N9_hist.png')

        #compute value transforms

	
    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        # read the parameters
        s1 = self.cfg['param']['s1']
        s2 = self.cfg['param']['s2']
        sizeY = image(self.work_dir + 'input_0.png').size[1]
        sizeYhist = image(self.work_dir + 'input_0_hist.png').size[1]
        # add 20 pixels to the histogram size to take margin into account
        sizeYmax = max(sizeY, sizeYhist+60)

        return self.tmpl_out("result.html", s1=s1, s2=s2,
                             sizeY="%i" % sizeYmax)



