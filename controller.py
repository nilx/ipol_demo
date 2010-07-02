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

        page = "<html><head><title>IPOL : Demonstrations</title></head>"
        page += "<body><h1>IPOL : Demonstrations</h1><ul>"
        for key in self.indexd.keys():
            page += "<li><a href='./%(id)s/'>%(title)s</a></li>" \
                % {'id' : key, 'title' : self.indexd[key].title}
        page += "</ul></body></html>"

        return page

if __name__ == '__main__':

    import os

    demo_dict = {}

    # load the demo collection
    # from now, the demo id is the demo module name, which happens to
    # also be the folder name
    # TODO : filter test demos
    demo_blacklist = ['.git', 'base_demo']
    base_dir = os.path.dirname(os.path.abspath(__file__))
    is_a_demo = lambda s : (os.path.isdir(os.path.join(base_dir,s)) 
                            and s not in demo_blacklist) 
    cherrypy.log("base_dir : %s" % base_dir,
                 context='DEBUG', traceback=False)
    cherrypy.log("listdir(base_dir) : %s" % str(os.listdir(base_dir)),
                 context='DEBUG', traceback=False)
    for demo_id in os.listdir(base_dir):
        cherrypy.log("try %s" % demo_id,
                 context='DEBUG', traceback=False)
        if not is_a_demo(demo_id):
            cherrypy.log("%s is not a demo" % demo_id,
                         context='DEBUG', traceback=False)
            continue
        else:
            cherrypy.log("%s is a demo" % demo_id,
                         context='DEBUG', traceback=False)
        # function version of `from demo_id import app as demo.app`
        # TODO : simplify
        demo = __import__(demo_id, globals(), locals(), ['app'], -1)
        cherrypy.log("loading demo : %s" % demo_id, context='SETUP',
                     traceback=False)
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
    # TODO : only for development
    cherrypy.tools.cgitb = cherrypy.Tool('before_error_response', err)
    
    cherrypy.quickstart(demo_index(demo_dict), 
                        config=os.path.join(os.path.dirname(__file__),
                                            'controller.conf'))
