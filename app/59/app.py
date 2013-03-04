"""
Efros-Leung Texture Synthesis demo web app
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
    """ Efros-Leung Texture Synthesis app """

    title = 'Efros-Leung Texture Synthesis'

    input_nb = 1
    input_max_pixels = 256 * 256        # max size (in pixels) of input image
    input_max_weight = 10 * 256 * 256 # max size (in bytes) of input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False

    def __init__(self):
        """
        App setup
        """
        # Setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # Select the base_app steps to expose
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
        tgz_file = self.dl_dir + "efros_leung_v1.0.tar.gz"
        prog_file = self.bin_dir + "efros_leung"
	prog_file_ac = self.bin_dir + "efrosLeung_accel"
        log_file = self.base_dir + "build.log"

        # get the latest source archive
        build.download("http://www.ipol.im/pub/pre/59/" +
                       "efros_leung_v1.0.tar.gz", tgz_file)

        # test if the dest file is missing, or too old
        # dont rebuild the file
        if  (os.path.isfile(prog_file)
            and os.path.isfile(prog_file_ac)
	    and ctime(tgz_file) < ctime(prog_file)
	    and ctime(tgz_file) < ctime(prog_file_ac)) :
            cherrypy.log("Not rebuild needed",
            context='BUILD', traceback=False)
        else:
            #extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -C %s"
                      % (self.src_dir + "efros_leung_v1.0/efros_leung_orig/src/" ), stdout=log_file)
            # build the program
            build.run("make -C %s"
                      % (self.src_dir + "efros_leung_v1.0/efros_leung_accel/src/" ), stdout=log_file)

            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir + os.path.join("efros_leung_v1.0/efros_leung_orig/src/",
                        "efros_leung"), prog_file)
            shutil.copy(self.src_dir + os.path.join("efros_leung_v1.0/efros_leung_accel/src/",
                        "efrosLeung_accel"), prog_file_ac)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


    @cherrypy.expose
    @init_app
    def crop(self, o = "128", ps = "5", t = "0.1", action=None, x=None, y=None,
             x0=None, y0=None, x1=None, y1=None, newrun=False):
        """
        select a rectangle in the image
        """
        if newrun:
            self.clone_input()

        # Save the current parameter values        
        self.cfg['param']['o'] = o
        self.cfg['param']['ps'] = ps
        self.cfg['param']['t'] = t
        self.cfg.save()

        if action == 'run':
	    a = 1
	    self.cfg['param']['a'] = a
            self.cfg.save()
            if x1 == None:
                # use the whole image
                img = image(self.work_dir + 'input_0.png')
                img.save(self.work_dir + 'input' + self.input_ext)
                img.save(self.work_dir + 'input.png')
            else:
                self.cfg['param']['x0'] = x0
                self.cfg['param']['y0'] = y0
                self.cfg['param']['x1'] = x1
                self.cfg['param']['y1'] = y1
            # go to the wait page, with the key
            http.redir_303(self.base_url + "wait?key=%s&a=%s&o=%s&ps=%s&t=%s" 
                           % (self.key, a, o, ps, t))
            return
        elif action == 'run_orig':
            a = 0
	    self.cfg['param']['a'] = a
	    self.cfg.save()
            if x1 == None:
                # use the whole image
                img = image(self.work_dir + 'input_0.png')
                img.save(self.work_dir + 'input' + self.input_ext)
                img.save(self.work_dir + 'input.png')
            else:
                self.cfg['param']['x0'] = x0
                self.cfg['param']['y0'] = y0
                self.cfg['param']['x1'] = x1
                self.cfg['param']['y1'] = y1
            # go to the wait page, with the key
            http.redir_303(self.base_url + "wait?key=%s&a=%s&o=%s&ps=%s&t=%s" 
                           % (self.key, a, o, ps, t))
            return
        else:
            # use a part of the image
            if x0 == None:
                if x == None:
                    return self.tmpl_out("params.html", o=o, ps=ps, t=t)
                else:
                    # first corner selection
                    x = int(x)
                    y = int(y)
                    # draw a cross at the first corner
                    img = image(self.work_dir + 'input_0.png')
                    img.draw_cross((x, y), size=4, color="white")
                    img.draw_cross((x, y), size=2, color="red")
                    img.save(self.work_dir + 'input_corner.png')
                    return self.tmpl_out("params.html",
                                         x0=x, y0=y, o=o, ps=ps, t=t)
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
                # draw selection rectangle on the image
                img = image(self.work_dir + 'input_0.png')
                img.draw_line([(x0, y0), (x1, y0), 
                               (x1, y1), (x0, y1), (x0, y0)], color="red")
                img.draw_line([(x0+1, y0+1), (x1-1, y0+1),
                               (x1-1, y1-1), (x0+1, y1-1),
                               (x0+1, y0+1)], color="white")
                img.save(self.work_dir + 'input_selection.png')
                # crop from the original input image
                img = image(self.work_dir + 'input_0.png')
                img_ = image(self.work_dir + 'input_0.png')
                (nx, ny) = img.size
                (nx_, ny_) = img_.size
                (zx, zy) = (float(nx) / float(nx_),
                            float(ny) / float(ny_))
                img.crop((int(x0 * zx), int(y0 * zy),
                          int(x1 * zx), int(y1 * zy)))
                img.save(self.work_dir + 'input' + self.input_ext)
                img.save(self.work_dir + 'input.png')
                return self.tmpl_out("params.html",
                                     x0=x0, y0=y0, x1=x1, y1=y1, o=o, ps=ps, t=t)
            return


    @cherrypy.expose
    @init_app
    def wait(self, a, o = "128", ps = "3", t = "0.1"):
        """
        params handling and run redirection
        """
        try:
            self.cfg['param'] = {'a' : int(a),
				'o' : int(o), 
				'ps' : int(ps),
				't' : float(t)}			                                        
            self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")
 
	http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None):
        """
        configure the algo execution
        """
        return self.tmpl_out("params.html", msg=msg,
                             input = ['input_%i.png' % i
                                      for i in range(self.input_nb)])


    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        # read the parameters
	a = self.cfg['param']['a']
        o = self.cfg['param']['o']
        ps = self.cfg['param']['ps']
        t = self.cfg['param']['t']
        # save standard output
        stdout = open(self.work_dir + 'stdout.txt', 'w')
 
	try:
	    if a == 1:
	            run_time = time.time()
        	    self.run_algo(a,o,ps,t,stdout=stdout)
        	    self.cfg['info']['run_time'] = time.time() - run_time
        	    self.cfg.save()
	    else:
	            run_time = time.time()
        	    self.run_algo_original(a,o,ps,t,stdout=stdout)
        	    self.cfg['info']['run_time'] = time.time() - run_time
        	    self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            stdout_text = open(self.work_dir + 'stdout.txt', 'r').read() 
            if stdout_text.find("The dictionary is too too small.")!=-1:
                return self.error("returncode",
                                  "The dictionary is too too small." + 
                                  "If the sample image is too small" +
                                  " choose an smaller patch size.") 
            if stdout_text.find("The patch size is too large.")!=-1:
                return self.error('returncode', 'The patch size is too large.')
            if stdout_text.find("Incorrect number of PCA components.")!=-1:
                return self.error('returncode', 'Incorrect number of PCA components ( 0 < d <= (2*ps + 1)*ps).')
            return self.error('returncode', 'Unknown Run Time Error')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input.png", info="input image")
            ar.add_file("output.png", info="output image")
            try:
                fh = open(self.work_dir + 'input_selection.png')
                fh.close()
                ar.add_file("input_selection.png", info="input selection")
                ar.add_file("input_0.orig.png", info="uploaded image")
            except IOError:
                pass
            ar.add_info({"a": a,"o": o, "ps": ps, "t": t})
            ar.save()

        return self.tmpl_out("run.html")


    def run_algo(self,a, o, ps, t, stdout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
	p = self.run_proc(['efrosLeung_accel',
                                    'input.png',
				    '-p',
			  	    str(ps),
				    '-t',
			  	    str(t),
				    '-s',
                        	    str(o),
                          	    'output.png',
			  	    'map.png',
                         	    'copy_map.png'],
			 	    stdout=stdout, stderr=stdout )  
        
        self.wait_proc(p)

    def run_algo_original(self, a, o, ps, t, stdout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        p = self.run_proc(['efros_leung',
                                   'input.png',
				    '-p',
                                    str(ps),
                                    '-t',  
				    str(t),
                                    '-s', 
                                    str(o),
                                    'output.png',
                                    'map.png',
                                    'copy_map.png'],
                                    stdout=stdout, stderr=stdout )

        self.wait_proc(p)
                


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        return self.tmpl_out("result.html",
                             height=image(self.work_dir
                                          + 'output.png').size[1])

