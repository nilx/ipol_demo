"""
base IPOL demo web app
"""
# pylint: disable=C0103

# TODO add steps (cf amazon cart)

import shutil
from mako.lookup import TemplateLookup
import cherrypy
import os.path

from .empty_app import empty_app
from .misc import index_dict, prod, get_check_key, http_redirect_303
from .image import thumbnail, image

class base_app(empty_app):
    """ base demo app class with a typical flow """

    # default class attributes
    # to be modified in subclasses
    title = "base demo"
    description = "This demo contains all the generic actions," \
        + "none of which should be exposed."

    input_nb = 1 # number of input files
    input_max_pixels = 1024 * 1024 # max size of an input image
    input_max_weight = 5 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '1x8i' # input image expected data type
    input_ext = '.tiff' # input image expected extention (ie. file format)
    timeout = 60 # subprocess execution timeout
    is_test = True
    allow_upload = True

    def __init__(self, base_dir):
        """
        app setup
        base_dir is supposed to be received from a subclass
        """
        # setup the parent class
        empty_app.__init__(self, base_dir)
        cherrypy.log("new demo",
                     context='SETUP/%s' % self.id, traceback=False)
        cherrypy.log("base_dir: %s" % self.base_dir,
                     context='SETUP/%s' % self.id, traceback=False)
        # local base_app templates folder
        tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'template')
        # first search in the subclass template dir
        self.tmpl_lookup = TemplateLookup( \
            directories=[os.path.join(self.base_dir,'template'), tmpl_dir],
            input_encoding='utf-8',
            output_encoding='utf-8', encoding_errors='replace')
        # [TEST] flag
        if self.is_test:
            self.title = '[TEST] ' + self.title

        # TODO early attributes validation

    #
    # TEMPLATES HANDLER
    #

    def tmpl_out(self, tmpl_fname, **kwargs):
        """
        templating shortcut, populated with the default app attributes
        """
        # app attributes dict
        attrd = dict([(attr, getattr(self, attr, ''))
                      for attr in ['id',
                                   'key',
                                   'title',
                                   'description']])
        kwargs.update(attrd)

        # create urld if it doesn't exist
        kwargs.setdefault('urld', {})
        # add urld items
        kwargs['urld'].update({'start' : self.url('index'),
                               'xlink_algo' : self.url('algo'),
                               'xlink_demo' : self.url('demo'),
                               'xlink_archive' : self.url('archive'),
                               'xlink_forum' : self.url('forum')})
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
        inputd = index_dict(self.path('input'))
        for key in inputd.keys():
            # convert the files to a list of file names
            # by splitting at blank characters
            inputd[key]['files'] = inputd[key]['files'].split()
            # generate thumbnails and thumbnail urls
            tn_fname = [thumbnail(self.path('input', fname))
                        for fname in inputd[key]['files']]
            inputd[key]['tn_url'] = [self.url('input',
                                              os.path.basename(fname))
                                     for fname in tn_fname]

        # urls dict
        urld = {'select_form' : self.url('input_select'),
                'upload_form' : self.url('input_upload')}
        return self.tmpl_out("input.html", urld=urld,
                             inputd=inputd,
                             input_nb=self.input_nb,
                             allow_upload=self.allow_upload)

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
                im = image(self.path('tmp', 'input_%i' % i))
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
            im.save(self.path('tmp', 'input_%i' % i + self.input_ext))
            # save a web viewable copy
            im.save(self.path('tmp', 'input_%i.png' % i))
            # delete the original
            os.unlink(self.path('tmp', 'input_%i' % i))
        return msg

    def clone_input(self):
        """
        clone the input for a re-run of the algo
        """
        # get a new key
        oldkey = self.key
        oldpath = self.path('tmp')
        self.new_key()
        # copy the input files
        fnames = ['input_%i' % i + self.input_ext
                  for i in range(self.input_nb)]
        fnames += ['input_%i.png' % i
                   for i in range(self.input_nb)]
        for fname in fnames:
            shutil.copy(os.path.join(oldpath, fname),
                        os.path.join(self.path('tmp'), fname))
        self.log("input cloned from %s" % oldkey)
        return

    #
    # INPUT STEP
    #

    def input_select(self, **kwargs):
        """
        use the selected available input images
        """
        self.new_key()
        # kwargs contains input_id.x and input_id.y
        input_id = kwargs.keys()[0].split('.')[0]
        assert input_id == kwargs.keys()[1].split('.')[0]
        # get the images
        input_dict = index_dict(self.path('input'))
        fnames = input_dict[input_id]['files'].split()
        for i in range(len(fnames)):
            shutil.copy(self.path('input', fnames[i]),
                        self.path('tmp', 'input_%i' % i))
        msg = self.process_input()
        self.log("input selected : %s" % input_id)
        # jump to the params page
        return self.params(msg=msg)

    def input_upload(self, **kwargs):
        """
        use the uploaded input images
        """
        self.new_key()
        for i in range(self.input_nb):
            file_up = kwargs['file_%i' % i]
            file_save = file(self.path('tmp', 'input_%i' % i), 'wb')
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
        # jump to the params page
        return self.params(msg=msg)

    #
    # ERROR HANDLING
    #

    def error(self, errcode=None, errmsg=''):
        """
        signal an error
        """
        return self.tmpl_out("error.html", errcode=errcode, errmsg=errmsg)

    #
    # PARAMETER HANDLING
    #

    @get_check_key
    def params(self, newrun=False, msg=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        urld = {'next_step' : self.url('run'),
                'input' : [self.url('tmp', 'input_%i.png' % i)
                           for i in range(self.input_nb)]}
        return self.tmpl_out("params.html", urld=urld, msg=msg)

    #
    # EXECUTION AND RESULTS
    #

    @get_check_key
    def run(self, **kwargs):
        """
        params handling and run redirection
        SHOULD be defined in the derived classes, to check the parameters
        """
        # simply avoid pylint warnmings
        # kwargs *is* used in derived classes
        kwargs = kwargs
        # redirect to the result page
        # TODO check_params as another function
        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'input' : [self.url('tmp', 'input_%i.png' % i)
                           for i in range(self.input_nb)]}
        return self.tmpl_out("run.html", urld=urld)

    def run_algo(self, params):
        """
        the core algo runner
        * could also be called by a batch processor
        * MUST be defined by the derived classes
        """
        pass

    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # TODO ensure only running once
        # TODO save each result in a new archive
        # TODO give the archive link
        # TODO give the option to not be public
        #        (and remember it from a cookie)
        # TODO read the kwargs from a file, and pass to run_algo
        # TODO pass these parameters to the template
        self.run_algo({})
        self.log("input processed")
        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_%i.png' % i)
                           for i in range(self.input_nb)],
                'output' : [self.url('tmp', 'output.png')]}
        return self.tmpl_out("result.html", urld=urld)
