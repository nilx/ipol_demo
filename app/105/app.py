"""
demo example for the X->aX+b transform
"""

from lib import base_app, build, http, image, config, thumbnail
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import subprocess
import glob
import time
from math import floor

class app(base_app):
    """ template demo app """

    title = "Implementation of the Centroid Method \
            for the Correction of Turbulence"
    is_test = False # switch to False for deployment
    is_listed = True

    input_max_weight = 400*400*3*10000

    xlink_article = 'http://www.ipol.im/pub/pre/105/'
    xlink_src   = "http://www.ipol.im/pub/pre/105/centroid-2.tar.gz"
    xlink_input = "http://www.ipol.im/pub/pre/105/turbuseqs.tar.gz"


    parconfig = {}
    parconfig['nframes'] = {'type': int,
            'default': 30, 'changeable': True,
            'htmlname': 'N<sub>frames</sub>',
            'doc': 'number of input frames'
                           }
    parconfig['nseeds'] = {'type': int,
            'default': 1, 'changeable': True,
            'htmlname': 'N<sub>seeds</sub>',
            'doc': 'number of centroid seeds'
                           }


    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)
        app_expose(base_app.params)

    def build_algo(self):
        """
        program build/update
        """
        ## store common file path in variables
        tgz_file = self.dl_dir + "centroid-2.tar.gz"
        prog_file = self.bin_dir + "centroid"
        log_file = self.base_dir + "build.log"

        ## get the latest source archive
        build.download(app.xlink_src, tgz_file)
        ## test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("no rebuild needed",
                          context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            srcdir  = self.src_dir + "centroid-2/"
            build.run("make", stdout=log_file, cwd=srcdir)

            cherrypy.log("before copy",
                      context='BUILD', traceback=False)

            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(srcdir + "centroid", self.bin_dir + "centroid")
            shutil.copy(srcdir + "imcombine", self.bin_dir + "imcombine")
            shutil.copy(srcdir + "demo.sh", self.bin_dir + "demo.sh")
            cherrypy.log("copy ok",
                          context='BUILD', traceback=False)

        return

    def grab_input(self):
        """
        download the input images from "xlink_input"
        """
        tgz_file = self.dl_dir + "input.tar.gz"
        input_cfg = self.input_dir + "index.cfg"
        ## get the latest source archive
        build.download(app.xlink_input, tgz_file)
        ## test if the dest file is missing, or too old
        if (os.path.isfile(input_cfg)
            and ctime(tgz_file) < ctime(input_cfg)):
            cherrypy.log("no rebuild needed",
                      context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            shutil.rmtree(self.input_dir)
            shutil.move(self.src_dir + "input", self.input_dir)

            # cleanup the source dir
            #shutil.rmtree(self.src_dir)
        return

    def build(self):
        self.build_algo()
        #self.build_demo()
        self.grab_input()
        return


    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        #print("WAIT key=%s" % self.key)
        #print("kwargs = " + str(kwargs))
        try:
            for k in app.parconfig:
                typ = app.parconfig[k]['type']
                self.cfg['param'][k] = typ(kwargs[k])
        except ValueError:
            return self.error(errcode='badparams',
                          errmsg='The parameters must be numeric.')
        #self.cfg.save()
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        self.cfg['meta']['height'] = image(self.work_dir + '/i0000.png').size[1]
        self.cfg['meta']['pos_inview'] = False
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self, **kwargs):
        """
        algo execution
        """
        #print("ENTER run")
        #print("kwargs = " + str(kwargs))
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
            ar.add_file("i0000.png", "i0000.png", info="first frame")
            ar.add_file("o_iavg.png", "o_iavg.png", info="input average")
            ar.add_file("o_cmed.png", "o_cmed.png", info="output result")
            ar.add_file("vidfile", "vidfile", info="uploaded video")
            nframes = self.cfg['param']['nframes']
            nseeds = self.cfg['param']['nseeds']
            ar.add_info({"nframes": nframes, "nseeds": nseeds})
            ar.save()

        return self.tmpl_out("run.html")


    def run_algo(self):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        inpat = 'i%04d.png'
        first = '0'
        last = self.cfg['param']['nframes']
        if (last > int(self.cfg['meta']['maxframes'])):
            last = int(self.cfg['meta']['maxframes'])
        if (last < 2):
            last = 2
        self.cfg['param']['nframes'] = last
        last = str(last-1)
        nseeds = str(self.cfg['param']['nseeds'])
        outprefix = 'o_'
        start_time = time.time()
        p = self.run_proc(['demo.sh', inpat, first, last, nseeds, outprefix])
        self.wait_proc(p, timeout=self.timeout)
        end_time = time.time()
        run_time = floor(10*(end_time - start_time))/10
        fi = open(self.work_dir + "run.time", "w")
        fi.write(str(run_time))
        fi.close()
        return


    @cherrypy.expose
    @init_app
    def reposition(self, **kwargs):
        """
        scroll the html upto the #view name
        """
        #print("REPOSITION KWARGS = " + str(kwargs))
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
        #print("ENTERING input_select")
        self.new_key()
        self.init_cfg()
        #print("key = " + self.key)
        # kwargs contains input_id.x and input_id.y
        input_id = kwargs.keys()[0].split('.')[0]
        assert input_id == kwargs.keys()[1].split('.')[0]
        # get the images
        input_dict = config.file_dict(self.input_dir)
        idir = self.input_dir + input_dict[input_id]['subdir'] + '/'
        #print("idir = " + idir)
        fnames = [os.path.basename(f) for f in glob.glob(idir + 'i????.png')]
        for f in fnames:
            shutil.copy(idir + f, self.work_dir + f)
        hastruth = os.path.isfile(idir + "a.png")
        self.cfg['meta']['hastruth'] = hastruth
        self.cfg['meta']['maxframes'] = len(fnames)
        if (hastruth):
            shutil.copy(idir + "a.png", self.work_dir + "a.png")

        self.log("input selected : %s" % input_id)
        self.cfg['meta']['original'] = False
        self.cfg['meta']['height'] = image(self.work_dir + '/i0000.png').size[1]
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
                        "File too large, (" + str(size) + "/" +
                                         str(self.input_max_weight) +
                        "), resize or use better compression")
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

        rv = self.upload_given_file('vidfile', kwargs['video'])

        if not rv:
            return self.error(errcode='badparams',
                         errmsg='(MISSING IMAGE SEQUENCE)')

        vidfile = self.work_dir + 'vidfile'
        frampat = self.work_dir + 'k%04d.png'

        strffmpeg = subprocess.Popen(['/usr/bin/ffmpeg',
                        '-i', vidfile,
                        '-vframes', '200',
                        '-vf', 'scale=384:384/dar',
                        '-f', 'image2', frampat
                                     ],
                  stdout=subprocess.PIPE).communicate()[0]
        self.log("ffmpeg returned = \"%s\"" % strffmpeg)

        # re-number the files
        sysfo = "bash -c 'C=0;for i in $(ls %sk*.png|sort -R);do mv $i \
                %s$(printf i%s04d.png $C); C=$[C+1]; done'\
                " % (self.work_dir, self.work_dir, "%")
        os.system(sysfo)

        self.log("input uploaded")
        self.cfg['meta']['original'] = True
        self.cfg['meta']['height'] = image(self.work_dir + '/i0000.png').size[1]
        self.cfg['meta']['hastruth'] = False
        self.cfg['meta']['maxframes'] = len(glob.glob(self.work_dir+
                                                      'i????.png'))

        self.cfg.save()
        # jump to the params page
        return self.params(msg="no message", key=self.key)

    @cherrypy.expose
    def index(self):
        """
        demo presentation and input menu
        """
        #print("ENTERING index")
        tn_size = 192
        # read the input index as a dict
        inputd = config.file_dict(self.input_dir)
        #print(inputd)
        for (input_id, input_info) in inputd.items():
            tn_fname = [thumbnail(self.input_dir + \
                                     input_info['subdir'] \
                                     + '/i0000.png',(tn_size,tn_size))]
            inputd[input_id]['hastruth'] = os.path.isfile(
                   self.input_dir + input_info['subdir']+'/a.png')
            inputd[input_id]['height'] = image(self.input_dir
                         + input_info['subdir'] + '/i0000.png').size[1]
            inputd[input_id]['baseinput'] = \
                        self.input_url + input_info['subdir'] + '/'
            inputd[input_id]['url'] = [self.input_url
                                        + input_info['subdir']
                                        + '/' + os.path.basename(f)
                                      for f in ["i0000.png"]]
            inputd[input_id]['tn_url'] = [self.input_url
                                             + input_info['subdir']
                                             + '/'
                                             + os.path.basename(f)
                for f in tn_fname]

        return self.tmpl_out("input.html", inputd=inputd)

    def clone_input(self):
        """
        clone the input for a re-run of the algo
        """
        self.log("cloning input from %s" % self.key)
        #print "CLONE HERE"
        # get a new key
        old_work_dir = self.work_dir
        old_cfg_meta = self.cfg['meta']
        self.new_key()
        self.init_cfg()
        # copy the input files
        fnames = [os.path.basename(f) for f in
                  glob.glob(old_work_dir+'i????.png')]
        for fname in fnames:
            shutil.copy(old_work_dir + fname, self.work_dir + fname)
        # copy cfg
        self.cfg['meta'].update(old_cfg_meta)
        self.cfg.save()
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        self.cfg['meta']['height'] = image(self.work_dir + '/i0000.png').size[1]
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

# vim: set ts=4 sw=4 expandtab list:
