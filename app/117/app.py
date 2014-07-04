"""
IPOL SIFT
"""

from lib import base_app, build, http
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
import os.path
import shutil
import Image

class app(base_app):
    """ demo app """
    title = "Gaussian Semigroup"
    input_nb = 1
    input_max_pixels = None
    input_max_method = 'zoom'
    input_dtype = '1x8i'
    input_ext = '.png'
    is_test = False

    xlink_article = "http://www.ipol.im/pub/pre/117/"
    st = "http://www.ipol.im/pub/pre/117/gaussconv_20140515.zip"
    xlink_src = st

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)
        # select the base_app steps to expose
        app_expose(base_app.index)
        app_expose(base_app.input_select)
        app_expose(base_app.input_upload)
        app_expose(base_app.params)



    def build(self):
        """
        program build/update
        """
        zip_filename = 'gaussconv_20140515.zip'
        src_dir_name = 'gaussconv_20140515/'
        prog_filename1 = 'demo_gaussconv_dct'
        prog_filename2 = 'demo_gaussconv_dft'
        prog_filename3 = 'demo_gaussconv_lindeberg'
        prog_filename4 = 'demo_gaussconv_sampled_kernel'
        # store common file path in variables
        tgz_file = self.dl_dir + zip_filename
        prog_file = self.bin_dir + prog_filename1
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(app.xlink_src, tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s" % (self.src_dir + src_dir_name),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            # copy all the programs to the bin dir
            shutil.copy(self.src_dir + \
                    os.path.join(os.path.join(src_dir_name, 'bin'),
                     prog_filename1),
                    os.path.join(self.bin_dir, prog_filename1))
            shutil.copy(self.src_dir + \
                    os.path.join(os.path.join(src_dir_name, 'bin'),
                     prog_filename2),
                    os.path.join(self.bin_dir, prog_filename2))
            shutil.copy(self.src_dir + \
                    os.path.join(os.path.join(src_dir_name, 'bin'),
                     prog_filename3),
                    os.path.join(self.bin_dir, prog_filename3))
            shutil.copy(self.src_dir + \
                    os.path.join(os.path.join(src_dir_name, 'bin'),
                     prog_filename4),
                    os.path.join(self.bin_dir, prog_filename4))
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return




    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        run redirection
        """
        # Initialize default values
        self.cfg['param']['newrun'] = False
        self.cfg['param']['x'] = '-1'
        self.cfg['param']['x'] = '-1'
        self.cfg['param']['width'] = '1000'
        VALID_KEYS = [
                'newrun',
                'sigma',
                'n',
                'k',
                'gamma']
        #if ('paradic' in self.cfg['param']):
        #    # deserialization !!
        #    self.cfg['param']['paradic'] = \
        #            dict(eval(str(self.cfg['param']['paradic'])))
        #else:
        #    self.load_standard_parameters()

        self.load_standard_parameters()
        # PROCESS ALL THE INPUTS
        for prp in kwargs.keys():
            if prp in VALID_KEYS:
                if prp == 'newrun':
                    self.cfg['param']['newrun'] = kwargs[prp]
                elif prp == 'action':
                    self.cfg['param']['action'] = kwargs[prp]
                elif prp == 'show':
                    self.cfg['param']['show'] = kwargs[prp]
                elif prp == 'x':
                    self.cfg['param']['x'] = kwargs[prp]
                elif prp == 'y':
                    self.cfg['param']['y'] = kwargs[prp]
                elif prp == 'sigma':
                    self.cfg['param']['sigma'] = kwargs[prp]
                elif prp == 'n':
                    self.cfg['param']['n'] = kwargs[prp]
                elif prp == 'k':
                    self.cfg['param']['k'] = kwargs[prp]
                elif prp == 'gamma':
                    self.cfg['param']['gamma'] = kwargs[prp]
                #else:
                #    self.cfg['param']['paradic'][prp] = kwargs[prp]
        self.cfg.save()
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")


    @cherrypy.expose
    @init_app
    def result(self, **kwargs):
        """
        display the algo results
        """
        VALID_KEYS = ['show']
        for prp in kwargs.keys():
            if prp in VALID_KEYS:
                if prp == 'show':
                    self.cfg['param']['show'] = kwargs[prp]
        self.cfg.save()
        return self.tmpl_out("result.html")


    def load_standard_parameters(self):
        """
        Four methods standard parameters
        """
       # paradic = {'sigma':'2.0', 'N':'5', 'k':'3', 'gamma':'0.5'}
        self.cfg['param']['sigma'] = '2.0'
        self.cfg['param']['n'] = '5'
        self.cfg['param']['k'] = '3'
        self.cfg['param']['gamma'] = '0.5'
        self.cfg.save()



    @cherrypy.expose
    @init_app
    def run(self):
        """
        Run run_semigroup and build an archive
        """
        work_dir = self.work_dir
        [w, h] = Image.open(work_dir+'input_0.orig.png').size
        self.cfg['param']['width'] = str(max(h, w) + 100)
        self.cfg.save()
        self.run_semigroup()
        ## archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.png", info="first input image")
            ar.add_file("keys_im0.txt", compress=True)
            ar.save()
        self.cfg.save()
        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html")





    def run_semigroup(self):
        """
        Run four binaries
        """
        #paradic = dict(eval(str(self.cfg['param']['paradic'])))
        param = dict(eval(str(self.cfg['param'])))
        image = 'input_0.png'

        ##dft
        meth = 'dft'
        f = open(self.work_dir+'rmse_'+meth+'.txt', 'w')
        dft = self.run_proc(['demo_gaussconv_dft', image,
            str(param['sigma']), str(param['n']), meth], stdout=f)
        self.wait_proc(dft, timeout=self.timeout)

        #dct
        meth = 'dct'
        f = open(self.work_dir+'rmse_'+meth+'.txt', 'w')
        dft = self.run_proc(['demo_gaussconv_dct', image,
            str(param['sigma']), str(param['n']), meth], stdout=f)
        self.wait_proc(dft, timeout=self.timeout)

        #sampled_discrete
        meth = 'sampled_kernel'
        f = open(self.work_dir+'rmse_'+meth+'.txt', 'w')
        dft = self.run_proc(['demo_gaussconv_sampled_kernel', image,
            str(param['sigma']), str(param['k']),
            str(param['n']), meth], stdout=f)
        self.wait_proc(dft, timeout=self.timeout)

        #lindeberg
        meth = 'lindeberg'
        f = open(self.work_dir+'rmse_'+meth+'.txt', 'w')
        dft = self.run_proc(['demo_gaussconv_lindeberg', image,
            str(param['sigma']), str(param['gamma']),
            str(param['n']), meth], stdout=f)
        self.wait_proc(dft, timeout=self.timeout)
        return 1

