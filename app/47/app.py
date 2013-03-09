"""
online image processing
"""

from lib import base_app, build, http, image, config, thumbnail
from lib.misc import ctime, prod
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import subprocess
import glob

class app(base_app):
    """ template demo app """

    title = "Study of the Principal Component Analysis Method for the Correction of Images Degraded by Turbulence"
    is_test = False           # switch to False for deployment
    is_listed = True
    is_built = True

    xlink_article = "http://www.ipol.im/pub/pre/47/"
    xlink_src = "http://www.ipol.im/pub/pre/47/filter_pca-0.9.2.zip"
    xlink_input = "http://dev.ipol.im/~coco/static/dt_pca_input.tar.gz"

    parconfig = {}
    parconfig['winsize'] = {'type': int, 'default': 10,
                          'changeable': True, 'archived' : True,
                          'order' : 1,
                          'htmlname': 'window size',
                          'doc': 'number of frames of sliding window'}
    parconfig['firstvec'] = {'type': int, 'default': 1,
                          'changeable': True, 'archived' : True,
              'htmlname': 'first vector', 'doc':'',
                          'order' : 2}
    parconfig['lastvec'] = {'type': int, 'default': 3,
                          'changeable': True, 'archived' : True,
             'htmlname': 'last vector', 'doc':'',
                          'order' : 3}

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        print("I'm initing!")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() is generic
        #app_expose(base_app.index)
        #app_expose(base_app.input_select)
        #app_expose(base_app.input_upload)
        # params() is modified from the template
        #app_expose(base_app.params)
        # run() and result() must be defined here


    def build_algo(self):
        """
        program build/update
        """
        ### store common file path in variables
        zip_file = self.dl_dir + "filter_pca-0.9.2.zip"
        prog_file = self.bin_dir + "filter_pca.exe"
        log_file = self.base_dir + "build.log"
        ## get the latest source archive
        build.download(app.xlink_src, zip_file)
        ## test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(zip_file) < ctime(prog_file)):
            cherrypy.log("no rebuild needed",
                      context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(zip_file, self.src_dir)
            # build the program
            build.run("make -C %s" % (self.src_dir +"filter_pca-0.9.2"),
                                                   stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                    shutil.rmtree(self.bin_dir)
            try:
                shutil.copy(self.src_dir +
                           os.path.join("filter_pca-0.9.2",
                           "filter_pca.exe"), prog_file)
            except IOError, e:
                print("Unable to copy file. %s" % e)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


    def grab_input(self):
        """
        download the input images from "xlink_input"
        """
        tgz_file = self.dl_dir + "input.tar.gz"
        input_cfg = self.input_dir + "input.cfg"
        ### get the latest source archive
        build.download(app.xlink_input, tgz_file)
        ### test if the dest file is missing, or too old
        if (os.path.isfile(input_cfg)
            and ctime(tgz_file) < ctime(input_cfg)):
            cherrypy.log("no rebuild needed",
                                  context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            shutil.rmtree(self.input_dir)
            shutil.move(self.src_dir + "input", self.input_dir)
        return

    def build(self):
        self.build_algo()
        self.grab_input()
        return


    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        print("ENTER wait")
        print("kwargs = " + str(kwargs))
        try:
            for k in app.parconfig:
                typ = app.parconfig[k]['type']
                self.cfg['param'][k] = typ(kwargs[k])
        except ValueError:
            return self.error(errcode='badparams',
                          errmsg='The parameters must be numeric.')
        #self.cfg.save()
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
        print("ENTER run")
        print("kwargs = " + str(kwargs))
        ## run the algorithm
        try:
            self.run_algo()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')
        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        ## archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("b_000.png", "b_000.png", info="")
            if (self.cfg['meta']['hastruth']):
                ar.add_file("a.png", info="")
            alist = {}
            for k in app.parconfig:
                if app.parconfig[k]['archived']:
                    alist[k] = self.cfg['param'][k]
            #ar.add_file(".png", info="output")
            ar.add_info(alist)
            ar.save()
        return self.tmpl_out("run.html")


    def run_algo(self):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        winsize = self.cfg['param']['winsize']
        firstvec = self.cfg['param']['firstvec']
        lastvec = self.cfg['param']['lastvec']
        print('ENTERING run_algo')
        for k in app.parconfig:
            print(k + ' = ' + str(self.cfg['param'][k]))
        p = self.run_proc(['ipol_demo.sh',
             str(winsize),
             str(firstvec),
             str(lastvec)
            ])
        self.wait_proc(p, timeout=self.timeout)
        return


    @cherrypy.expose
    @init_app
    def reposition(self, **kwargs):
        print("REPOSITION KWARGS = " + str(kwargs))
        self.cfg['meta']['pos_inview'] = True
        return self.tmpl_out("result.html")

    def tralara(self, f):
        """
        the string returned by this function will be used
        as the tooltip text of image "f"
        """
        msg = f + self.work_dir
        msg = "-"
        return msg

    @cherrypy.expose
    def input_select(self, **kwargs):
        """
        use the selected available input images
        """
        print("ENTERING input_select")
        self.new_key()
        self.init_cfg()
        print("key = " + self.key)
        # kwargs contains input_id.x and input_id.y
        input_id = kwargs.keys()[0].split('.')[0]
        assert input_id == kwargs.keys()[1].split('.')[0]
        # get the images
        input_dict = config.file_dict(self.input_dir)
        idir = self.input_dir + input_dict[input_id]['subdir'] + '/'
        print("idir = " + idir)
        fnames = [os.path.basename(f) for f in glob.glob(idir + 'b_???.png')]
        for f in fnames:
            shutil.copy(idir + f, self.work_dir + f)
        hastruth = os.path.isfile(idir + "a.png")
        self.cfg['meta']['hastruth'] = hastruth
        self.cfg['meta']['nframes'] = len(fnames)
        if (hastruth):
            shutil.copy(idir + "a.png", self.work_dir + "a.png")

        #fnames = input_dict[input_id]['files'].split()
        #for i in range(len(fnames)):
        #    shutil.copy(self.input_dir + fnames[i],
        #                self.work_dir + 'input_%i' % i)
        #msg = self.process_input()
        self.log("input selected : %s" % input_id)
        self.cfg['meta']['original'] = False
        self.cfg['meta']['height'] = image(self.work_dir + '/b_000.png').size[1]
        self.cfg.save()
        # jump to the params page
        return self.params(msg="(no message)", key=self.key)

    def upload_given_file(self, i, fi):
        """
        upload a file
        """
        file_up = fi
        if '' == file_up.filename:
            # missing file
            return False
        file_save = file(self.work_dir + i, 'wb')
        size = 0
        while True:
            # T O D O larger data size
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
        return True

    @cherrypy.expose
    def input_upload(self, **kwargs):
        """
        use the uploaded input images
        """
        self.new_key()
        self.init_cfg()

        ra = self.upload_given_file('a', kwargs['file_a'])
        rb = self.upload_given_file('b', kwargs['file_b'])
        rt = self.upload_given_file('t.tiff', kwargs['file_t'])

        if not ra:
            return self.error(errcode='badparams',
                         errmsg='(MISSING FIRST IMAGE)')
        if not rb:
            return self.error(errcode='badparams',
                         errmsg='(MISSING SECOND IMAGE)')

        try:
            ima = image(self.work_dir + 'a')
            imb = image(self.work_dir + 'b')
        except IOError:
            return self.error(errcode='badparams',
                     errmsg='(INPUT IMAGE FORMAT ERROR)')

        msg = "no message"


        if self.input_max_pixels and prod(ima.size) > (self.input_max_pixels):
            ima.resize(self.input_max_pixels)
            imb.resize(self.input_max_pixels)
            msg = """The image has been resized
                  for a reduced computation time."""

        if ima.size[0] != imb.size[0] or ima.size[1] != imb.size[1]:
            ss = "%dx%d - %dx%d" % (ima.size[0], ima.size[1],
                           imb.size[0], imb.size[1])
            return self.error(errcode='badparams',
             errmsg='(INPUT IMAGES MUST HAVE THE SAME SIZE %s)'%ss)

        if len(ima.im.getbands()) != len(imb.im.getbands()):
            return self.error(errcode='badparams',
             errmsg='(DO NOT MIX COLOR AND GRAY)')
        if rt:
            sizetruth = subprocess.Popen([self.bin_dir + 'imprintf',
                  '%w %h %c' , self.work_dir + 't.tiff'],
                  stdout=subprocess.PIPE).communicate()[0]
            ts = [int(f) for f in sizetruth.split()]
            if len(ts) != 3 or ts[2] != 2:
                return self.error(errcode='badparam',
                         errmsg='(CAN NOT READ GROUND TRUTH FILE)')
            if ts[0] != ima.size[0] or ts[1] != ima.size[1]:
                return self.error(errcode='badparams',
                  errmsg='(GROUND TRUTH IMAGE HAS DIFFERENT SIZE)')

        ima.save(self.work_dir + 'a.png')
        imb.save(self.work_dir + 'b.png')

        self.log("input uploaded")
        self.cfg['meta']['original'] = True
        self.cfg['meta']['height'] = image(self.work_dir + '/a.png').size[1]
        self.cfg['meta']['hastruth'] = rt

        self.cfg.save()
        # jump to the params page
        return self.params(msg=msg, key=self.key)

    @cherrypy.expose
    def index(self):
        """
        demo presentation and input menu
        """
        print("ENTERING index")
        tn_size = 192
        # read the input index as a dict
        inputd = config.file_dict(self.input_dir)
        print(inputd)
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
    def result(self, **kwargs):
        """
        display the algo results
        """
        self.cfg['meta']['height'] = image(self.work_dir + '/b_000.png').size[1]
        return self.tmpl_out("result.html")

    def algo_getruntime(self):
        """
        return a string containing the running time of the algorithm
        """
        #return subprocess.check_output([self.bin_dir+'cat',\
        #   self.work_dir+'stuff_'+a+'.time'])
        return subprocess.Popen(['/bin/cat',
                   self.work_dir+'run.time'],
                  stdout=subprocess.PIPE).communicate()[0]

# vim: set ts=8 noexpandtab list:
