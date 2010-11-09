"""
archive bucket class
"""
# pylint: disable=C0103


import os.path
import time
import shutil
import gzip

from . import config
from .image import thumbnail

def key2url(key):
    """
    url construction scheme
    """
    return "%s/%s/" % (key[:2], key[2:])

def key2path(key):
    """
    path construction scheme
    """
    return os.path.join(key[:2], key[2:])

def path2key(path):
    """
    reverse key2path()
    """
    return ''.join(os.path.split(path))

def list_key(path):
    """
    get a list of all the bucket keys in the path
    """
    # TODO: iterator
    return [path2key(os.path.join(pfx, sfx))
            for pfx in os.listdir(path)
            if os.path.isdir(os.path.join(path, pfx))
            for sfx in os.listdir(os.path.join(path, pfx))
            if os.path.isdir(os.path.join(path, pfx, sfx))]

class bucket(object):
    """
    archive bucket class
    """
    # TODO: commit() model
    def __init__(self, path, key, cwd=None):
        """
        opem/read/crewate an archive bucket

        an archive bucket is
        * a set of files
        * a config dict, with these 3 sections:
          * info : free-form informations
          * file : file legends
          * meta : archive meta-information:
            * date : archive date

        @param path: base archive folder
        @param key: unique bucket key
        @param cwd: working directory used when adding files
        """
        date = time.strftime("%Y/%m/%d %H:%M")
        # bucket path
        path = os.path.abspath(path)
        self.path = os.path.join(path, key2path(key))
        # create the folder if needed
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        # read or init config dictionary
        self.cfg = config.file_dict(self.path)
        if not (self.cfg.has_key('info')
                and self.cfg.has_key('fileinfo')
                and self.cfg.has_key('meta')
                and self.cfg['meta'].has_key('date')
                and self.cfg['meta'].has_key('key')):
            self.cfg.setdefault('info', {})
            self.cfg.setdefault('fileinfo', {})
            self.cfg.setdefault('meta', {})
            self.cfg['meta'].setdefault('date', date)
            self.cfg['meta'].setdefault('key', key)
            self.cfg.save()
        # working directory for add_file()
        self.cwd = cwd
        # pending files
        self.pend_files = []
        self.pend_zfiles = []

    def add_file(self, src, dst=None, info='', compress=False):
        """
        save a file in the archive bucket
        the file is copied from self.cwd to self.path
        """
        # source filename
        src = os.path.basename(src)
        src_fname = os.path.join(self.cwd, src)
        # destination filename
        if dst is None:
            dst = src
        dst = os.path.basename(dst)
        if compress:
            dst += '.gz'
        dst_fname = os.path.join(self.path, dst)
        # add to the pending list
        if not compress:
            self.pend_files.append((src_fname, dst_fname))
        else:
            self.pend_zfiles.append((src_fname, dst_fname))
        # add the file info
        self.cfg['fileinfo'][dst] = info

    def add_info(self, info):
        """
        add an info {key: value} in the archive config dict
        """
        self.cfg['info'].update(info)

    def commit(self):
        """
        copy the files,
        save the config file
        """
        # save the pending files
        for (src, dst) in self.pend_files:
            shutil.copy(src, dst)
        self.pend_files = []
        for (src, dst) in self.pend_zfiles:
            f_src = open(src, 'rb')
            f_dst = gzip.open(dst, 'wb')
            f_dst.writelines(f_src)
            f_dst.close()
            f_src.close()
        self.pend_zfiles = []
        # update the config
        self.cfg.save()

#
# INDEX ITEMS 
#

class item(object):
    """
    content of an index
    """
    def __init__(self, path, info=''):
        """
        create an index_item
        """
        self.path = os.path.abspath(path)
        self.name = os.path.basename(path)
        #self.ctime = misc.ctime(path, format="iso")
        #self.mtime = misc.mtime(path, format="iso")
        self.info = info
        if os.path.isdir(path):
            self.is_file = False
            self.is_dir = True
        if os.path.isfile(path): 
            self.is_file = True
            self.is_dir = False
            if self.name.endswith((".png", ".tif", ".tiff")):
                self.tn_path = thumbnail(self.path, size=(64, 64))
                self.tn_name = os.path.basename(self.tn_path)
                self.has_tn = True
            else:
                self.has_tn = False
