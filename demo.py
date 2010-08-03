#! /usr/bin/python
""" base cherrypy launcher for the IPOL demo app """

import cherrypy
from mako.template import Template

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

        tmpl = os.path.join(os.path.dirname(__file__), 'index.html')
        return Template(filename=tmpl,
                        input_encoding='utf-8',
                        output_encoding='utf-8',
                        encoding_errors='replace').render(indexd=self.indexd)

if __name__ == '__main__':

    import os

    conf_file = os.path.join(os.path.dirname(__file__), 'demo.conf')

    demo_dict = {}
    demo_blacklist = ['.git', 'base_demo', 'template_demo']
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cherrypy.log("app base_dir : %s" % base_dir,
                 context='SETUP', traceback=False)
    cherrypy.config.update(conf_file)

    # load the demo collection
    # from now, the demo id is the demo module name, which happens to
    # also be the folder name
    for demo_id in os.listdir(base_dir):
        if not os.path.isdir(os.path.join(base_dir, demo_id)):
            continue
        if demo_id in demo_blacklist:
            continue
        # function version of `from demo_id import app as demo.app`
        demo = __import__(demo_id, globals(), locals(), ['app'], -1)
        # filter test demos
        if (cherrypy.config['server.environment'] == 'production'
            and demo.app.is_test):
            continue
        cherrypy.log("loading demo : %s" % demo_id, context='SETUP',
                     traceback=False)
        demo_dict[demo_id] = demo.app
        mount_point = '/' + demo_id
        # static subfolders config
        config = {'/input':
                      {'tools.staticdir.on' : True,
                       'tools.staticdir.dir' : \
                           os.path.join(base_dir, demo_id, 'data', 'input')
                       },
                  '/tmp':
                      {'tools.staticdir.on' : True,
                       'tools.staticdir.dir' : \
                           os.path.join(base_dir, demo_id, 'data', 'tmp')
                       },
                  }
        cherrypy.tree.mount(demo.app(), mount_point, config=config)

    # use cgitb error handling
    # enable via config
    # [/]
    # tools.cgitb.on = True
    cherrypy.tools.cgitb = cherrypy.Tool('before_error_response', err_tb)
    
    cherrypy.quickstart(demo_index(demo_dict), config=conf_file)
