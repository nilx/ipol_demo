"""
Stereo block matching with integral images 
"""
# pylint: disable-msg=R0904,C0103

from lib import base_app, build, http, config, thumbnail
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

########  WARNING OVERLOADING EMPYT_APP ######### 
########  WARNING OVERLOADING EMPYT_APP ######### 
########  WARNING OVERLOADING EMPYT_APP ######### 
import config_json
########  WARNING OVERLOADING EMPYT_APP ######### 
########  WARNING OVERLOADING EMPYT_APP ######### 
########  WARNING OVERLOADING EMPYT_APP ######### 

# Workflow
# 
# HTML                    Python
#
# input   ---------->     input_select
#                         input_upload
#                           |    |
# paramresult  <------------|    |
#   |                            |
#   --------------------> wait <-|
#                           |  
# wait    <-----------------+
#   |                       |
#   v                       v
# paramresult  <---------  run
#
#



class app(base_app):
    """ stereo block matching with integral images """

    title = 'Integral Images for Block Matching'

    input_nb = 2
    input_max_pixels = 2048* 2048       # max size (in pixels) input image
    input_max_weight = 3 * 2048 * 2048  # max size (in bytes) input file
    input_dtype = '3x8i'                # input image expected data type
    input_ext = '.png'                  # expected extension
    is_test = False    
    is_listed = True

    xlink_article = "http://www.ipol.im/pub/pre/57/"

    xlink_src = "http://www.ipol.im/pub/pre/57/intimagebm_1.tgz"
#    xlink_src_demo = "http://dev.ipol.im/~facciolo/tmp/demoUtils.tgz"
    xlink_input = "http://dev.ipol.im/~facciolo/tmp/intimagebm_1_inputs.tar.gz"

    # ONLY THESE INPUTS ARE ACCEPTED
    VALID_KEYS=[ 'left_image', 'right_image', 
                 'ground_truth', 'ground_truth_mask', 'ground_truth_occ',
                 'min_disparity', 'max_disparity', 'min_off_y', 'max_off_y',
                 # THESE ARE EXECUTION PARAMETERS
                 'block_match_method', 'filter_method', 
                 'windowsize', 'noise_sigma', 'action',
                 'run', 'subpixel', 'addednoisesigma'
                 ]

    # these are files 
    FILE_KEYS=[ 'left_image', 'right_image', 'ground_truth', 'ground_truth_mask', 'ground_truth_occ' ]
    

    # Default parameters
    default_param = dict(
          {  'windowsize': '9',
             'min_disparity': '-31',
             'max_disparity': '31',
             'min_off_y': '0',
             'max_off_y': '0',
             'addednoisesigma': '0',
             'image_width': '800',
             'image_height': '600',
             'subpixel' : '1',
             'maxerrdiff' : '4',    # display range
             'filter_method' : [],
             'block_match_method' : []
             }.items()
          )

    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 

    def init_cfg(self):
        """
        reinitialize the config dictionary between 2 page calls
        """
        # read the config dict
        self.cfg = config_json.cfg_open(self.work_dir)
        # default three sections
        self.cfg.setdefault('param', {})
        self.cfg.setdefault('info', {})
        self.cfg.setdefault('meta', {})

    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 
    ########  WARNING OVERLOADING EMPYT_APP ######### 


    def build_algo(self):
        """
        program build/update
        """
        ## store common file path in variables
        tgz_file = self.dl_dir + "algo.tgz"
        prog_file = self.bin_dir + "simplestereo"
        progBM_file = self.bin_dir + "simplebm"
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
            build.run("cd %s; cmake ." % (self.src_dir + "intimagebm_1" ),
                                  stdout=log_file)
            build.run("make -C %s" % (self.src_dir + "intimagebm_1" ),
                                  stdout=log_file)

            # Create bin dir (delete the previous one if exists)
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)

            # save into bin dir
            #if os.path.isdir(self.bin_dir):
            #        shutil.rmtree(self.bin_dir)
            #try:
            shutil.copy(self.src_dir +
                    os.path.join("intimagebm_1",
                        "simplestereo"), prog_file)
            shutil.copy(self.src_dir +
                    os.path.join("intimagebm_1",
                        "simplebm"), progBM_file)
            #except:
            #   print("some error occurred copying files")

            # cleanup the source dir
            shutil.rmtree(self.src_dir)

            # link all the scripts to the bin dir
            import glob
            for file in glob.glob( os.path.join( self.base_dir, 'scripts/*')):
                os.symlink(file, os.path.join( self.bin_dir , os.path.basename(file)))
        return

    def build_demoUtils(self):
        """
        built the demo auxiliary programs (stored with the demo)
        """
        ## store common file path in variables
        tgz_file = self.base_dir + "support/demoUtils.tar.gz"
        prog_file = self.bin_dir + "plambda"
        log_file = self.base_dir + "build_utils.log"
        ## test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("no rebuild needed",
                      context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("cd %s; cmake ." %
                         (self.src_dir +"demoUtils"),
                            stdout=log_file)
            build.run("make -C %s" %
                         (self.src_dir +"demoUtils"),
                            stdout=log_file)
            # save into bin dir
            #try:
            import glob
            for f in glob.glob(os.path.join(self.src_dir,
                            "demoUtils", "bin", "*")):
                shutil.copy(f, self.bin_dir)
            #except:
            #   print("some error occurred copying files")
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    def grab_input(self):
       """
       download the input images from "xlink_input"
       """
       tgz_file = self.dl_dir + "input.tar.gz"
       input_cfg = self.input_dir + "input.cfg"
       ## get the latest source archive
       build.download(app.xlink_input, tgz_file)
       ## test if the dest file is missing, or too old
       if (os.path.isfile(input_cfg) 
             and ctime(tgz_file) < ctime(input_cfg)):
          cherrypy.log("no rebuild needed",
          context='BUILD', traceback=False)
       else:
          # Create bin dir (delete the previous one if exists)
          if os.path.isdir(self.input_dir):
              shutil.rmtree(self.input_dir)
          os.mkdir(self.input_dir)
          # extract the archive
          build.extract(tgz_file, self.input_dir)
          shutil.copytree(self.base_dir+'/support/HELP', os.path.join( self.input_dir, 'HELP'))

       return

    def build(self):
        self.build_algo()
        self.build_demoUtils()
        self.grab_input()
#        return




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
        # Generate a new timestamp
        self.timestamp = int(100*time.time())        


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
        tn_size = int(cherrypy.config.get('input.thumbnail.size', '192'))
        # TODO: build via list-comprehension
        for (input_id, input_info) in inputd.items():
            # convert the files to a list of file names
            # by splitting at blank characters
            # and generate thumbnails and thumbnail urls
            fname = input_info['files'].split()
#           GENERATE THUMBNAIL EVEN FOR FILES IN SUBDIRECTORIES OF INPUT
            inputd[input_id]['tn_url'] = [self.input_url +'/'+ os.path.dirname(f) + '/' +
                        os.path.basename(thumbnail(self.input_dir + f, (tn_size, tn_size)))
                        for f in fname]
            inputd[input_id]['url'] = [self.input_url + os.path.basename(f)
                                       for f in fname]


        return self.tmpl_out("input.html",
                             inputd=inputd)


############ INPUT HANDLING #####################
# These functions provide the some alternative and flexible ways to 
# load information into an application. 
# The idea is simple being able to load a set of parameters and files
# in several ways to facilitate the interaction with the application.
#
# We propose two interaction modalities:
# - load a pre-configured (params.cfg) experiment from an input directory
# - upload the parameters and the files from an html form using HTTP POST/GET
# - load all the parameters from an url encoded GET (experiment in a link)
#
# Whishlist: * zip files
#            * file sets 
#            * rename the uploaded/downloaded/copied files to the keyname (keep extension)
#
#
# The names of the parameters or files must be known in advance:
# the list: VALID_KEYS, is a list of accepted keys to be stored in the dictionary self.cfg['params']
# the list: FILE_KEYS, contains the subset of VALID_KEYS which corresponds to paths to local files 
#           containing the uploaded files. 
#           When processing an html form, these fileds correspond to POSTed files
#
# For each file there are always two keys in the dictionary:
# file_a     : contains a path to the file (relative or absolute)
# file_a_url : contains the url of the file (absolute)
# This allows to handle uploaded files and urls corresponding to those files.
# The path always has higher precedence than the url, 
# this means that the url is used only if the first is not specified.
#
# default_param : is a dictionary containing default values for the dictionary  
#
#

# copy_cfg_from_path(self, cfgfile, destdir)
#    copies params.cfg from the url cfgfile to destdir/dl/params.cfg 
#    and loads the dictionary self.cfg['params']
#    The files specified in FILE_KEYS are also copyed to destdir/dl, 
#    and the corresponding keys are updated 


# load_cfg_from_kwargs(self, kwargs, destdir)
#    loads the dictionary self.cfg['params'] with data from kwargs (obtained 
#    from an http post/get). Only the VALID_KEYS are accepted, 
#    and if the key contains a file its content is saved in the destdir/dl directory.
#    TODO: A file params.cfg is also stored in destdir/dl




    def copy_cfg_from_path(self, cfgfile, destdir):
        """
        Read the configuration from a local file, 
        the files are assumed to be in the same subdirectory as the cfg file.
        The configuration file can contain both references to local files, 
        and references to remote URL's.
        The local files are copied to the /dl directory
        """
        import os

        # SOURCE DIR
        srcdir = os.path.dirname(cfgfile)

        # create download directory if does not exist
        dl_dir = os.path.join(destdir,'dl')
        if not os.path.exists(dl_dir):
           os.mkdir(dl_dir)

        # DEFAULT PARAM
        self.cfg['param'] = self.default_param.copy()

        # LOAD param.cfg
        # TODO : must be done with eval , MAYBE SOME OTHER SOLUTION?
        f = file(cfgfile); 
        params = eval(f.read()); 
        f.close()
        shutil.copy(cfgfile, dl_dir)

        # Load self.cfg with non-null params
        for key in self.VALID_KEYS:
           if key in params.keys():
              self.cfg['param'][key] = params[key];
           else:
              if key not in self.cfg['param'].keys():
                 self.cfg['param'][key]='' 

        # COPY the files
        for key in self.FILE_KEYS:
            if key in params.keys():
               if params[key] != '':
                  oname = params[key]
                  dname = key + os.path.splitext(oname)[1]
                  shutil.copy(os.path.join(srcdir, oname), os.path.join(dl_dir, dname))
                  self.cfg['param'][key] = os.path.join('dl', dname)

        return



    def load_cfg_from_kwargs(self, kwargs, destdir):
        """
        load configuration and files from post/get http
        imports the cfg, and generates the files
        """
        import os

        # create download directory if does not exist
        dl_dir = os.path.join(destdir,'dl')
        if not os.path.exists(dl_dir):
           os.mkdir(dl_dir)

        # DEFAULT PARAM
        self.cfg['param'] = self.default_param.copy()

        size = 0

        # DEBUG
        print "Got " +  str(kwargs.keys())

        # TODO: DESCRIBE THE FOLLOWING PROCESS 
        for key in self.VALID_KEYS:
           if key in kwargs.keys():

              # IN CASE IT IS A STRING
              if (type(kwargs[key]) == str ): 
                 self.cfg['param'][key] = kwargs[key];

              # IN CASE IT IS A FILE
              else:
                 file_up = kwargs[key]

#                 if '' == file_up.filename:
#                    # missing file
#                    raise cherrypy.HTTPError(400, # Bad Request
#                                         "Missing input file")
   
                 if file_up.filename != '':
                    oname = file_up.filename 
                    dname = key + os.path.splitext(oname)[1]
                    self.cfg['param'][key] = os.path.join('dl',dname);
                    file_save = file(self.work_dir + self.cfg['param'][key], 'wb')
                    while True:
                       # TODO larger data size
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
                 else:
                    self.cfg['param'][key] = ''
           else:
              if key not in self.cfg['param'].keys():
                 self.cfg['param'][key]='' 
        return size







######### END INPUT HANDLING #####################
###############################################################################



    @cherrypy.expose
    @init_app
    def input_from_cfg(self, input_cfg_path):
        """
        input_cfg_path is a GET parameter, it contains the 
        url of rhe cfg file to be read

        After this method has run, the images have been:
        downloaded, converted and renamed to standard names
        IF the ground truth is provided, then the mask images
        are also generated
        The format for the images is PNG, except for the ground truth, which is encoded as TIFF
        A PNG thumbnail of the ground truth is also generated
        """
    
        from lib import config
    
    
        self.new_key()
        self.init_cfg()
    
        # it should be a relative path
        cfg_path_or_url = os.path.join(self.base_dir,'input',input_cfg_path , 'param.cfg')
        self.copy_cfg_from_path( cfg_path_or_url,  self.work_dir)
    
        # process the input files
        msg = self.process_input_files()
    
    
        self.cfg['meta']['original'] = False
        self.cfg['meta']['input_id'] = 'unknown'
        self.cfg.save()
        # jump to the params page
        return self.wait(msg=msg, key=self.key)

    

    #
    # PARAMETER HANDLING
    #

    @init_app
    def params(self, newrun=False, msg=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        return self.tmpl_out("paramresult.html", msg=msg,
                             input = ['input_%i.png' % i
                                      for i in range(self.input_nb)])


    @cherrypy.expose
    @init_app
    def input_select(self, **kwargs):
        """
        After this method has run, the images have been:
        downloaded, converted and renamed to standard names
        IF the ground truth is provided, then the mask images
        are also generated
        The format for the images is PNG, except for the ground truth, which is encoded as TIFF
        A PNG thumbnail of the ground truth is also generated
        """
    
        from lib import config
    
        # get parameters for the preconfigured experiments
        # kwargs contains input_id.x and input_id.y
        # The html form uses the input identifiers as names of the field
        input_id = kwargs.keys()[0].split('.')[0]
        #assert input_id == kwargs.keys()[1].split('.')[0]
    
        # load the input.cfg either from a local path or from an url
        input_cfg_path = config.file_dict(self.input_dir)[input_id]['path']
    
#        self.new_key()
        self.init_cfg()
    
        # it should be a relative path
        cfg_path_or_url = os.path.join(self.base_dir,'input',input_cfg_path , 'param.cfg')
        self.copy_cfg_from_path( cfg_path_or_url,  self.work_dir)
    
        # process the input files
        msg = self.process_input_files()
    
    
        self.log("input selected : %s" % input_id)
        self.cfg['meta']['input_id'] = input_id
        self.cfg['meta']['original'] = False
        self.cfg.save()
        # jump to the params page
        return self.params(msg=msg, key=self.key)




    @cherrypy.expose
    @init_app
    def input_upload(self, **kwargs):
        """
        After this method has run, the images have been:
        downloaded, converted and renamed to standard names
        IF the ground truth is provided, then the mask images
        are also generated
        The format for the images is PNG, except for the ground truth, which is encoded as TIFF
        A PNG thumbnail of the ground truth is also generated
        """

#        self.new_key()
        self.init_cfg()
        size = 0

        # read the parameters from kwargs, also the uploaded files
        size += self.load_cfg_from_kwargs(kwargs, self.work_dir)

        # process the input files: 
        msg = self.process_input_files()

        # TODO : uncompress zip files, 

        self.log("input uploaded")
        self.cfg['meta']['input_id'] = 'unknown'
        self.cfg['meta']['original'] = True
        self.cfg.save()


        if( self.cfg['param']['run'] ):
           return self.wait(msg=msg, key=self.key)


        # jump to the params page
        return self.params(msg=msg, key=self.key)





    def process_input_files(self):
        """
        PROCESS THE INPUT DATA
         * convert the files to TIFF and generate PNG previews, save with uniform names
         * apply data scaling to the groud truth 
         * update the names in the configuration file
         * generate thumbnail for the ground truth
        """
        msg = None
        import Image


        # CONVERT FORMAT OF THE INPUT FILES
        for file in self.FILE_KEYS:
           localname = self.cfg['param'][file]

           print file

           try:
              print localname
              if localname != '':
                 # Convert and uniformize names
#                 print os.path.join(self.work_dir, localname)
                 if file == 'ground_truth':
                    mindisp = float(self.cfg['param']['min_disparity'])
                    maxdisp = float(self.cfg['param']['max_disparity'])

                    # convert the original image and apply the stretching 
                    #tmp = self.run_proc(['convert.sh', localname , file+'.tif'])
                    tmp = self.run_proc(['axpb.sh',localname, file+'.tif', '1', '0'])
                    self.wait_proc(tmp)

                    # then remove the original file
                    os.unlink(os.path.join(self.work_dir, localname))

                    # generate the preview with a scale
                    tmp = self.run_proc(['genpreview_stretch.sh', file+'.tif', file+'.png', str(mindisp), str(maxdisp)])
                    self.wait_proc(tmp)

                    # update the configuration
                    self.cfg['param'][file]=file+'.tif'
                 else:
                    # read and remove the original file
                    tmp = self.run_proc(['convert.sh', localname , file+'.tif'])
                    self.wait_proc(tmp)
                    os.unlink(os.path.join(self.work_dir, localname))

                    # generate the preview
                    tmp = self.run_proc(['genpreview.sh', file+'.tif', file+'.png'])
                    self.wait_proc(tmp)

#                    im=Image.open(os.path.join(self.work_dir , localname))

                    # update the configuration
                    self.cfg['param'][file]=file+'.tif'


           except NameError:
              raise cherrypy.HTTPError(400, # Bad Request
                                      "Bad input file (not found)")
           except IOError:
              raise cherrypy.HTTPError(400, # Bad Request
                                      "Bad input file (not recognized)")


        # CHECK IF THERE ARE TWO IMAGES
        if ( self.cfg['param']['left_image'] == '' or self.cfg['param']['right_image'] == '' ):
            raise cherrypy.HTTPError(400, # Bad Request
                  "Stereoscope (noun): a device by which TWO photographs " + 
                  "of the same object taken at slightly different angles " + 
                  "are viewed together, creating an impression of depth and solidity." )

        # determine the image height and width
        im = Image.open(self.work_dir+'left_image.png')
        self.cfg['param']['image_width']  = im.size[0]
        self.cfg['param']['image_height'] = im.size[1]


        # GENERATE DISPARITY THUMBNAIL IF THE DISPARITY IS PROVIDED
        if self.cfg['param']['ground_truth'] != '':
#            # generate thumbnail (already done!)

            # CHECK IF THERE IS A MASK otherwise generate one
            if self.cfg['param']['ground_truth_mask'] == '':
               imw = self.cfg['param']['image_width']
               imh = self.cfg['param']['image_height']
               # generate an empty image and save it
               Image.new('I',(imw, imh), color=255).save(os.path.join(self.work_dir,'ground_truth_mask.png'))
               # update config
               self.cfg['param']['ground_truth_mask'] = 'ground_truth_mask.png'


        return msg




    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
       

        # DEFAULT PARAM VALUES FOR THE PARAMETERS THAT ARE NOT IN KWARGS
        for prp in self.default_param.keys():
           if( prp not in kwargs.keys() ):
                 self.cfg['param'][prp] = self.default_param[prp]

        # PROCESS ALL THE INPUTS
        for prp in kwargs.keys():
           if( prp in self.VALID_KEYS ):
              self.cfg['param'][prp] = kwargs[prp];

        #print self.cfg['param']

        # TODO: NOT VIRIFIED YET THE SIZE OF THE IMAGES SO JUST TAKE ONE OF THEM
        # THIS SHOULD BE DONE ONLY ONCE
        import Image
        im = Image.open(self.work_dir+'left_image.png')
        self.cfg['param']['image_width']  = im.size[0]
        self.cfg['param']['image_height'] = im.size[1]

        self.cfg.save()   


        ## The refresh (and the call to run) will only occur after all the images are loaded
        ## To speed-up the execution it is better not to show the images or to call redir
        ## which will not show the wait page at all..
        #http.redir_303(self.base_url + 'run?key=%s' % self.key)
        http.refresh(self.base_url + 'run?key=%s' % self.key)            
        return self.tmpl_out("wait.html")



    def make_archive(self):
        """
        create an archive bucket HACK!
        This overloaded verion of the empty_app function
        first deletes the entry and its directory so that the 
        new one is correcly stored.
        """
        # First delete the key from the archive if it exist
        from lib import archive
        archive.index_delete(self.archive_index, self.key)
        import shutil,os
        entrydir = self.archive_dir + archive.key2url(self.key)
        if os.path.isdir(entrydir):
           print "DELETING ARCHIVE ENTRY %s"%self.key
           shutil.rmtree(entrydir)

        # Then insert the new data
        ar = archive.bucket(path=self.archive_dir,
                            cwd=self.work_dir,
                            key=self.key)
        ar.cfg['meta']['public'] = self.cfg['meta']['public']

        def hook_index():
            return archive.index_add(self.archive_index,
                                     bucket=ar,
                                     path=self.archive_dir)
        ar.hook['post-save'] = hook_index
        return ar


    def dump_shell_params(self, outfile):
        """
        write the dict into a config file
        """
        prm = ["addednoisesigma", "image_width", "windowsize", "max_disparity", 
              "ground_truth_occ", "left_image", "filter_method", "max_off_y", 
              "min_off_y", "min_disparity", "ground_truth_mask", "subpixel", 
              "ground_truth", "right_image", "maxerrdiff", "prevaddednoisesigma", 
              "block_match_method", "noise_sigma"]

        fd = open(outfile, 'wb')
        fd.write('input_id="%s"\n' % self.cfg['meta']['input_id'])

        for nm in prm:
           fd.write('%s="%s"\n'%(nm,self.cfg['param'][nm]))
        fd.close()



    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # read the parameters

        algolist     = self.cfg['param']['block_match_method']
        filterlist   = self.cfg['param']['filter_method']
        if type(algolist) != list:
           algolist = [ algolist ]
        if type(filterlist) != list:
           filterlist = [ filterlist ]


        ## PREPROCESS INPUT (ADDING NOISE), only if something has changed
        # detect differences WRT the previous run
        conf = self.cfg['param']
        if( 'prevaddednoisesigma' not in conf ) :
           conf['prevaddednoisesigma'] = -1 # invalid
        if( conf['prevaddednoisesigma'] != conf['addednoisesigma'] ):
           # generate noisy images for the experiment and convert to mono if necessary
           # the images are stored in left_imagen.{tif,png} right_imagen.{tif,png}
           # the PNG files are the previews of the noisy images 
           self.dump_shell_params(self.work_dir + '/configSHELL.cfg');

           p1 = self.run_proc(['runPREPROCESS.sh'])
           self.wait_proc(p1, timeout=self.timeout)




           ## then update the previous parameter
           self.cfg['param']['prevaddednoisesigma'] =  self.cfg['param']['addednoisesigma']



        # run the algorithm once for each instance
        try:
            self.run_algo(algolist, filterlist)
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')



        ## archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("left_image.tif", info="")
            ar.add_file("right_image.tif", info="")
            ar.add_file("left_imagen.png", info="")
            ar.add_file("right_imagen.png", info="")
            if self.cfg['param']['ground_truth'] :
               ar.add_file("ground_truth.tif",info="")
               ar.add_file("ground_truth_mask.png",info="")

            for method in algolist:
               ar.add_file("output_" + method + ".png", info="")
            ar.add_info({"block_match_method": self.cfg['param']['block_match_method'], "window": self.cfg['param']['windowsize'],  "addednoisesigma": self.cfg['param']['addednoisesigma']})
            ar.save()


        # FUCK!
        self.cfg.save()   


        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html")



    def run_algo(self,algolist,filterlist):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """





        # STEREO
        if(float(self.cfg['param']['min_off_y']) == float(self.cfg['param']['max_off_y']) == 0):

           self.cfg['param']['isubpixel'] = 1./float(self.cfg['param']['subpixel'])
           self.dump_shell_params(self.work_dir + '/configSHELL.cfg');
   
           p={}
           for a in algolist:
               print("starting algo %s" % a)
               p[a] = self.run_proc(['/bin/bash', 'run.sh', a])
               self.wait_proc(p[a], timeout=self.timeout)

        # OPTICAL FLOW
        else:

           # NO SUBPIXEL IF IT IMPLIES AN EXCESSIVE WORK
           d=self.cfg['param']
           estimated_cost = float(d['subpixel'])*float(d['subpixel'])*(float(d['max_off_y'])-
                 float(d['min_off_y']))*(float(d['max_disparity'])- float(d['min_disparity']))
           if estimated_cost > 6400:
               self.cfg['param']['subpixel'] = '1';
               self.cfg['param']['isubpixel'] = '0';
           # NO GROUND TRUTH
           self.cfg['param']['ground_truth'] = '';
           self.dump_shell_params(self.work_dir + '/configSHELL.cfg');
   
           p={}
           for a in algolist:
               print("starting algo %s" % a)
               p[a] = self.run_proc(['/bin/bash', 'runOF.sh', a])
               self.wait_proc(p[a], timeout=self.timeout)


        # GENERATE A ZIP (do not wait for it)
        p = self.run_proc(['/bin/bash', 'zipresults.sh', 'results.zip'])
#        self.wait_proc(p, timeout=self.timeout)
        return



    @cherrypy.expose
    @init_app
    def result(self, public=None):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        self.cfg['param']['run']=1;

        return self.tmpl_out('paramresult.html' )
