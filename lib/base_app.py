"""
base IPOL demo web app
includes interaction and rendering
"""
# pylint: disable=C0103

# TODO add steps (cf amazon cart)

import shutil
from mako.lookup import TemplateLookup
import cherrypy
import os.path

from . import http
from . import config
from . import archive
from .empty_app import empty_app
from .misc import prod, init_app
from .image import thumbnail, image

class base_app(empty_app):
    """ base demo app class with a typical flow """
    # default class attributes
    # to be modified in subclasses
    title = "base demo"

    input_nb = 1 # number of input files
    input_max_pixels = 1024 * 1024 # max size of an input image
    input_max_weight = 5 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '1x8i' # input image expected data type
    input_ext = '.tiff' # input image expected extention (ie. file format)
    timeout = 60 # subprocess execution timeout
    is_test = True

    def __init__(self, base_dir):
        """
        app setup
        base_dir is supposed to be received from a subclass
        """
        # setup the parent class
        empty_app.__init__(self, base_dir)
        cherrypy.log("base_dir: %s" % self.base_dir,
                     context='SETUP/%s' % self.id, traceback=False)
        # local base_app templates folder
        tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'template')
        # first search in the subclass template dir
        self.tmpl_lookup = TemplateLookup( \
            directories=[self.base_dir + 'template', tmpl_dir],
            input_encoding='utf-8',
            output_encoding='utf-8', encoding_errors='replace')
 
    #
    # TEMPLATES HANDLER
    #

    def tmpl_out(self, tmpl_fname, **kwargs):
        """
        templating shortcut, populated with the default app attributes
        """
        # pass the app object
        kwargs['app'] = self
        # production flag
        kwargs['prod'] = (cherrypy.config['server.environment']
                          == 'production')

        tmpl = self.tmpl_lookup.get_template(tmpl_fname)
        return tmpl.render(**kwargs)

    #
    # INDEX
    #

    def index(self):
        """
        demo presentation and input menu
        """
        # read the input index as a dict
        inputd = config.file_dict(self.input_dir)
        tn_size = int(cherrypy.config.get('input.thumbnail.size', '128'))
        # TODO: build via list-comprehension
        for (input_id, input_info) in inputd.items():
            # convert the files to a list of file names
            # by splitting at blank characters
            # and generate thumbnails and thumbnail urls
            tn_fname = [thumbnail(self.input_dir + fname,
                                  (tn_size, tn_size))
                        for fname in input_info['files'].split()]
            inputd[input_id]['tn_url'] = [self.input_url
                                          + os.path.basename(fname)
                                          for fname in tn_fname]

	"""
        return self.tmpl_out("input.html",
                             tn_size=tn_size,
                             inputd=inputd)

	"""
	#Jose Luis changes
	#credits
	cr_size=24
        for (input_id, input_info) in inputd.items():
            # convert the files to a list of file names
            # by splitting at blank characters
            # and generate thumbnails and thumbnail urls
            cr_fname = [thumbnail(self.input_dir + fname,
                                  (cr_size, cr_size))
                        for fname in input_info['files'].split()]
            inputd[input_id]['cr_url'] = [self.input_url
                                          + os.path.basename(fname)
                                          for fname in cr_fname]
            inputd[input_id]['href_url'] = [self.input_url
                                          + os.path.basename(fname)
                        		for fname in input_info['files'].split()]

        return self.tmpl_out("input.html",
                             tn_size=tn_size,
			     cr_size=cr_size,
                             inputd=inputd)
	"""
	"""



    #
    # INPUT HANDLING TOOLS
    #

    def process_input(self):
        """
        pre-process the input data
        """
        msg = None
        for i in range(self.input_nb):
            # open the file as an image
            try:
                im = image(self.work_dir + 'input_%i' % i)
            except IOError:
                raise cherrypy.HTTPError(400, # Bad Request
                                         "Bad input file")
            # convert to the expected input format
            im.convert(self.input_dtype)
            # check max size
            if self.input_max_pixels \
                    and prod(im.size) > (self.input_max_pixels):
                im.resize(self.input_max_pixels)
                self.log("input resized")
                msg = """The image has been resized
                      for a reduced computation time."""
            # save a working copy
            im.save(self.work_dir + 'input_%i' % i + self.input_ext)
            # save a web viewable copy
            im.save(self.work_dir + 'input_%i.png' % i)
            # delete the original
            os.unlink(self.work_dir + 'input_%i' % i)
        return msg

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
        fnames = ['input_%i' % i + self.input_ext
                  for i in range(self.input_nb)]
        fnames += ['input_%i.png' % i
                   for i in range(self.input_nb)]
        for fname in fnames:
            shutil.copy(old_work_dir + fname,
                        self.work_dir + fname)
        # copy cfg
        self.cfg['meta'] = old_cfg_meta
        self.cfg.save()
        return

    #
    # INPUT STEP
    #

    def input_select(self, **kwargs):
        """
        use the selected available input images
        """
        self.new_key()
        self.init_cfg()
        # kwargs contains input_id.x and input_id.y
        input_id = kwargs.keys()[0].split('.')[0]
        assert input_id == kwargs.keys()[1].split('.')[0]
        # get the images
        input_dict = config.file_dict(self.input_dir)
        fnames = input_dict[input_id]['files'].split()
        for i in range(len(fnames)):
            shutil.copy(self.input_dir + fnames[i],
                        self.work_dir + 'input_%i' % i)
        msg = self.process_input()
        self.log("input selected : %s" % input_id)
        # '' is the empty string, evals to False
        self.cfg['meta']['original'] = ''
        self.cfg.save()
        # jump to the params page
        return self.params(msg=msg, key=self.key)

    def input_upload(self, **kwargs):
        """
        use the uploaded input images
        """
        self.new_key()
        self.init_cfg()
        for i in range(self.input_nb):
            file_up = kwargs['file_%i' % i]
            file_save = file(self.work_dir + 'input_%i' % i, 'wb')
            if '' == file_up.filename:
                # missing file
                raise cherrypy.HTTPError(400, # Bad Request
                                         "Missing input file")
            size = 0
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
        msg = self.process_input()
        self.log("input uploaded")
        self.cfg['meta']['original'] = True
        self.cfg.save()
        # jump to the params page
        return self.params(msg=msg, key=self.key)

    #
    # ERROR HANDLING
    #

    def error(self, errcode=None, errmsg=''):
        """
        signal an error
        """
        msgd = {'badparams' : 'Error: bad parameters. ',
                'timeout' : 'Error: execution timeout. '
                + 'The algorithm took more than %i seconds ' % self.timeout
                + 'and had to be interrupted. ',
                'returncode' : 'Error: execution failed. '}
        msg = msgd.get(errcode, 'Error: an unknown error occured. ') + errmsg

        return self.tmpl_out("error.html", msg=msg)

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
        return self.tmpl_out("params.html", msg=msg,
                             input = ['input_%i.png' % i
                                      for i in range(self.input_nb)])

    #
    # EXECUTION AND RESULTS
    #

    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        SHOULD be defined in the derived classes, to check the parameters
        """
        # pylint compliance (kwargs *is* used in derived classes)
        kwargs = kwargs
        # TODO check_params as a hook
        # use http meta refresh (display the page content meanwhile)
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html",
                             input=['input_%i.png' % i
                                    for i in range(self.input_nb)])

    @init_app
    def run(self, **kwargs):
        """
        algo execution and redirection to result
        SHOULD be defined in the derived classes, to check the parameters
        """
        # pylint compliance (kwargs *is* used in derived classes)
        kwargs = kwargs
        # run the algo
        # TODO ensure only running once
        self.run_algo({})
        # redirect to the result page
        # use http 303 for transparent non-permanent redirection
        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html")

    def run_algo(self, params):
        """
        the core algo runner
        * could also be called by a batch processor
        * MUST be defined by the derived classes
        """
        pass

    @init_app
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # TODO display the archive link with option to not be public
        return self.tmpl_out("result.html",
                             input=['input_%i.png' % i
                                    for i in range(self.input_nb)],
                             output=['output.png'])

    #
    # ARCHIVE
    #
    
    @cherrypy.expose
    def archive(self, offset=0):
        """
        lists the archive content
        """
        buckets = []
        for key in self.get_archive_key_by_date(offset=offset):
            ar = archive.bucket(self.archive_dir, key)
            files = []
            for fname in os.listdir(ar.path):
                if (not os.path.isfile(os.path.join(ar.path, fname))
                    or fname.startswith('.')):
                    continue
                if "index.cfg" == fname:
                    continue
                info = ar.cfg['fileinfo'].get(fname, '')
                files.append(archive.item(os.path.join(ar.path, fname),
                                          info=info))
            buckets += [{'url' : self.archive_url + archive.key2url(key),
                         'files' : files,
                         'meta' : ar.cfg['meta'],
                         'info' : ar.cfg['info']}]
        return self.tmpl_out("archive.html",
                             bucket_list=buckets)


