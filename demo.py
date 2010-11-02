#! /usr/bin/python
"""
base cherrypy launcher for the IPOL demo app
"""
# pylint: disable=C0103

import cherrypy
from mako.lookup import TemplateLookup

import os
import shutil


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

def do_build(demo_dict):
    """
    build/update the demo programs
    """
    for (demo_id, demo_app) in demo_dict.items():
        # update the demo apps programs
        demo = demo_app()
        cherrypy.log("building", context='SETUP/%s' % demo_id,
                     traceback=False)
        demo.build()
    return

def do_clean(demo_dict):
    """
    cleanup all the temporary folders
    """
    for (demo_id, demo_app) in demo_dict.items():
        # delete temporary folders
        demo = demo_app()
        cherrypy.log("cleaning", context='SETUP/%s' % demo_id,
                     traceback=False)
        for clean_dir in [demo.tmp_dir, demo.bin_dir,
                          demo.dl_dir, demo.src_dir]:
            if os.path.isdir(clean_dir):
                shutil.rmtree(clean_dir)
    return

def do_run(demo_dict):
    """
    run the demo app server
    """
    for (demo_id, demo_app) in demo_dict.items():
        # mount the demo apps
        demo = demo_app()
        cherrypy.log("loading", context='SETUP/%s' % demo_id,
                     traceback=False)
        cherrypy.tree.mount(demo, script_name='/%s' % demo_id)
    # cgitb error handling config
    cherrypy.tools.cgitb = cherrypy.Tool('before_error_response', err_tb)
    # start the server
    cherrypy.quickstart(demo_index(demo_dict), config=conf_file)
    return

if __name__ == '__main__':

    import sys

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
    from app import demo_dict
    # filter out test demos
    if cherrypy.config['server.environment'] == 'production':
        for (demo_id, demo_app) in demo_dict.items():
            if demo_app.is_test:
                demo_dict.pop(demo_id)

    # now handle the command-line options

    # default behaviour : build, run
    if len(sys.argv) == 1:
        sys.argv += ["run"]

    for arg in sys.argv[1:]:
        if "clean" == arg:
            do_clean(demo_dict)
        elif "build" == arg:
            do_build(demo_dict)
        elif "run" == arg:
            do_run(demo_dict)
        else:
            print """
usage: %(argv0)s [action]

actions:
* clean   delete all temporary files
* build   build/update the compiled programs
* run     launch the web service

notes:
Default action is "run".
Multiple successive actions can be specified. They will be processed
in the arguments order. Note that the script will hang when the server
is run.
""" % {'argv0' : sys.argv[0]}
