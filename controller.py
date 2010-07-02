#! /usr/bin/python
""" base cherrypy launcher for the IPOL demo app """

import cherrypy

def err():
    """
    replace the default error response
    with an cgitb HTML traceback
    """
    import cgitb, sys
    tb = cgitb.html(sys.exc_info())
    def set_tb():
        cherrypy.response.body = tb
        cherrypy.response.headers['Content-Length'] = None
    cherrypy.request.hooks.attach('after_error_response', set_tb)


class demo_index:
    """
    simplistic demo index used as the root app
    """

    def __init__(self, demo_dict={}):
        """
        initialize with demo_dict for indexing
        """
        self.demo_dict = demo_dict

    def index(self):
        """
        simple demo index page
        """

        page = "<html><head><title>IPOL : Demonstrations</title></head>"
        page += "<body><h1>IPOL : Demonstrations</h1><ul>"
        for id in demo_dict:
            page += "<li><a href='./%(id)s/'>%(title)s</a></li>" \
                % {'id' : id, 'title' : demo_dict[id].title}
        page += "</ul></body></html>"

        return page
    index.exposed = True

if __name__ == '__main__':

    import os

    demo_dict = {}

    # load the demo collection
    # from now, the demo id is the demo module name, which happens to
    # also be the folder name
    demo_blacklist = ['.git', 'base_demo']
    is_a_demo = lambda s : (os.path.isdir(s) 
                            and s not in demo_blacklist) 
    for demo_id in filter(is_a_demo, os.listdir('./')):
        print "loading : " + demo_id
        # function version of `from demo_id import app as demo.app`
        # TODO : simplify
        demo = __import__(demo_id, globals(), locals(), ['app'], -1)
        demo_dict[demo_id] = demo.app
        mount_point = '/' + demo_id
        # static subfolders config
        config = {'/input':
                      {'tools.staticdir.on' : True,
                       'tools.staticdir.dir' : \
                           os.path.abspath(demo_id + '/data/input')
                       },
                  '/tmp':
                      {'tools.staticdir.on' : True,
                       'tools.staticdir.dir' : \
                           os.path.abspath(demo_id + '/data/tmp')
                       },
                  }
        cherrypy.tree.mount(demo.app(), mount_point, config=config)

    # use cgitb error handling
    cherrypy.tools.cgitb = cherrypy.Tool('before_error_response', err)
    
    cherrypy.quickstart(demo_index(), 
                        config=os.path.join(os.path.dirname(__file__),
                                            'controller.conf'))
