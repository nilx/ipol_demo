"""
Computing Visual Correspondence with Occlusions using Graph Cuts demo
interaction script
"""
# pylint: disable-msg=C0103

from lib import base_app
from lib import build
from lib import image
from lib.misc import get_check_key, http_redirect_303, app_expose
from lib.misc import index_dict, ctime
import cherrypy
from cherrypy import TimeoutError
import os.path
import time
import shutil

#
# FRACTION UTILITY FUNCTIONS
#

def gcd(q):
    """
    compute the greatest common divider, Euclid algorithm
    """
    (a, b) = q
    if 0 == b:
        return a
    return gcd((b, a % b))

def simplify_frac(q):
    """
    simplify a fraction
    """
    (a, b) = q
    assert 0 != b
    g = gcd((a, b))
    return (a / g, b / g)

def str2frac(qstr):
    """
    parse the string representation of a rational number
    """
    # handle simple integer cases
    if not '/' in qstr:
        qstr += "/1"
    # split the fraction
    (a, b) = [int(x) for x in qstr.split('/')][:2]
    return simplify_frac((a, b))

def frac2str(q):
    """
    represent a rational number as string
    """
    q = simplify_frac(q)
    if 1 == q[1]:
        return "%i" % q[0]
    else:
        return "%i/%i" % q
#
# INTERACTION
#

class app(base_app):
    """ template demo app """
    
    title = "Computing Visual Correspondence with Occlusions using Graph Cuts"
    description = """V. Kolmogorov and R. Zabih's method tries to minimize an 
    energy defined on all possible configurations.<br />
    Please select two images; color images will be converted into gray
    level; images larger than 1M pixels will be resized."""

    input_nb = 2 # number of input images
    input_max_pixels = 1024*1024 # max size (in pixels) of an input image
    input_max_method = 'zoom'
    input_dtype = '3x8i' # input image expected data type    
    input_ext = '.ppm'   # input image expected extension (ie file format)    
    is_test = True       # switch to False for deployment

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() is generic
        app_expose(base_app.index)
        app_expose(base_app.input_select)
        app_expose(base_app.input_upload)
        # params() is modified from the template
        app_expose(base_app.params)
        # run() and result() must be defined here

    def build(self):
        """
        program build/update
        """
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        # store common file path in variables
        match_tgz_file = os.path.join(self.dl_dir, "match.tar.gz")
        match_tgz_url = "https://edit.ipol.im/edit/algo/" \
            + "ltp_stereovision_with_graph_cuts/match.tar.gz"
        match_prog_file = os.path.join(self.bin_dir, "match")
        match_log_file = os.path.join(self.base_dir, "build_match.log")
        autok_tgz_file = os.path.join(self.dl_dir, "autoK.tar.gz")
        autok_tgz_url = "https://edit.ipol.im/edit/algo/" \
            + "ltp_stereovision_with_graph_cuts/autoK.tar.gz"
        autok_prog_file = os.path.join(self.bin_dir, "autoK")
        autok_log_file = os.path.join(self.base_dir, "build_autok.log")
        # get the latest source archive
        build.download(match_tgz_url, match_tgz_file)
        build.download(autok_tgz_url, autok_tgz_file)
        # MATCH
        # test if the dest file is missing, or too old
        if (os.path.isfile(match_prog_file)
            and ctime(match_tgz_file) < ctime(match_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(match_tgz_file, self.src_dir)
            # build the program
            build.run("make -C %s ../bin/match" %
                      os.path.join(self.src_dir, "match-v3.3.src", "unix")
                      + " CCOMP='ccache c++' -j4", stdout=match_log_file)
            # save into bin dir
            shutil.copy(os.path.join(self.src_dir,
                                     "match-v3.3.src", "bin", "match"),
                        match_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        # AUTOK
        # test if the dest file is missing, or too old
        if (os.path.isfile(autok_prog_file)
            and ctime(autok_tgz_file) < ctime(autok_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(autok_tgz_file, self.src_dir)
            # build the program
            build.run("make -C %s ../bin/autoK" %
                      os.path.join(self.src_dir, "autoK", "unix")
                      + " CCOMP='ccache c++' -j4", stdout=autok_log_file)
            # save into bin dir
            shutil.copy(os.path.join(self.src_dir, "autoK", "bin", "autoK"),
                        match_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    @cherrypy.expose
    @get_check_key
    def run(self, **kwargs):
        """
        params handling and run redirection
        """
        # save and validate the parameters
        try:
            params_file = index_dict(self.path('tmp'))
            params_file['params'] = {}
            if 'K' in kwargs:
                k = str2frac(kwargs['K'])
                params_file['params']['k'] = frac2str(k)
            if 'lambda' in kwargs:
                lambda_ = str2frac(kwargs['lambda'])
                params_file['params']['lambda'] = frac2str(lambda_)
            params_file.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be rationals.")

        # redirect to the result page
        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')]}
        return self.tmpl_out("run.html", urld=urld,
                             height=image(self.path('tmp', 
                                                    'input_0.png')).size[1])

    def compute_k_auto(self):
        """
        compute default K and lambda values
        """
        # create autok.conf file
        kfile = open(self.path('tmp', 'autok.conf'), 'w')
        kfile.write("LOAD_COLOR input_0.ppm input_1.ppm\n")
        kfile.write("SET disp_range -15 0 0 0\n")
        kfile.close()
        
        # run autok
        stdout = open(self.path('tmp', 'stdout.txt'), 'w')
        p = self.run_proc(['autoK', 'autok.conf'],
                          stdout=stdout, stderr=stdout)
        self.wait_proc(p)
        stdout.close()
        
        # get k from stdout
        stdout = open(self.path('tmp', 'stdout.txt'), 'r')
        k_auto = str2frac(stdout.readline()) 
        lambda_auto = simplify_frac((k_auto[0], k_auto[1] * 5))
        stdout.close()
        params_file = index_dict(self.path('tmp'))
        params_file['params']['k_auto'] = frac2str(k_auto)
        params_file['params']['lambda_auto'] = frac2str(lambda_auto)
        params_file.save()
        return (k_auto, lambda_auto)

    def run_algo(self, timeout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        # get the default parameters
        params_file = index_dict(self.path('tmp'))
        if 'k_auto' not in params_file['params']:
            del params_file
            (k_auto, lambda_auto) = self.compute_k_auto()
            params_file = index_dict(self.path('tmp'))
        else:
            k_auto = str2frac(params_file['params']['k_auto'])
            lambda_auto = str2frac(params_file['params']['lambda_auto'])

        # use default or overrriden parameter values
        params_file['params']['k_used'] = \
            params_file['params'].get('k', frac2str(k_auto))
        params_file['params']['lambda_used'] = \
            params_file['params'].get('lambda', frac2str(lambda_auto))
        params_file.save()

        # split the input images
        nproc = 6   # number of slices
        margin = 6  # overlap margin 

        input0_fnames = image(self.path('tmp', 'input_0.ppm')) \
            .split(nproc, margin=margin,
                   fname=self.path('tmp', 'input0_split.ppm'))
        input1_fnames = image( self.path('tmp', 'input_1.ppm')) \
            .split(nproc, margin=margin,
                   fname=self.path('tmp', 'input1_split.ppm'))
        output_fnames = ['output_split.__%0.2i__.png' % n
                         for n in range(nproc)]
        plist = []
        for n in range(nproc):
            # creating the conf files (one per process)
            conf_file = open(self.path('tmp', 'match_%i.conf' % n),'w')
            conf_file.write("LOAD_COLOR %s %s\n"
                            % (input0_fnames[n], input1_fnames[n]))
            conf_file.write("SET disp_range -15 0 0 0\n")
            conf_file.write("SET iter_max 30\n")
            conf_file.write("SET randomize_every_iteration\n")
            conf_file.write("SET k %s\n"
                            % params_file['params']['k_used'])
            conf_file.write("SET lambda %s\n"
                            % params_file['params']['lambda_used'])
            conf_file.write("KZ2\n")
            conf_file.write("SAVE_X_SCALED %s\n" % output_fnames[n])
            conf_file.close()
            # run each process
            plist.append(self.run_proc(['match', 'match_%i.conf' %n],
                                       ))
        self.wait_proc(plist, timeout)

        # join all the partial results into a global one
        output_img = image().join([image(self.path('tmp', output_fnames[n]))
                                   for n in range(nproc)], margin=margin)
        output_img.save(self.path('tmp', fname='disp_output.ppm'))

        # delete the strips
        for fname in input0_fnames + input1_fnames:
            os.unlink(fname)
        for fname in output_fnames:
            os.unlink(self.path('tmp', fname))
        return

    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # no parameters
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout)
            run_time = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="""
The algorithm took more than %i seconds and had to be interrupted.
Try again with simpler images.""" % self.timeout)
        except RuntimeError:
            return self.error(errcode='retime',
                              errmsg="""
The program ended with a failure return code,
something must have gone wrong""")
        self.log("input processed")
        
        params_file = index_dict(self.path('tmp'))

        im = image(self.path('tmp', 'disp_output.ppm'))
        im.save(self.path('tmp', 'dispmap.png'))
        
        urld = {'new_input' : self.url('index'),
                'run' : self.url('run'),
                'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')],
                'output' : [self.url('tmp', 'dispmap.png')]}
                
        params_file = index_dict(self.path('tmp'))
        k_used = params_file['params']['k_used']
        lambda_used = params_file['params']['lambda_used']
        k_auto = params_file['params']['k_auto']
        k = str2frac(k_auto)
        l = (k[0], k[1] * 5)
        k_proposed = [frac2str((k[0] * 1, k[1] * 2)),
                      frac2str((k[0] * 2, k[1] * 3)),
                      frac2str((k[0] * 1, k[1] * 1)),
                      frac2str((k[0] * 3, k[1] * 2)),
                      frac2str((k[0] * 2, k[1] * 1))]
        l_proposed = [frac2str((l[0] * 1, l[1] * 2)),
                      frac2str((l[0] * 2, l[1] * 3)),
                      frac2str((l[0] * 1, l[1] * 1)),
                      frac2str((l[0] * 3, l[1] * 2)),
                      frac2str((l[0] * 2, l[1] * 1))]

        return self.tmpl_out("result.html", urld=urld,
                             run_time="%0.2f" % run_time,
                             height=image(self.path('tmp', 
                                                    'input_0.png')).size[1],
                             k_used=k_used,
                             lambda_used=lambda_used,
                             k_proposed=k_proposed,
                             l_proposed=l_proposed)

