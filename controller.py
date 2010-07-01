#! /usr/bin/python

"""
Hello World
"""

import cherrypy

class HelloWorld:
    """ Sample request handler class. """

    def index(self):
        return "Hello world!"
    index.exposed = True


if __name__ == '__main__':

    import os.path

    cherrypy.quickstart(HelloWorld(), 
                        config=os.path.join(os.path.dirname(__file__),
                                            'server.conf'))
