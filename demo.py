#! /usr/bin/python
"""
base cherrypy launcher for the IPOL demo app
"""
# pylint: disable=C0103

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


class demo_index(object):
    """
    simplistic demo index used as the root app
    """

    def __init__(self, indexd):
        """
        initialize with demo_dict for indexing
        """
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
                    description="")

if __name__ == '__main__':

    import os
    import shutil

    # config file and location settings
    base_dir = os.path.dirname(os.path.abspath(__file__))
    conf_file = os.path.join(base_dir, 'demo.conf')
    conf_file_example = os.path.join(base_dir, 'demo.conf.example')
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
    from app import demo_dict
    # filter out test demos
    if cherrypy.config['server.environment'] == 'production':
        for (demo_id, demo_app) in demo_dict.items():
            if demo_app.is_test:
                demo_dict.pop(demo_id)
    # mount the demo apps
    for (demo_id, demo_app) in demo_dict.items():
        cherrypy.log("loading demo: %s" % demo_id, context='SETUP',
                     traceback=False)
        cherrypy.tree.mount(demo_app(), script_name='/%s' % demo_id)

    # use cgitb error handling
    # enable via config
    # [global]
    # tools.cgitb.on = True
    cherrypy.tools.cgitb = cherrypy.Tool('before_error_response', err_tb)
    
    # start the server
    cherrypy.quickstart(demo_index(demo_dict), config=conf_file)
