#! /usr/bin/python
""" base cherrypy launcher for the IPOL demo app """

import cherrypy
from mako.lookup import TemplateLookup

def err_tb():
    """
    replace the default error response
    with an cgitb HTML traceback
    """
    import cgitb, sys
    tb = cgitb.html(sys.exc_info())
    def set_tb():
        """ set the traceback output """
        cherrypy.response.body = tb
        cherrypy.response.headers['Content-Length'] = None
    cherrypy.request.hooks.attach('after_error_response', set_tb)


class demo_index:
    """
    simplistic demo index used as the root app
    """

    def __init__(self, indexd=None):
        """
        initialize with demo_dict for indexing
        """
        if indexd == None:
            self.indexd = {}
        else:
            self.indexd = indexd

    @cherrypy.expose
    def index(self):
        """
        simple demo index page
        """

        tmpl_dir = os.path.join(os.path.dirname(__file__),
                                'lib', 'template')
        tmpl_lookup = TemplateLookup(directories=[tmpl_dir],
                                     input_encoding='utf-8',
                                     output_encoding='utf-8',
                                     encoding_errors='replace')
        return tmpl_lookup.get_template('index.html')\
            .render(indexd=self.indexd,
                    title="Demonstrations",
                    description="foo")

if __name__ == '__main__':

    import os
    import shutil

    # config file and location settings
    base_dir = os.path.dirname(os.path.abspath(__file__))
    conf_file = os.path.join(base_dir, 'demo.conf')
    conf_file_example = os.path.join(base_dir, 'demo.conf.example')

    demo_dict = {}
    # TODO: blacklist and whitelist text files
    demo_blacklist = ['.git', 'lib']
    cherrypy.log("app base_dir: %s" % base_dir,
                 context='SETUP', traceback=False)

    if not os.path.isfile(conf_file):
        cherrypy.log("warning: the conf file is missing, " \
                         "copying the example conf",
                     context='SETUP', traceback=False)
        shutil.copy(conf_file_example, conf_file)

    cherrypy.config.update(conf_file)

    # load the demo collection
    # from now, the demo id is the demo module name, which happens to
    # also be the folder name
    # TODO: mode the demos to a subfolder (solve the lib import issue)
    # TODO: first make a (demo_id:demo_app) dict, then use it
    for demo_id in os.listdir(base_dir):
        if not os.path.isdir(os.path.join(base_dir, demo_id)):
            continue
        if demo_id in demo_blacklist:
            continue
        # function version of `from demo_id import app as demo.app`
        demo = __import__(demo_id, globals(), locals(), ['app'], -1)
        # filter test demos
        # TODO: use real filter
        if (cherrypy.config['server.environment'] == 'production'
            and demo.app.is_test):
            continue
        cherrypy.log("loading demo: %s" % demo_id, context='SETUP',
                     traceback=False)
        demo_dict[demo_id] = demo.app
        mount_point = '/' + demo_id
        # static subfolders config
        input_dir = os.path.join(base_dir, demo_id, 'input')
        tmp_dir = os.path.join(base_dir, demo_id, 'tmp')
        config = {'/input':
                      {'tools.staticdir.on' : True,
                       'tools.staticdir.dir' : input_dir
                       },
                  '/tmp':
                      {'tools.staticdir.on' : True,
                       'tools.staticdir.dir' : tmp_dir
                       },
                  }
        # create missing static subfolders
        if not os.path.isdir(input_dir):
            cherrypy.log("warning: missing input folder, creating it",
                         context='SETUP', traceback=False)
            os.mkdir(input_dir)
        if not os.path.isdir(tmp_dir):
            cherrypy.log("warning: missing tmp folder, creating it",
                         context='SETUP', traceback=False)
            os.mkdir(tmp_dir)
        # mount static subfolders
        cherrypy.tree.mount(demo.app(), mount_point, config=config)

    # use cgitb error handling
    # enable via config
    # [global]
    # tools.cgitb.on = True
    cherrypy.tools.cgitb = cherrypy.Tool('before_error_response', err_tb)
    
    cherrypy.quickstart(demo_index(demo_dict), config=conf_file)
