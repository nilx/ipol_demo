"""
The Flutter Shutter Code Calculator
"""

from lib import base_app, build, http
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time
import subprocess

class app(base_app):
    """ The Flutter Shutter Code Calculator app """

    title = "The Flutter Shutter Code Calculator"
    xlink_article = 'http://www.ipol.im/'

    input_nb = 0
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
        tgz_file = self.dl_dir + "source_code_calculator_1.zip"
        prog_file = self.bin_dir + "flutter_optimizer"
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download("http://www.ipol.im/pub/pre/108/" +\
                       "source_code_calculator_1.zip", \
                       tgz_file)

        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive

            build.extract(tgz_file, self.src_dir)
            # build the program


            build.run("make -j4 -C %s %s " % (self.src_dir+"srcflutteropt_1",
                      os.path.join("flutter_optimizer")),stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir + "srcflutteropt_1/flutter_optimizer" \
, prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return





    @cherrypy.expose
    @init_app
    def params(self, action=None, newrun=False, msg=None, \
motion_model="Gaussian (truncated at 4*std-dev)", s1="0.25", s2="1", \
s3="52", s4="2"):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        if action == 'run':
            try:
                self.cfg['param'] = {'motion_model' : motion_model,
                             's1' : float(s1),
                             's2' : float(s2),
                             's3' : float(s3),
                             's4' : float(s4)
                             }
                self.cfg.save()
                http.redir_303(self.base_url + "wait?key=%s" % self.key)
            except ValueError:
                return self.error(errcode='badparams',
                                      errmsg="Bad parameters!")

        if motion_model == 'Trimodal: \
rho(v)= rho_0*delta_0(v)+(1/2)*(1-rho_0)*delta_s(v)+(1/2)*(1-rho_0)*\
delta_{-s}(v)':
            return self.tmpl_out("params_h.html", msg=msg
, motion_model=motion_model, s1=s1, s2=s2, s3=s3, s4=s4)

        if motion_model == 'Uniform over [-s,s]':
            return self.tmpl_out("params_u.html", msg=msg
, motion_model=motion_model, s1=s1, s2=s2, s3=s3, s4=s4)

        return self.tmpl_out("params_g.html", msg=msg
, motion_model=motion_model, s1=s1, s2=s2, s3=s3, s4=s4)


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
        motion_model = self.cfg['param']['motion_model']
        s1 = self.cfg['param']['s1']
        s2 = self.cfg['param']['s2']
        s3 = self.cfg['param']['s3']
        s4 = self.cfg['param']['s4']
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(s1, s2, s3, s4, motion_model, stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')

        stdout.close()

        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        # archive

        ar = self.make_archive()
        ar.add_file("code.png", info="flutter code")
        ar.add_file("TF_code.png", info="Fourier transform of the \
flutter shutter function")
        ar.add_file("efficiency.png", info="RMSE factor curves")
        ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, s1, s2, s3, s4, motion_model, stdout=None, \
                 timeout=False):

        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """


        if motion_model == 'Trimodal: \
rho(v)= rho_0*delta_0(v)+(1/2)*(1-rho_0)*delta_s(v)+(1/2)*(1-rho_0)*\
delta_{-s}(v)':
            p = self.run_proc(['flutter_optimizer', '2', str(s2), str(s3), \
str(s4), str(s1), 'code.txt', 'TF_code.txt', 'efficiency.txt', 'mean_sdt.txt']\
, stdout=stdout, stderr=None)
            self.wait_proc(p, timeout=timeout)


        if motion_model == 'Gaussian (truncated at 4*std-dev)':
            p = self.run_proc(['flutter_optimizer', '0', str(s1), \
str(s3), str(s4), 'code.txt', 'TF_code.txt', 'efficiency.txt', 'mean_sdt.txt']\
, stdout=stdout, stderr=None)
            self.wait_proc(p, timeout=timeout)


        if motion_model == 'Uniform over [-s,s]':
            p = self.run_proc(['flutter_optimizer', '1', str(s1), \
str(s3), str(s4), 'code.txt', 'TF_code.txt', 'efficiency.txt', 'mean_sdt.txt']\
, stdout=stdout, stderr=None)
            self.wait_proc(p, timeout=timeout)


        if motion_model == 'Trimodal: \
rho(v)= rho_0*delta_0(v)+(1/2)*(1-rho_0)*delta_s(v)+(1/2)*(1-rho_0)*\
delta_{-s}(v)':
            p = subprocess.Popen(['gnuplot','-p'],
                        shell=True,
                        stdin=subprocess.PIPE,
                        )
            p.stdin.write( ' set lmargin 10 ;  set rmargin 2 \n')
            p.stdin.write( ' set xlabel "Velocity v" \n')
            p.stdin.write( ' set ylabel "Gain factor" \n')
            p.stdin.write( ' set yrange [0:5] \n ')
            p.stdin.write( ' set terminal png size 900, 480\n')
            p.stdin.write( ' set output "'+ self.work_dir +'efficiency.png" \n')
            p.stdin.write( ' set key on  below box title "Legend" \n')
            p.stdin.write( ' set key left Left reverse \n ' )
            p.stdin.write( ' plot "'+ self.work_dir +'efficiency.txt" using \
1:2 with lines title "Gain factor G(v)" linewidth 3,' )
            p.stdin.write( ' "' + self.work_dir +'efficiency.txt" using 1:3 \
with lines title "Average gain factor" linewidth 3,' )
            p.stdin.write( ' "' + self.work_dir +'efficiency.txt" using 1:4 \
with lines title "Motion model" linewidth 5, ' )
            p.stdin.write( ' "' + self.work_dir +'efficiency.txt" using 1:5 \
with dots title "Gain=1 line. Above this line: the flutter beats the \
snapshot in terms of RMSE" linewidth 2\n' )
            p.stdin.write(' exit \n')
            p.communicate()
            self.wait_proc(p, timeout=timeout)


        if motion_model == 'Gaussian (truncated at 4*std-dev)':
            p = subprocess.Popen(['gnuplot','-p'],
                        shell=True,
                        stdin=subprocess.PIPE,
                        )
            p.stdin.write( ' set lmargin 10 ;  set rmargin 2 \n')
            p.stdin.write( ' set xlabel "Velocity v" \n')
            p.stdin.write( ' set ylabel "Gain factor" \n')
            p.stdin.write( ' set yrange [0:5] \n ')
            p.stdin.write( ' set terminal png size 900, 480\n')
            p.stdin.write( ' set output "'+ self.work_dir +'efficiency.png" \n')
            p.stdin.write( ' set key on  below box title "Legend" \n')
            p.stdin.write( ' set key left Left reverse \n ' )
            p.stdin.write( ' plot "'+ self.work_dir +'efficiency.txt" \
using 1:2 with lines title "Gain factor G(v)" linewidth 3,' )
            p.stdin.write( ' "' + self.work_dir +'efficiency.txt" using 1:3 \
with lines title "Average gain factor" linewidth 3,' )
            p.stdin.write( ' "' + self.work_dir +'efficiency.txt" using 1:4 \
with dots title "Motion model" linewidth 5,' )
            p.stdin.write( ' "' + self.work_dir +'efficiency.txt" using 1:5 \
with dots title "Gain=1 line. Above this line: the flutter beats the \
snapshot in terms of RMSE" linewidth 2\n' )
            p.stdin.write(' exit \n')
            p.communicate()
            self.wait_proc(p, timeout=timeout)

        if motion_model == 'Uniform over [-s,s]':
            p = subprocess.Popen(['gnuplot','-p'],
                        shell=True,
                        stdin=subprocess.PIPE,
                        )
            p.stdin.write( ' set lmargin 10 ;  set rmargin 2 \n')
            p.stdin.write( ' set xlabel "Velocity v" \n')
            p.stdin.write( ' set ylabel "Gain factor" \n')
            p.stdin.write( ' set yrange [0:5] \n ')
            p.stdin.write( ' set terminal png size 900, 480\n')
            p.stdin.write( ' set output "'+ self.work_dir +'efficiency.png" \n')
            p.stdin.write( ' set key on  below box title "Legend" \n')
            p.stdin.write( ' set key left Left reverse \n ' )
            p.stdin.write( ' plot "'+ self.work_dir +'efficiency.txt" using \
1:2 with lines title "Gain factor G(v)" linewidth 3,' )
            p.stdin.write( ' "' + self.work_dir +'efficiency.txt" using 1:3 \
with lines title "Average gain factor" linewidth 3,' )
            p.stdin.write( ' "' + self.work_dir +'efficiency.txt" using 1:4 \
with dots title "Motion model" linewidth 5,' )
            p.stdin.write( ' "' + self.work_dir +'efficiency.txt" using 1:5 \
with dots title "Gain=1 line. Above this line: the flutter beats the \
snapshot in terms of RMSE" linewidth 2\n' )
            p.stdin.write(' exit \n')
            p.communicate()
            self.wait_proc(p, timeout=timeout)



        p = subprocess.Popen(['gnuplot','-p'],
                        shell=True,
                        stdin=subprocess.PIPE,
                        )
        p.stdin.write( ' set lmargin 10 ;  set rmargin 2 \n')
        p.stdin.write( ' set key font ",10" \n')
        p.stdin.write( ' set xlabel "k" \n')
        p.stdin.write( ' set ylabel "Gain" \n')
        p.stdin.write( ' set terminal png size 900, 480\n')
        p.stdin.write( ' set output "'+ self.work_dir +'code.png" \n')
        p.stdin.write( ' set key on  below box title "Legend" \n')
        p.stdin.write( ' set key left Left reverse \n ' )
        p.stdin.write( ' plot "'+ self.work_dir +'code.txt" with steps title \
"Flutter shutter code" linewidth 3 \n' )
        p.stdin.write(' exit \n')



        p = subprocess.Popen(['gnuplot','-p'],
                        shell=True,
                        stdin=subprocess.PIPE,
                        )
        p.stdin.write( ' set lmargin 5 ;  set rmargin 2 \n')
        p.stdin.write( ' set key font ",10" \n')
        p.stdin.write( ' set xlabel "xi" \n')
        p.stdin.write( ' set ylabel "Fourier tranform (modulus)" \n')
        p.stdin.write( ' set terminal png size 900, 480\n')
        p.stdin.write( ' set output "'+ self.work_dir +'TF_code.png" \n')
        p.stdin.write( ' set key on  below box title "Legend" \n')
        p.stdin.write( ' set key left Left reverse \n ' )
        p.stdin.write( ' plot "'+ self.work_dir +'TF_code.txt" using 1:3 with \
lines title "Fourier tranform (modulus) of the flutter shutter function" \
linewidth 3,' )
        p.stdin.write( ' "' + self.work_dir +'TF_code.txt" using 1:2 with \
lines title "Ideal Fourier tranform (modulus)" linewidth 3\n' )
        p.stdin.write(' exit \n')
        p.communicate()
        self.wait_proc(p, timeout=timeout)


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        return self.tmpl_out("result.html",
                             height=480)
