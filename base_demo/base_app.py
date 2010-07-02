"""
generic ipol demo web app
"""
# TODO : add steps (cf amazon cart)

import cherrypy
import os, shutil

from mako.lookup import TemplateLookup

from base_demo.empty_app import empty_app, get_check_key
#TODO : move lib up
from base_demo.lib import index_dict, tn_image, image, prod

class base_app(empty_app):
    """ base demo app class with a typical flow """

    # default class attributes
    # to be modified in subclasses
    title = "base demo"
    description = "This demo contains all the generic actions," \
        + "none of which should be exposed."

    input_nb = 1 # number of input files
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_pixels_tolerance = 1.1 # tolerance rate (reduce aliasing)
    input_max_weight = 5 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '1x8i' # input image expected data type
    input_ext = '.tiff' # input image expected extention (ie. file format)
    output_ext = '.tiff' # output image extention (ie. file format)
    display_ext = '.jpeg' # html embedded displayed image extention

    def __init__(self, base_dir):
        """
        app setup
        base_dir is supposed to be received from a subclass
        """
        # setup the parent class
        empty_app.__init__(self, base_dir)
        # local base_app templates folder
        tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'tmpl')
        # first search in the subclass tmpl dir
        self.tmpl_lookup = TemplateLookup( \
            directories=[os.path.join(self.base_dir,'tmpl'), tmpl_dir])
        # TODO : early attributes validation

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
                                   'input_nb',
                                   'title',
                                   'description']])
        kwargs.update(attrd)
        # crosslink urls
        kwargs['crosslink'] = dict([(link, self.url(link))
                                     for link in ['demo', 'algo',
                                                  'archive', 'forum']])
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
            tn_fname = [tn_image(self.path('input', fname)).fname
                        for fname in inputd[key]['files']]
            inputd[key]['tn_url'] = [self.url('input', fname)
                                     for fname in tn_fname]

        # urls dict
        urld = {'select_form' : self.url('input_select'),
                'upload_form' : self.url('input_upload')}
        return self.tmpl_out("index.html", urld=urld,
                              inputd=inputd)

    #
    # INPUT HANDLING TOOLS
    #

    def process_input(self):
        """
        pre-process the input data
        """
        input_url = []
        # TODO : check the data type
        for i in range(self.input_nb):
            # open the file as an image
            im = image(self.path('tmp', 'input_%i' % i))
            # convert to the expected input format
            im.convert(self.input_dtype)
            # check max size
            if prod(im.size) > (self.input_max_pixels
                                * self.input_max_pixels_tolerance):
                im.resize(self.input_max_pixels, mode="pixels")
                self.log("input resized")
            # save a working copy
            im.save(self.path('tmp', 'input_%i' % i + self.input_ext))
            # save a web viewable copy
            im.save(self.path('tmp', 'input_%i' % i + self.display_ext))
            # store the viewable url
            input_url += [self.url('tmp', 'input_%i' % i + self.display_ext)]
        return input_url

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
        fnames += ['input_%i' % i + self.display_ext
                   for i in range(self.input_nb)]
        for fname in fnames:
            shutil.copy(os.path.join(oldpath, fname),
                        os.path.join(self.path('tmp'), fname))
        self.log("input cloned from %s" % oldkey)
        return

    #
    # INPUT STEP
    #

    def input_select(self, input_id, **kwargs):
        """
        use the selected available input images
        """
        # kwargs is for input_id.x and input_id.y, unused
        del kwargs
        self.new_key()
        input_dict = index_dict(self.path('input'))
        fnames = input_dict[input_id]['files'].split()
        for i in range(len(fnames)):
            shutil.copy(self.path('input', fnames[i]),
                        self.path('tmp', 'input_%i' % i))
        input_url = self.process_input()
        urld = {'next_step' : self.url('params'),
                'input' : input_url}
        self.log("input selected : %s" % input_id)
        return self.tmpl_out("input.html", urld=urld)

    def input_upload(self, **kwargs):
        """
        use the uploaded input images
        """
        self.new_key()
        for i in range(self.input_nb):
            file_up = kwargs['file_%i' % i]
            file_save = file(self.path('tmp', 'input_%i' % i), 'wb')
            size = 0
            while True:
                # TODO : larger data size
                data = file_up.file.read(128)
                if not data:
                    break
                size += len(data)
                if size > self.input_max_weight:
                    # TODO : handle error
                    pass
                file_save.write(data)
            file_save.close()
        input_url = self.process_input()
        urld = {'next_step' : self.url('params'),
                'input' : input_url}
        self.log("input uploaded")
        return self.tmpl_out("input.html", urld=urld)

    #
    # PARAMETER HANDLING
    #

    @get_check_key
    def params(self, newrun=False):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        urld = {'next_step' : self.url('run')}
        return self.tmpl_out("params.html", urld=urld)

    #
    # EXECUTION AND RESULTS
    #

    @get_check_key
    def run(self, **kwargs):
        """
        run redirection
        """
        # TODO : filter-out kwargs from a class attr ans store in file
        # redirect to the result page
        del kwargs
        cherrypy.response.status = "303 See Other"
        cherrypy.response.headers['Refresh'] = \
            "0; %s" % self.url('result', {'key':self.key})
        urld = {'next_step' : self.url('result'),
                'input' : [self.url('tmp', 'input_%i' % i + self.display_ext)
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
        """
        # TODO : ensure only running once
        # TODO : save each result in a new archive
        # TODO : give the archive link
        # TODO : give the option to not be public
        #        (and remember it from a cookie)
        # TODO : read the kwargs from a file, and pass to run_algo
        # TODO : pass these parameters to the template
        self.run_algo({})
        self.log("input processed")
        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_%i' % i + self.display_ext)
                           for i in range(self.input_nb)],
                'output' : [(self.url('tmp', 'output' + self.display_ext),
                             self.url('tmp', 'output' + self.output_ext))]}
        return self.tmpl_out("result.html", urld=urld)
