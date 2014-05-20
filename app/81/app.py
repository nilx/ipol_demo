"""
Demo for the ball pivoting algorithm
"""

from lib import base_app, build, http
from lib.misc import ctime
from lib.base_app import init_app
import cherrypy
import fileinput
from cherrypy import TimeoutError
import os.path
import time
import gzip
import stat

# for custom input_select:
from lib.base_app import config
import shutil


#-------------------------------------------------------------------------------
# Demo main class
#-------------------------------------------------------------------------------
class app(base_app):
    """
    IPOL app class
    """
    # IPOL demo system configuration
    title = 'Ball Pivoting Algorithm'
    xlink_article = 'http://www.ipol.im/pub/pre/81/'
    input_max_weight = 100000000
    input_max_lines = 150000
    recommended_radius = str([0.1])
    size = 0.0
    is_test = False


    #---------------------------------------------------------------------------
    # set up application
    #---------------------------------------------------------------------------
    def __init__(self):
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() and input_xxx() are generic
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True
        # input_upload() is modified from the template
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True

    def build(self):
        """
        program build/update
        """
        tbz_filename = 'BallPivoting.tgz'
        prog_filename = 'ballpivoting'
        # store common file path in variables
        tbz_file = self.dl_dir + tbz_filename
        prog_file = self.bin_dir + prog_filename
        log_file = self.base_dir + "build.log"

        # get the latest source archive
        build.download('http://www.ipol.im/pub/pre/81/' + \
                       tbz_filename, tbz_file)

        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tbz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tbz_file, self.src_dir)

            # delete and create bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)

            # build the program
            program = 'ballpivoting'
            # build
            os.chdir(self.src_dir)
            build.run("cmake %s" % 'BallPivoting', stdout=log_file)
            build.run("make -j4", stdout=log_file)
            # move binary to bin dir
            shutil.copy(os.path.join(self.src_dir, \
                                     program),
                        os.path.join(self.bin_dir, program))

            # Move scripts to the base dir
            shutil.copy(os.path.join(self.src_dir, 'BallPivoting', 'scripts', \
                                         'ply2obj.py'), self.bin_dir)

            # Give exec permission to the script
            os.chmod(
                     os.path.join(
                                  self.bin_dir, "ply2obj.py"),
                     stat.S_IREAD | stat.S_IEXEC
                    )
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


    #
    # INDEX
    #
    @cherrypy.expose
    def index(self):
        """
        demo presentation and input menu
        """
        # read the input index as a dict
        inputd = config.file_dict(self.input_dir)
        return self.tmpl_out("input.html",
                             inputd=inputd)


    #---------------------------------------------------------------------------
    # upload points file
    #---------------------------------------------------------------------------
    #accessory function
    @cherrypy.expose
    def count_lines(self, filename):
        """
        Count the number of lines
        """

        fd = open(filename, 'r')
        line = fd.readline()
        maxx = float(line.split()[0])
        maxy = float(line.split()[1])
        maxz = float(line.split()[2])
        minx = maxx
        miny = maxy
        minz = maxz
        n = 1
        for line in fd:
            n += 1
            vals = [float(x) for x in line.split()]
            if vals[0] > maxx:
                maxx = vals[0]
            elif vals[0] < minx:
                minx = vals[0]
            if vals[1] > maxy:
                maxy = vals[1]
            elif vals[1] < miny:
                miny = vals[1]
            if vals[2] > maxz:
                maxz = vals[2]
            elif vals[2] < minz:
                maxz = vals[2]
        fd.close()
        self.size = maxx - minx
        sizey = maxy - miny
        if sizey > self.size:
            self.size = sizey
        sizez = maxz - minz
        if sizez > self.size:
            self.size = sizez
        return n

    @cherrypy.expose
    def subsample(self, filename, nlines):
        """
        subsample the input file
        """
        import math
        from random import random
        r = float(self.input_max_lines)/nlines
        f = open(filename, 'r')
        lines = [line for line in f if random() <= r]
        f.close()

        f = open(filename, 'w')
        nn = 0

        for line in lines:
            f.write("%s" % line)
            nn += 1
        f.close()
        r = self.size * math.sqrt(20.0/nn)
        self.recommended_radius = str([r])
        return nn

    @cherrypy.expose
    @staticmethod
    def normalize(filename):
        """
        normalize the point cloud
        """
        i = 0
        for line in fileinput.input(filename):
            p = [float(r) for r in line.split()]
            if i == 0:
                xmin = p[0]
                xmax = p[0]
                ymin = p[1]
                ymax = p[1]
                zmin = p[2]
                zmax = p[2]
            else:
                if p[0] < xmin:
                    xmin = p[0]
                elif p[0] > xmax:
                    xmax = p[0]
                if p[1] < ymin:
                    ymin = p[1]
                elif p[1] > ymax:
                    ymax = p[1]
                if p[2] < zmin:
                    zmin = p[2]
                elif p[2] > zmax:
                    zmax = p[2]
            i = i + 1

        sx = xmax - xmin
        sy = ymax - ymin
        sz = zmax - zmin

        ox = xmin + sx / 2.0
        oy = ymin + sy / 2.0
        oz = zmin + sz / 2.0

        smax = sx
        if smax < sy:
            smax = sy
        if smax < sz:
            smax = sz

        for line in fileinput.input(filename, inplace=1):
            p = [float(r) for r in line.split()]
            x = (p[0] - ox) / smax
            y = (p[1] - oy) / smax
            z = (p[2] - oz) / smax
            d = [x, y, z, p[3], p[4], p[5]]
            print '\t'.join(str(i) for i in d)

    @cherrypy.expose
    def input_upload(self, **kwargs):
        """
        upload a new point cloud
        """
        self.new_key()
        self.init_cfg()
        file_up = kwargs['input']
        filename = self.work_dir + 'input'
        file_save = file(filename, 'wb')

        if '' == file_up.filename:
            # missing file
            raise cherrypy.HTTPError(400, # Bad Request
                                     "Missing input file")

        if file_up.filename[-3:] != '.gz':
            # not the right format
            raise cherrypy.HTTPError(400, # Bad Request
                                     "Input file should be gzipped\
                                     (and have .gz extension)")
        size = 0
        while True:
            #larger data size
            data = file_up.file.read(128)
            if not data:
                break
            size += len(data)
            if size > self.input_max_weight:
                # file too heavy
                raise cherrypy.HTTPError(400, # Bad Request
                                         "File too large")
            file_save.write(data)
        file_save.close()

        #creating the file content
        filename_gz = filename
        filename_txt = self.work_dir + 'input.txt'

        file_save = gzip.open(filename_gz, 'r')
        file_content = file_save.read()
        file_save.close()

        file_save = open(filename_txt, 'w')
        file_save.write(file_content)
        file_save.close()

        #ensuring that the file is not above x-lines
        nlines = self.count_lines(filename_txt)
        self.subsample(filename_txt, nlines)

        #normalizing the point cloud
        self.normalize(filename_txt)

        msg = ""
        self.log("input uploaded")
        self.cfg['meta']['original'] = True
        self.cfg.save()
        return self.params(msg=msg, key=self.key)



    # --------------------------------------------------------------------------
    # INPUT STEP
    # --------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def input_select(self, **kwargs):
        """
        use the selected available input images
        """
        self.new_key()
        self.init_cfg()
        # get the point sets
        input_dict = config.file_dict(self.input_dir)
        input_id = kwargs['id']
        self.recommended_radius = input_dict[input_id]['radii']
        self.size = float(input_dict[input_id]['size'])
        fname = input_dict[input_id]['file']
        shutil.copy(self.input_dir + fname,
                        self.work_dir + 'input.txt')
        msg = ""
        self.log("input selected : %s" % input_id)
        self.cfg['meta']['original'] = False
        self.cfg.save()
        return self.params(msg=msg, key=self.key)

    @cherrypy.expose
    def clone_input(self):
        """
        clone the input for a re-run of the algo
        """
        self.log("cloning input from %s" % self.key)
        # get a new key
        old_work_dir = self.work_dir
        old_cfg_meta = self.cfg['meta']
        self.new_key()
        self.init_cfg()
        # copy the input files
        fname = 'input'
        shutil.copy(old_work_dir + fname,
                        self.work_dir + fname)
        # copy cfg
        self.cfg['meta'].update(old_cfg_meta)
        self.cfg.save()
        return



    #---------------------------------------------------------------------------
    # generate point selection page
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def params(self, r=None, newrun=False, msg=None):
        # return the parameters page
        if newrun:
            self.clone_input()

        return self.tmpl_out('params.html', r=r)

    #---------------------------------------------------------------------------
    # input handling and run redirection
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def wait(self, r="0.0003"):
        """
        params handling and run redirection
        """
        maxrad = 0.25 * self.size
        # save and validate the parameters
        try:
            self.cfg['param'] = {'r' : [float(x) for x in r.split()]}
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")
        try:
            for z in self.cfg['param']['r']:
                if z <= 0:
                    raise ValueError("radius must be positive")
                if z > maxrad:
                    raise ValueError("radius must be less than a quarter\
                            of the bounding box %f" % maxrad)
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The radii must be positive and less\
                              than half the bounding box (%f)" % maxrad)

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        self.cfg['info']['render_time'] = 0
        self.cfg.save()
        return self.tmpl_out("wait.html")

    #---------------------------------------------------------------------------
    # run the algorithm
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def run(self):
        # read the parameters
        r = self.cfg['param']['r']

        # run the algorithm
        try:
            self.run_algo(r)
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')

        f_in = open(self.work_dir+'output.ply', 'rb')
        f_out = gzip.open(self.work_dir+'output.ply.gz', 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            shutil.copy(self.work_dir + 'input',
                        self.work_dir + 'input.txt.gz')
            ar = self.make_archive()
            ar.add_file("input.txt.gz", info="input")
            ar.add_file("output.ply.gz", info="output")
            ar.add_info({"r": r})
            ar.save()


        return self.tmpl_out("run.html")

#---------------------------------------------------------------------------
# core algorithm runner
# it could also be called by a batch processor, this one needs no parameter
#---------------------------------------------------------------------------
    def run_algo(self, r):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        d = eval(r)
        stdout_file = open(self.work_dir + 'stdout.txt', 'w')
        run_time = time.time()
        p = self.run_proc(['ballpivoting', '-p', '-i', 'input.txt', '-r',\
                ' '.join(str(i) for i in d), '-o', 'output.ply'],\
                stdout=stdout_file)
        self.wait_proc(p, timeout=self.timeout)
        self.cfg['info']['run_time'] = time.time() - run_time
        #conversion
        p = self.run_proc(['ply2obj.py', 'output.ply', 'output.obj'],\
                stdout=stdout_file)
        self.wait_proc(p, timeout=self.timeout)
        stdout_file.close()
        self.cfg.save()

        return

#---------------------------------------------------------------------------
# display the algorithm result
#---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def result(self, r=None):
        stdout_str = open(self.work_dir + 'stdout.txt', 'r').read()
        stdout_str = stdout_str.replace("\n", "<br/>")


        return self.tmpl_out("result.html", r=r, stdout_str=stdout_str)


#-------------------------------------------------------------------------------


