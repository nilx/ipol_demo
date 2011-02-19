"""
build tools
"""
# pylint: disable=C0103

import os, shutil
import urllib2, time
import tarfile, zipfile
from subprocess import Popen
import cherrypy

from .misc import mtime

TIME_FMT = "%a, %d %b %Y %H:%M:%S %Z"

def download(url, fname):
    """
    download a file from the network if it is newer than the local
    file
    
    @param url: source url
    @param fname: destination file name

    @return: the file name
    """
    cherrypy.log("retrieving: %s" % url, context='BUILD',
                 traceback=False)

    # create the folder if needed
    if not os.path.isdir(os.path.dirname(fname)):
        os.mkdir(os.path.dirname(fname))

    try:
        # setup http auth manager, if info provided
        urlbase = cherrypy.config['download.auth.urlbase']
        username = cherrypy.config['download.auth.username']
        password = cherrypy.config['download.auth.password']
    except KeyError:
        urlbase = ''
        username = ''
        password = ''

    pwd_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    pwd_manager.add_password(None, urlbase, username, password)
    # open the url
    auth_handler = urllib2.HTTPBasicAuthHandler(pwd_manager)
    url_opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(url_opener)
  
    # open the url
    url_handle = urllib2.urlopen(url)

    if not os.path.isfile(fname):
        # no local copy : retrieve
        file_handle = open(fname, 'w')
        file_handle.write(url_handle.read())
        file_handle.close()
        cherrypy.log("retrieved", context='BUILD',
                     traceback=False)
    else:
        # only retrieve if a newer version is available
        url_mtime = time.strptime(url_handle.info()['last-modified'],
                                  TIME_FMT)
        url_size = int(url_handle.info()['content-length'])
        file_mtime = mtime(fname)
        file_size = os.path.getsize(fname)
        if (url_size != file_size
            or url_mtime > file_mtime):
            # download
            file_handle = open(fname, 'w')
            file_handle.write(url_handle.read())
            file_handle.close()
            cherrypy.log("retrieved", context='BUILD',
                         traceback=False)
        else:
            cherrypy.log("not retrieved (local file is newer)",
                         context='BUILD', traceback=False)
        url_handle.close()
    return fname

def extract(fname, target):
    """
    extract tar, tgz, tbz and zip archives

    @param fname: archive file name
    @param target: target extraction directory

    @return: the archive content
    """
    try:
        # start with tar
        ar = tarfile.open(fname)
        content = ar.getnames()
    except tarfile.ReadError:
        # retry with zip
        ar = zipfile.ZipFile(fname)
        content = ar.namelist()

    # no absolute file name
    assert not any([os.path.isabs(f) for f in content])
    # no .. in file name
    assert not any([(".." in f) for f in content])
    
    # cleanup/create the target dir
    if os.path.isdir(target):
        shutil.rmtree(target)
    os.mkdir(target)

    # extract into the target dir
    try:
        ar.extractall(target)
    except AttributeError:
        # zipfile module < 2.6
        for member in content:
            if member.endswith(os.path.sep):
                os.mkdir(os.path.join(target, member))
            else:
                f = open(os.path.join(target, member), 'wb')
                f.write(ar.read(member))
                f.close()

    cherrypy.log("extracted: %s" % fname, context='BUILD',
                 traceback=False)

    return content

def run(command, stdout, cwd=None, env=None):
    """
    run a build execution

    @param command: shell-like command string
    @param stdout: standard output storage

    @return: the exit code
    """
    # merge env with the current environment 
    if env != None:
        environ = os.environ
        environ.update(env)
        env = environ

    # open the log file and write the command
    logfile = open(stdout, 'w')
    logfile.write("%s : %s\n" % (time.strftime(TIME_FMT),
                                 command))
    # TODO : fix'n'clean
    logfile.close()
    logfile = open(stdout, 'a')
    process = Popen(command, shell=True, stdout=logfile, stderr=logfile,
                    cwd=cwd, env=env)
    cherrypy.log("running: %s" % command, context='BUILD',
                 traceback=False)
    process.wait()
    logfile.close()
    if 0 != process.returncode:
        raise RuntimeError
    return process.returncode
