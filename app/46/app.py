"""
MaoGilles demo
"""

from lib import base_app, build, http, image, config, thumbnail
from lib.misc import ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import glob
import time

class app(base_app):
    """ template demo app """

    title = "Mao-Gilles Stabilization Algorithm"
    is_test = False
    xlink_article = 'http://www.ipol.im/pub/pre/46/'

        # Definition of the parameters and their default values
    parconfig = {}
    parconfig['winsize'] = {'type': int, 'default': 10,
                          'changeable': True, 'archived' : False,
                          'order' : 1,
                          'htmlname': 'winsize',
                          'doc': 'number of frames of sliding window (<149)'}
    parconfig['nbregman'] = {'type': int, 'default': 4,
                          'changeable': True, 'archived' : False,
                          'order' : 2,
                          'htmlname': 'Nbregman',
                          'doc': 'number of iterations of the Bregman loop \
(<10)'}
    parconfig['nsplitting'] = {'type': int, 'default': 5,
                          'changeable': True, 'archived' : False,
                          'order' : 3,
                          'htmlname': 'Nsplitting',
                          'doc': 'number of iterations of the operator \
splitting loop (<10)'}
    parconfig['lambd'] = {'type': float, 'default': 0.1,
                          'changeable': True, 'archived' : False,
              'htmlname': 'lambda', 'doc':'regularization parameter (<1)',
                          'order' : 4}
    parconfig['delta'] = {'type': float, 'default': 0.5,
                          'changeable': True, 'archived' : False,
             'htmlname': 'delta', 'doc':'step for the gradient descent\
(0.05 < delta < 1)',
                          'order' : 5}

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)



    def build(self):
        """
        program build/update
        """
        ### store common file path in variables
        zip_file = self.dl_dir + "MaoGilles_201306c.zip"
        prog_file = self.bin_dir + "ShiftMaoGilles"
        log_file = self.base_dir + "build.log"
        ### get the latest source archive
        build.download("http://www.ipol.im/pub/pre/46/MaoGilles_201306c.zip"
        , zip_file)
        ### test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(zip_file) < ctime(prog_file)):
            cherrypy.log("no rebuild needed",
                      context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(zip_file, self.src_dir)
            # build the program
            build.run("make OPENMP=1 -C %s" % (self.src_dir
            +os.path.join("MaoGilles_201306")), stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            try:
                os.mkdir(self.bin_dir)
                shutil.copy(self.src_dir +
                           "MaoGilles_201306/ShiftMaoGilles", prog_file)
            except IOError, e:
                print("Unable to copy file. %s" % e)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return




    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        try:
            for k in app.parconfig:
                typ = app.parconfig[k]['type']
                self.cfg['param'][k] = typ(kwargs[k])
                self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                          errmsg='The parameters must be numeric.')

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        self.cfg['meta']['height'] = image(self.work_dir + '/b_000.png').size[1]
        self.cfg['meta']['pos_inview'] = False
        return self.tmpl_out("wait.html")




    @cherrypy.expose
    @init_app
    def run(self, **kwargs):
        """
        algo execution
        """

        ## run the algorithm
        try:
            run_time = time.time()
            self.run_algo()
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')
        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        return self.tmpl_out("run.html")


    def run_algo(self):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        w = self.cfg['param']['winsize']
        nb = self.cfg['param']['nbregman']
        ns = self.cfg['param']['nsplitting']
        l = self.cfg['param']['lambd']
        d = self.cfg['param']['delta']
        p = self.run_proc(['ShiftMaoGilles',
                     self.work_dir + 'b_%03d.png',
                     str(0),
                     str(8+w),
             str(l),
             str(d),
             str(w),
             str(nb),
             str(ns),
             str(1)
            ])
        shutil.copy(self.base_dir + '/template/flow_legend.png',
                    self.work_dir + 'flow_legend.png')
        self.wait_proc(p, timeout=self.timeout)
        return

    @cherrypy.expose
    def input_select(self, **kwargs):
        """
        use the selected available input images
        """
        self.new_key()
        self.init_cfg()
        # kwargs contains input_id.x and input_id.y
        input_id = kwargs.keys()[0].split('.')[0]
        assert input_id == kwargs.keys()[1].split('.')[0]
        # get the images
        input_dict = config.file_dict(self.input_dir)
        idir = self.input_dir + input_dict[input_id]['subdir'] + '/'
        fnames = [os.path.basename(f) for f in glob.glob(idir + 'b_???.png')]
        for f in fnames:
            shutil.copy(idir + f, self.work_dir + f)
        hastruth = os.path.isfile(idir + "a.png")
        self.cfg['meta']['hastruth'] = hastruth
        self.cfg['meta']['nframes'] = len(fnames)
        if (hastruth):
            shutil.copy(idir + "a.png", self.work_dir + "a.png")

        self.log("input selected : %s" % input_id)
        self.cfg['meta']['original'] = False
        self.cfg['meta']['height'] = image(self.work_dir + '/b_000.png').size[1]
        self.cfg.save()
        # jump to the params page
        return self.tmpl_out("params.html", key=self.key)



    @cherrypy.expose
    def index(self):
        """
        demo presentation and input menu
        """
        tn_size = 192
        # read the input index as a dict
        inputd = config.file_dict(self.input_dir)
        for (input_id, input_info) in inputd.items():
            tn_fname = [thumbnail(self.input_dir + \
                                     input_info['subdir'] \
                                     + '/b_000.png',(tn_size,tn_size))]
            inputd[input_id]['hastruth'] = os.path.isfile(
                   self.input_dir + input_info['subdir']+'/a.png')
            inputd[input_id]['height'] = image(self.input_dir
                         + input_info['subdir'] + '/b_000.png').size[1]
            inputd[input_id]['baseinput'] = \
                        self.input_url + input_info['subdir'] + '/'
            inputd[input_id]['url'] = [self.input_url
                                        + input_info['subdir']
                                        + '/' + os.path.basename(f)
                                      for f in "b_000.png"]
            inputd[input_id]['tn_url'] = [self.input_url
                                             + input_info['subdir']
                                             + '/'
                                             + os.path.basename(f)
                for f in tn_fname]

        return self.tmpl_out("input.html", inputd=inputd)

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        self.cfg['meta']['height'] = image(self.work_dir + '/b_000.png').size[1]
        return self.tmpl_out("result.html")
