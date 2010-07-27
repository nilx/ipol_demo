#! /usr/bin/python
# encoding: utf-8
""" base cherrypy launcher for the IPOL demo app """

import cherrypy

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
        # TODO: use mako
        page = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>IPOL: Demonstrations</title>
<meta name="language" content="english" />
<link rel="icon" href="http://www.ipol.im/favicon.ico" type="image/x-icon" />
<link rel="stylesheet" href="http://www.ipol.im/style.css" type="text/css" />
<link rel="stylesheet" href="http://www.ipol.im/local.css" type="text/css" />
</head>
<body>
<div class="pageheader">
<div class="header">
<div class="parentlinks">
<a href="http://www.ipol.im/">ipol.im</a>
»
<a href="http://www.ipol.im/pub/">pub</a>
»
</div> <!-- .parentlinks -->
</div> <!-- .header -->
</div> <!-- .pageheader -->
<div id="main">
<div id="pagetitle">
Demonstrations
</div> <!-- #pagetitle -->
<div id="content">
"""
        for key in self.indexd.keys():
            page += "<li><a href='./%(id)s/'>%(title)s</a></li>" \
                % {'id' : key, 'title' : self.indexd[key].title}
        page += "</ul>"
        page += """
</div> <!-- #content -->
</div> <!-- #main -->
<div id="footer" class="pagefooter">
<ul>
<!--
<li class="pagedate">
  last modified <span class="date"></span>
</li>
-->
<li class="feeds">
  <a href="/feed/">feeds</a>
</li>
<li class="sitemap">
  <a href="/meta/sitemap/" rel="sitemap">sitemap</a>
</li>
<li class="contact">
  <a href="/meta/contact/">contact</a>
</li>
<li class="privacy">
  <a href="/meta/privacy/">privacy policy</a>
</li>
</ul>
<ul>
<li class="hostinfo">
  hosting provided by
  <a href="http://www.cmla.ens-cachan.fr/">CMLA</a>,
  <a href="http://www.ens-cachan.fr/">ENS Cachan</a>
</li>
<li class="refs">
  <a href="http://www.issn.org/">ISSN:2105-1232</a>
  <!-- link http://www.worldcat.org/issn/2105-1232 empty -->
  <a href="http://www.crossref.org/">DOI:pending</a>
</li>
<li class="pagecopyright">
  <a name="pagecopyright"></a>
  <a href="/meta/copyright/" rel="copyright">copyright ©&nbsp;2009-2010,
  IPOL Image Processing On Line</a>
</li>
</ul>
<!-- from IPOL -->
</div><!-- .pagefooter #footer -->
</body>
</html>
"""
        return page

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
