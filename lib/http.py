"""
HTTP tools
"""
# pylint: disable=C0103

import cherrypy

def redir_301(url):
    """
    HTTP "301 Moved Permanently" redirection
    """
    cherrypy.response.status = "301 Moved Permanently"
    cherrypy.response.headers['Location'] = "%s" % url

def redir_302(url):
    """
    HTTP "302 Found" redirection
    """
    cherrypy.response.status = "302 Found"
    cherrypy.response.headers['Location'] = "%s" % url

def redir_303(url):
    """
    HTTP "303 See Other" redirection
    """
    cherrypy.response.status = "303 See Other"
    cherrypy.response.headers['Location'] = "%s" % url

# HTTP 307 implementation is not reliable
# would be better for a POST->POST wait->run redirection
# http://www.alanflavell.org.uk/www/post-redirect.html
# http://stackoverflow.com/questions/46582/redirect-post
def redir_307(url):
    """
    HTTP "307 Temporary Redirect" redirection
    """
    cherrypy.response.status = "307 Temporary Redirect"
    cherrypy.response.headers['Location'] = "%s" % url

def refresh(url, delay=0):
    """
    HTTP "Refresh" header
    """
    cherrypy.response.headers['Refresh'] = "%i; %s" % (delay, url)

