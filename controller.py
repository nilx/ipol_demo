#! /usr/bin/python

"""
Hello World
"""

import cherrypy

class HelloWorld:
    """ Sample request handler class. """

    def index(self):
        return "Hello world! (dev test)"
    index.exposed = True


if __name__ == '__main__':

    from sys import argv
    import os.path

    config_fname = {'local' : 'local.conf',
                    'server' : 'server.conf'}
    pwd = os.path.dirname(__file__)
    for key in config_fname.keys():
        config_fname[key] = os.path.join(pwd, config_fname[key])

    try:
        cherrypy.quickstart(HelloWorld(), config=config_fname[argv[1]])
    except IndexError:
        print 'a configuration parameter is needed'
    except KeyError:
        print 'the configuration parameter must be in : %s' \
            % ', '.join(config_fname.keys())
