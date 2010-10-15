"""
build tools
"""
# pylint: disable-msg=C0103

import os.path
import urllib, time

def download(url, fname):
    """
    download a file from the network if it is newer than the local
    file
    
    @param url: source url
    @param fname: destination file name

    @return: the file name
    """
    # TODO restrict the allowed servers
    # TODO handle username/password
    if not os.path.isfile(fname):
        # no local copy : retrieve
        urllib.urlretrieve(url, fname)
    else:
        # only retrieve if a newer version is available
        urlfile = urllib.urlopen(url)
        urlfile_ctime = time.strptime(urlfile.info()['last-modified'],
                                      "%a, %d %b %Y %H:%M:%S %Z")
        urlfile_size = urlfile.info()['content-length']
        localfile_ctime = time.gmtime(os.path.getmtime(fname))
        localfile_size = os.path.getsize(fname)
        del urlfile
        if (urlfile_ctime > localfile_ctime
            or urlfile_size != localfile_size):
            urllib.urlretrieve(url, fname)
    return fname

import tarfile, zipfile

def extract_archive(fname, target):
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
    assert not any([os.path.isabs(fname) for fname in content])
    # no .. in file name
    assert not any([(".." in fname) for fname in content])
    ar.extractall(target)
    
    return content
