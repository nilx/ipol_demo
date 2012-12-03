"""
A Real Time Morphological Snakes Algorithm ipol demo web app
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
    """ A Real Time Morphological Snakes Algorithm app """

    title = 'A Real Time Morphological Snakes Algorithm'
    xlink_article = 'http://www.ipol.im/pub/art/2012/abmh-rtmsa/'
    
    old_work_dir = ''

    input_nb = 1
    input_max_pixels = 1048576          # max size (in pixels) input image
    input_max_weight = 3 * 1024 * 1024  # max size (in bytes) input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False
    
    first_run = True
    orig_work_dir = ''
           

    # Default parameters
    default_param = dict(
            {'sigma'                         : 8,
             'snake_structure'               : 1,
             'snake_balloon'                 : 0,
             'snake_balloon_diff_radius'     : 48,
             'snake_edge_detector_threshold' : 0.5,
             'snake_edge_balloon_threshold'  : 0.4,
             'iterations'                    : 100,             
#
             'viewport_width'                : 740,
             'viewport_height'               : 600,
             'img_width'                     : 512,
             'img_height'                    : 512,
#
             'zoom'                          : 0,
             'zoom_default'                  : 0,
             'scrollx'                       : 0,
             'scrolly'                       : 0,
             'poly'                          : json.dumps( [] ),
             'background'                    : '',
             'foreground'                    : '',
             'action'                        : '',
             'command_line'                  : ''
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
        tgz_url = 'http://www.ipol.im/pub/algo/' \
            + 'abmh_real_time_morphological_snakes_algorithm/' \
            + 'MorphologicalSnakes_20111228.zip'

        tgz_file = self.dl_dir + 'MorphologicalSnakes_20111228.zip'
        progs = ['morphological_snake']
        
        sub_dir = 'MorphologicalSnakes_20111228/source'
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
                    + " --makefile=Makefile", stdout=log_file)

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

        points = self.work_dir + "points.txt"

        ofile = file(points, "w")
        ofile.writelines("%i %i \n" % (x, y)  \
                       for (x, y) in json.loads( self.cfg['param']['poly'] ) )
        ofile.close()

        shutil.copy(points, self.work_dir + 'input_%i' % 0 + '.cn')


## .................................  ## .................................



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

        if len(poly) > 0 :

            ptargs = ['-stroke', '#00FF00', '-strokewidth', \
                      '1.5', '-fill', '#00FF00']

            ptargs += ['-draw', ' '.join(['circle %(x)i,%(y)i %(x)i,%(y_r)i'
                                       % {'x' : x * 2 ** zoom,
                                          'y' : y * 2 ** zoom,
                                          'y_r' : y * 2 ** zoom - ptrad}
                                          for (x, y) in poly])]
            ## ...........

            lnargs = ['-stroke', '#FF0000', '-fill', 'none']

            lnargs += ['-draw', ('polyline ' + ' '.join(['%(x)i,%(y)i '
                                                   % {'x' : x * 2 ** zoom,
                                                      'y' : y * 2 ** zoom}
                                                       for (x, y) in poly]))]
        
            if (2 < len(poly)):
                lnargs += ['-strokewidth', '.5', '-draw', 'line %i,%i %i,%i' \
                          % tuple([2 ** zoom * p for p in poly[-1] + poly[0]])]

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

            if len(poly) > 0:
                poly.pop()
                param['poly'] = json.dumps( poly )
                spoly = param['poly']

        elif action == 'zoom_in':
            param['zoom'] += 1
            param['zoom'] = int(self.check_zoom( param['zoom'], param ))

        elif action == 'zoom_out':
            param['zoom'] -= 1
            param['zoom'] = int(self.check_zoom( param['zoom'], param ))
  
        elif action == 'clear':
            param['poly'] = json.dumps( [] )
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
            print "\n\n check_scroll: Exception \n"

        return [scrollx, scrolly]


    ## .................

    @classmethod
    def check_structure( cls, value ):
        """
        get the structure value
        """      

        structure = int( value )
        return structure


    ## .................

    @classmethod
    def check_balloon( cls, value ):
        """
        get the balloon value
        """      

        balloon = int( value )
        return balloon


    ## .................

    @classmethod
    def check_gauss( cls, value ):
        """
        get the sigma value
        """      

        gauss = float( value )
        gauss = 8.

        if gauss < 0:
            gauss = 0.
        if gauss > 30:
            gauss = 30.

        return gauss


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

        poly += [[xcoor, ycoor]]

        return json.dumps( poly )

    ## .................






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
            shutil.copy(self.old_work_dir + 'input_0.png', \
                        self.work_dir     + 'input_0.png')


        self.cfg['param']['zoom'] = int(self.check_zoom( kwargs['zoom'],      \
                                                         self.cfg['param'] ))

        self.cfg['param']['zoom_default'] = int(self.get_zoom_default(        \
                                                           self.cfg['param'] ))

        [ self.cfg['param']['scrollx'], self.cfg['param']['scrolly'] ] =      \
                     self.check_scroll( kwargs['scrollx'], kwargs['scrolly'], \
                     self.cfg['param']['zoom'], self.cfg['param'] )


        if (0 <= float(self.cfg['param']['sigma']) <= 30):
            self.cfg['param']['sigma'] = float( kwargs['sigma'] )

        if int(kwargs['iterations']) > 0:
            self.cfg['param']['iterations'] = int( kwargs['iterations'] )
        else: 
            self.cfg['param']['iterations'] = (-1)*int( kwargs['iterations'] )

        self.cfg['param']['snake_structure'] = int( kwargs['structure'] )
        self.cfg['param']['snake_balloon'] = int( kwargs['balloon'] )


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

        if newrun:      

            self.clone_input()
            
            # Keep old parameters
            self.cfg['param'] = \
                      cfg_open(self.old_work_dir + 'index.cfg', 'rb')['param']
            


        img = image(self.work_dir + 'input_0.png')
        (xsize, ysize) = img.size       
       
        self.cfg['param']['img_width'] = xsize
        self.cfg['param']['img_height'] = ysize 
        
        self.cfg['param']['zoom_default'] = int(self.get_zoom_default( \
                                                self.cfg['param'] ))

        if msg == 'use the output points':
            shutil.copy(self.old_work_dir + 'output_0.cn', \
                        self.work_dir     + 'input_0.cn')

            lst = []
            
            ofile = open(self.work_dir + 'input_0.cn','r')

            line = ofile.readline()
            line = ofile.readline()
            
            ii = 0
 
            while line:
                if ii > -1:
                    vec = line.split(" ")
                    vec[1] = vec[1][0:len(vec[1])-1]

                    lst += [[int(vec[0]), self.cfg['param']['img_height'] \
                                        - int(vec[1])]]
                    ii = 0
                    
                ii += 1   
                line = ofile.readline()
 
 
            self.cfg['param']['poly'] = json.dumps( lst )


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

        # Validate sigma
        if not (0 <= float(self.cfg['param']['sigma']) <= 30):
            return self.error(errcode='badparams') 

        self.cfg['param']['snake_structure'] = int( kwargs['structure'] )
        self.cfg['param']['snake_balloon'] = int( kwargs['balloon'] )

        if int(kwargs['iterations']) > 0:
            self.cfg['param']['iterations'] = int( kwargs['iterations'] )
        else: 
            self.cfg['param']['iterations'] = (-1)*int( kwargs['iterations'] )

        self.cfg['param']['sigma'] = float( kwargs['sigma'] )

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
            ar.add_file('input_0.cn', info='Input contour')
            ar.add_file('output_0.cn', info='Output contour')
            ar.add_info({'sigma': self.cfg['param']['sigma']})
            ar.add_info({'snake_structure': \
                          self.cfg['param']['snake_structure']})
            ar.add_info({'snake_balloon': self.cfg['param']['snake_balloon']})
            ar.add_info({'snake_balloon_diff_radius': \
                          self.cfg['param']['snake_balloon_diff_radius']})
            ar.add_info({'snake_edge_detector_threshold': \
                          self.cfg['param']['snake_edge_detector_threshold']})
            ar.add_info({'snake_edge_balloon_threshold': \
                          self.cfg['param']['snake_edge_balloon_threshold']})
            ar.add_info({'iterations': self.cfg['param']['iterations']})

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
        
       
        animate_inc = 20
        niter = int( (self.cfg['param']['iterations']/animate_inc) ) + 1

        nn = 0
        oimg = ''

        for ii in range(0, niter) :
            
            nn = ii * animate_inc
            
            if nn < 100 :
                oimg = 'output_0' + str(nn) 
            else :
                oimg = 'output_' + str(nn)

            # Perform the morphological snake            
            morpho_snake = self.run_proc(['morphological_snake',  \
               '-I', 'input_0.png',                             \
               '-O', oimg +'_0.png',                            \
               '-C', 'input_0.cn',                              \
               '-F', 'output_0.cn',                             \
               '-S', str(self.cfg['param']['sigma']),           \
               '-T', str(self.cfg['param']['snake_structure']), \
               '-N', str(nn),                                   \
               '-B', str(self.cfg['param']['snake_balloon']),   \
               '-R', str(self.cfg['param']['snake_balloon_diff_radius']),  \
               '-P', str(self.cfg['param']['snake_edge_detector_threshold'])], \
                     stdout=stdout, stderr=stdout )


        self.wait_proc( morpho_snake, timeout )


        if self.cfg['param']['iterations'] < 100 :
            oimg = 'output_0' + str(self.cfg['param']['iterations']) 
        else :
            oimg = 'output_' + str(self.cfg['param']['iterations'])


        morpho_snake = self.run_proc(['morphological_snake',  \
             '-I', 'input_0.png',                             \
             '-O', oimg +'_0.png',                            \
             '-C', 'input_0.cn',                              \
             '-F', 'output_0.cn',                             \
             '-S', str(self.cfg['param']['sigma']),           \
             '-T', str(self.cfg['param']['snake_structure']), \
             '-N', str(self.cfg['param']['iterations']),      \
             '-B', str(self.cfg['param']['snake_balloon']),   \
             '-R', str(self.cfg['param']['snake_balloon_diff_radius']),  \
             '-P', str(self.cfg['param']['snake_edge_detector_threshold'])], \
                   stdout=stdout, stderr=stdout )

        self.wait_proc( morpho_snake, timeout )


        shutil.copy( self.work_dir + oimg +'_0.png', \
                     self.work_dir + 'output_0.png' )         

        cmdrun = ['convert', '-delay', '100', '-loop', '0', ' ', \
                  self.work_dir + 'output_*_0.png',              \
                  self.work_dir + 'animate_output.gif'] 
        
        subprocess.Popen( cmdrun ).wait()


        self.cfg['param']['command_line'] = 'morphological_snake ' +          \
             ' -I ' + ' input_0.png' + ' -O ' + ' output_0.png' +             \
             ' -C ' + 'input_0.cn' + ' -F ' + 'output_0.cn' +                 \
             ' -S ' + str(self.cfg['param']['sigma']) +                       \
             ' -T ' + str(self.cfg['param']['snake_structure']) +             \
             ' -N ' + str(self.cfg['param']['iterations']) +                  \
             ' -B ' + str(self.cfg['param']['snake_balloon']) +               \
             ' -R ' + str(self.cfg['param']['snake_balloon_diff_radius']) +   \
             ' -P ' + str(self.cfg['param']['snake_edge_detector_threshold'])


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
            displaysize=image(self.work_dir + 'output_0.png').size,
            stdout=open(self.work_dir + 'stdout.txt', 'r').read())
