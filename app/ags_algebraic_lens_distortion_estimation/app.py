"""
Algebraic Lens Distortion Model Estimation ipol demo web app
"""

from lib import base_app, build, http
from lib.misc import ctime
from lib.base_app import init_app
from lib.config import cfg_open
import shutil
import cherrypy
from cherrypy import TimeoutError
from lib import image
import math
import os.path
import time

import json
import subprocess 



class app(base_app):
    """ Algebraic Lens Distortion Model Estimation app """

    title = 'Algebraic Lens Distortion Model Estimation'
    xlink_article = 'http://www.ipol.im/pub/art/2011/ags-alde/'

    input_nb = 1
    input_max_pixels = 1048576          # max size (in pixels) input image
    input_max_weight = 3 * 1024 * 1024  # max size (in bytes) input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.bmp'                  # expected extension
    is_test = False

    first_run = True
    old_work_dir = ''
    orig_work_dir = ''

    # Default parameters
    default_param = dict(
            {'x_center'                      : 256,
             'y_center'                      : 256,
             'optimized'                     : 0,
             'viewport_width'                : 740,
             'viewport_height'               : 600,
             'img_width'                     : 512,
             'img_height'                    : 512,
             'zoom'                          : 0,
             'zoom_default'                  : 0,
             'scrollx'                       : 0,
             'scrolly'                       : 0,
             'poly'                          : json.dumps( [[]] ),
             'background'                    : '',
             'foreground'                    : '',
             'action'                        : ''
             }.items() )



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
        ## Generate a new timestamp
        timestamp = int(100*time.time())        

    def build(self):
        """
        Program build/update
        """
        # Store common file path in variables
        tgz_url = 'http://www.ipol.im/pub/art/2011/ags-alde/' \
            + 'algebraic_lens_distortion_model_estimation_basic_march_2012.tar.gz'

        tgz_file = self.dl_dir + \
              'algebraic_lens_distortion_model_estimation_basic_march_2012.tar.gz'
                             
        progs = ['lens_distortion_estimation']
        
        sub_dir = 'algebraic_lens_distortion_model_estimation_basic'
        
        src_bin = dict([(self.src_dir + os.path.join(sub_dir, prog),
                         self.bin_dir + prog) for prog in progs])
        log_file = self.base_dir + 'build.log'
        
        ## Get the latest source archive
        build.download(tgz_url, tgz_file)
        
        # Test if any dest file is missing, or too old
        if all([(os.path.isfile(bin_file) and  \
            ctime(tgz_file) < ctime(bin_file)) \
            for bin_file in src_bin.values()]):
            cherrypy.log('not rebuild needed', context='BUILD', traceback=False)
        else:
            # Extract the archive
            build.extract(tgz_file, self.src_dir)

            # Build the programs
            build.run("make -C %s %s" %  \
                      (self.src_dir + sub_dir, " ".join(progs))
                    + " --makefile=makefile", stdout=log_file)

            # Save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for (src, dst) in src_bin.items():
                shutil.copy(src, dst)
            # Cleanup the source dir
            shutil.rmtree(self.src_dir)
        return




    def input_points_file(self):
        """
        write the poly points in a file
        """      

        pfile = self.work_dir + 'index.cfg'

        if os.path.isfile( pfile ) :
            self.cfg['param'] = cfg_open(pfile, 'rb')['param']
        else :
            self.cfg['param'] = dict(self.default_param, **self.cfg['param'])

        ### ....................

        points = self.work_dir + "line_primitives.dat"
        ofile = file(points, "w")

        lines = json.loads( self.cfg['param']['poly'] )

        ofile.writelines("%i\n" % len(lines) )

        for ii in range(0, len(lines)) :

            ofile.writelines("%i\n" % len(lines[ii]) )
            ofile.writelines("%i %i \n" % (x, y) for (x, y) in lines[ii] )

        ofile.close()




    def draw_poly(self, param):
        """
        draw the point store in param['poly']
        """      

        poly = json.loads( param['poly'] )
        zoom = param['zoom']

        width  = 2**zoom * param['img_width'] 
        height = 2**zoom * param['img_height']

        gifparam = 'GIF:' + self.work_dir + 'foreground.gif'

        ## .................................

        ptargs = []
        lnargs = []
        
        ptrad = 3
        
        ptargs = ['-stroke', '#00FF00', '-strokewidth', \
                   '1.5', '-fill', '#00FF00']
        
        lnargs = ['-stroke', '#FF0000', '-fill', 'none']


        for ii in range(0, len(poly)) :

            ptargs += ['-draw', ' '.join(['circle %(x)i,%(y)i %(x)i,%(y_r)i'
                                         % {'x' : x * 2 ** zoom,
                                            'y' : y * 2 ** zoom,
                                            'y_r' : y * 2 ** zoom - ptrad}
                                            for (x, y) in poly[ii] ])]

            lnargs += ['-draw', ('polyline ' + ' '.join(['%(x)i,%(y)i '
                                                 % {'x' : x * 2 ** zoom,
                                                    'y' : y * 2 ** zoom}
                                                    for (x, y) in poly[ii] ]))]

        ## .................................

        cmdrun = ['convert', '-quality', '100', '+antialias', '-size', \
                  str(width) + 'x' + str(height), \
                  'xc:transparent'] + ptargs + lnargs + [gifparam ]
        subprocess.Popen( cmdrun ).wait()





## .................................  ## .................................

    @classmethod
    def get_zoom_default( cls, param):
        """
        get the zoom default value
        """

        viewport_width  = param['viewport_width']
        viewport_height = param['viewport_height']

        img_width  = param['img_width']
        img_height = param['img_height']

        zoom_default = math.floor(min(( \
              math.log(viewport_width)  - math.log(img_width))  / math.log(2), \
              (math.log(viewport_height) - math.log(img_height)) / math.log(2)))

        return zoom_default


    ## .................

    def check_zoom(self, value, param):
        """
        check if the zoom parameter is the the range allowed
        """      
        zoom_default = self.get_zoom_default( param )
        zoom_max = zoom_default + 2
        zoom_min = zoom_default - 2        

        zoom = float(value)

        if zoom < zoom_min:
            zoom = zoom_min
        if zoom > zoom_max:
            zoom = zoom_max

        return zoom    


    ## .................

    def check_action(self, action, spoly, param):
        """
        check the action given by the user
        """      
        param['poly'] = spoly

        if action == 'delete last point' :
            poly = json.loads( spoly )

            if len( poly[len(poly)-1] ) > 0:
                poly[len(poly)-1].pop()
                param['poly'] = json.dumps( poly )
                spoly = param['poly']
                
            if len( poly[len(poly)-1] ) < 3:
                param['optimized'] = 0

        elif action == 'delete last line' :
            poly = json.loads( spoly )
            
            if len(poly) > 0:

                if len( poly[len(poly)-1] ) < 3:
                    param['optimized'] = 0
                   
                if len(poly) < 2:
                    param['optimized'] = 0                   

                poly.pop()
                param['poly'] = json.dumps( poly )
                spoly = param['poly']                   
                   
            else: 
                param['optimized'] = 0


        elif action == 'next line' :
            poly = json.loads( spoly )
            poly += [[[0, 0]]]
            param['poly'] = json.dumps( poly )
            spoly = param['poly']

        elif action == 'zoom_in':
            param['zoom'] += 1
            param['zoom'] = int(self.check_zoom( param['zoom'], param ))

        elif action == 'zoom_out':
            param['zoom'] -= 1
            param['zoom'] = int(self.check_zoom( param['zoom'], param ))
  
        elif action == 'clear':
            param['poly'] = json.dumps( [[]] )
            param['zoom'] =  self.get_zoom_default(param)
            param['scrollx'] = 0
            param['scrolly'] = 0

        return action




    ## .................
    @classmethod
    def check_scroll( cls, xcoor, ycoor, zoom, param ):
        """
        check if the scroll parameter is the the range allowed        
        """      
        img_width  = float( param['img_width']  )
        img_height = float( param['img_height'] )

        try:
            scrollx = float( xcoor )
            scrolly = float( ycoor )
            assert 0 <= scrollx < img_width * 2 ** zoom
            assert 0 <= scrolly < img_height * 2 ** zoom

        except Exception:
            scrollx = 0
            scrolly = 0

        return [scrollx, scrolly]



    ## .................

    @classmethod
    def check_poly( cls, spoly, x_value, y_value, param ):
        """
        get the polygon points from a string (json)
        """      
        img_width  = float( param['img_width']  )
        img_height = float( param['img_height'] )
        zoom       = float( param['zoom']       )

        poly = json.loads( spoly )

        xcoor = int( int( x_value ) / 2 ** zoom)
        ycoor = int( int( y_value ) / 2 ** zoom)

        assert 0 <= xcoor < img_width
        assert 0 <= ycoor < img_height
        
        n = len(poly)

        if n > 0:
            if poly[n-1] == [[0, 0]] :
                poly[n-1] = [[xcoor, ycoor]]
            else:
                poly[n-1] += [[xcoor, ycoor]]
        else:
            poly += [[[xcoor, ycoor]]]

        return json.dumps( poly )

    ## .................


    @classmethod
    def check_distorsion_center( cls, param):
        """
        get the zoom default value
        """

        viewport_width  = param['viewport_width']
        viewport_height = param['viewport_height']

        img_width  = param['img_width']
        img_height = param['img_height']

        zoom_default = math.floor(min(( \
              math.log(viewport_width)  - math.log(img_width))  / math.log(2), \
              (math.log(viewport_height) - math.log(img_height)) / math.log(2)))

        return zoom_default




    

    @cherrypy.expose
    @init_app
    def addpoint(self, **kwargs):
        """
        draw the polygon 
        """      
        
        pfile = self.old_work_dir + 'index.cfg'

        if os.path.isfile( pfile ) :
            self.cfg['param'] = cfg_open(pfile, 'rb')['param']


        if self.old_work_dir != self.work_dir:
            shutil.copy(self.old_work_dir + 'input_0.bmp', \
                        self.work_dir     + 'input_0.bmp')


        self.cfg['param']['zoom'] = int(self.check_zoom( kwargs['zoom'],      \
                                                         self.cfg['param'] ))

        self.cfg['param']['zoom_default'] = int(self.get_zoom_default(        \
                                                           self.cfg['param'] ))

        [ self.cfg['param']['scrollx'], self.cfg['param']['scrolly'] ] =      \
                     self.check_scroll( kwargs['scrollx'], kwargs['scrolly'], \
                     self.cfg['param']['zoom'], self.cfg['param'] )

    ## .................
        
        if 'x_center' in kwargs:
            self.cfg['param']['x_center'] = float( kwargs['x_center'] )

        xcoor = int( int( self.cfg['param']['x_center'] ) /  \
                     2 ** self.cfg['param']['zoom'])            
            
        if ( 0 <= xcoor <= float( self.cfg['param']['img_width']) ):
            self.cfg['param']['x_center'] = float( kwargs['x_center'] )
        else :
            self.cfg['param']['x_center'] = \
                                    float(self.cfg['param']['img_width']) / 2

        ### ......

        if 'y_center' in kwargs:
            self.cfg['param']['y_center'] = float( kwargs['y_center'] )

        ycoor = int( int( self.cfg['param']['y_center'] ) /  \
                     2 ** self.cfg['param']['zoom'])

        if ( 0 <= ycoor <= float( self.cfg['param']['img_height']) ):
            self.cfg['param']['y_center'] = float( kwargs['y_center'] )
        else :
            self.cfg['param']['y_center'] = \
                                    float(self.cfg['param']['img_height']) / 2

        ### ......

        if 'optimized' in kwargs:
            if kwargs['optimized'] == 'on':
                self.cfg['param']['optimized'] = 1
            else:
                self.cfg['param']['optimized'] = 0

        else: 
            if 'action' not in kwargs:
                self.cfg['param']['optimized'] = 0

    ## .................

       # Check action (VALUE)
        if 'action' in kwargs:
            self.cfg['param']['action'] = self.check_action( kwargs['action'], \
                                             kwargs['poly'], self.cfg['param'] )

        else :
            self.cfg['param']['poly'] = self.check_poly( kwargs['poly'], 
                                         kwargs['point.x'], kwargs['point.y'], \
                                         self.cfg['param'])

        self.cfg.save()        

        self.draw_poly( self.cfg['param'] )
        return self.tmpl_out('params.html')






    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None):
        """
        Configure the algo execution
        """

        if self.first_run:
            self.orig_work_dir = self.work_dir
            self.first_run = False
        
        self.old_work_dir = self.work_dir
        
        # Set undefined parameters to default values
        self.cfg['param'] = dict(self.default_param, **self.cfg['param'])

        img = image(self.work_dir + 'input_0.bmp')
        (xsize, ysize) = img.size       
       
        self.cfg['param']['img_width'] = xsize
        self.cfg['param']['img_height'] = ysize 
        
        self.cfg['param']['x_center'] = xsize/2.0
        self.cfg['param']['y_center'] = ysize/2.0 

        self.cfg['param']['zoom_default'] = int(self.get_zoom_default( \
                                                self.cfg['param'] ))

        if newrun:      
            self.clone_input()
            
            # Keep old parameters
            self.cfg['param'] = \
                      cfg_open(self.old_work_dir + 'index.cfg', 'rb')['param']


        self.cfg.save()

        self.draw_poly( self.cfg['param'] )
        return self.tmpl_out('params.html')






    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        Params handling and run redirection
        """
        self.input_points_file()

        ## .................        
        
        if 'x_center' in kwargs:
            self.cfg['param']['x_center'] = float( kwargs['x_center'] )

        xcoor = int( int( self.cfg['param']['x_center'] ) /  \
                     2 ** self.cfg['param']['zoom'])            
            
        if ( 0 <= xcoor <= float(self.cfg['param']['img_width']) ):
            self.cfg['param']['x_center'] = float( kwargs['x_center'] )
        else :
            self.cfg['param']['x_center'] = \
                                    float(self.cfg['param']['img_width']) / 2

        ### ......

        if 'y_center' in kwargs:
            self.cfg['param']['y_center'] = float( kwargs['y_center'] )

        ycoor = int( int( self.cfg['param']['y_center'] ) /  \
                     2 ** self.cfg['param']['zoom'])

        if ( 0 <= ycoor <= float(self.cfg['param']['img_height']) ):
            self.cfg['param']['y_center'] = float( kwargs['y_center'] )
        else :
            self.cfg['param']['y_center'] = \
                                    float(self.cfg['param']['img_height']) / 2

        ### ......

        if 'optimized' in kwargs:
            if kwargs['optimized'] == 'on':
                self.cfg['param']['optimized'] = 1
            else:
                self.cfg['param']['optimized'] = 0

        else: 
            if 'action' in kwargs and kwargs['action'] == 'Run' :
                self.cfg['param']['optimized'] = 0

        ## .................
        
        self.cfg.save()
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")





    @cherrypy.expose
    @init_app
    def run(self):
        """
        Algorithm execution
        """
        try:
            run_time = time.time()
            self.run_algo(stdout=open(self.work_dir + 'stdout.txt', 'w'))
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # Archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file('input_0.png', info='Input Image')
            ar.add_file('output_0.png', info='Output Image')
            ar.add_file('line_primitives.dat', info='Selected lines')
            ar.add_file('output_0.dat', info='Output data')
            ar.add_info({'x_center': self.cfg['param']['x_center']})
            ar.add_info({'y_center': self.cfg['param']['y_center']})
            ar.add_info({'center_optimization': \
                         self.cfg['param']['optimized']})
            ar.save()

        return self.tmpl_out("run.html")




    def run_algo(self, stdout=None):
        """
        The core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        timeout = False

        # Read data from configuration file
        pfile = self.work_dir + 'index.cfg'

        if os.path.isfile( pfile ) :
            self.cfg['param'] = cfg_open(pfile, 'rb')['param']
        else :
            self.cfg['param'] = dict(self.default_param, **self.cfg['param'])
        
                   
        lens_distortion = self.run_proc(['lens_distortion_estimation',        \
                                         'input_0.bmp',                       \
                                         'output_0.bmp',                      \
                                         'line_primitives.dat',               \
                                         'output_0.dat',                      \
                                         str(self.cfg['param']['x_center']),  \
                                         str(self.cfg['param']['y_center']),  \
                                         str(self.cfg['param']['optimized'])],\
                                          stdout=stdout, stderr=stdout )

        self.wait_proc( lens_distortion, timeout )

        # .............
        
        in1 = self.work_dir + 'output_0.bmp'
        out1 = self.work_dir + 'output_0.png'
        
        cmdrun = ['convert'] + [in1] + [out1]
        subprocess.Popen( cmdrun ).wait()        
        
        # .............
        
        self.cfg.save()
        return




    @cherrypy.expose
    @init_app
    def result(self, public=None):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        return self.tmpl_out('result.html',
            displaysize=image(self.work_dir + 'output_0.bmp').size,            
            stdout=open(self.work_dir + 'stdout.txt', 'r').read())
