"""
archive bucket class
"""
# pylint: disable=C0103


import os.path
import time
import shutil
import gzip
import sqlite3

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
        # FIXME: file_dict keys are lowercase
        dst = dst.lower()
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
                self.tn_path = thumbnail(self.path, size=(128, 128))
                self.tn_name = os.path.basename(self.tn_path)
                self.has_tn = True
            else:
                self.has_tn = False

#
# DATABASE
#

def index_rebuild(indexdb, path):
    """
    create an index of the archive buckets
    """
    cherrypy.log("(re)building the archive index %s" % indexdb,
                 context='SETUP', traceback=False)
    db = sqlite3.connect(indexdb)
    c = db.cursor()
    # (re)create table
    c.execute("drop table if exists buckets")
    # TODO : check SQL index usage
    c.execute("drop index if exists buckets_by_date")
    c.execute("create table buckets (key text unique, date text)")
    c.execute("create index buckets_by_date on buckets (date)")
    # populate the db
    for key in list_key(path):
        bucket = bucket(path=path, key=key)
        date = bucket.cfg['meta']['date']
        c.execute("""insert into buckets (key, date) values (?, ?)""",
                  (key, date))
    db.commit()
    c.close()


def index_keys(indexdb, limit=50, offset=0):
    """
    get some keys from the index
    """
    # TODO: use iterators
    db = sqlite3.connect(indexdb)
    c = db.cursor()
    c.execute("select key from buckets order by date desc "
              + "limit ? offset ?",
              (limit, offset))
    return [key[0] for key in c]


def index_count(indexdb):
    """
    get nb keys in the index
    """
    db = sqlite3.connect(indexdb)
    c = db.cursor()
    c.execute("select count(*) from buckets")
    return c.next()[0]

def index_add(indexdb, key, date):
    """
    add an archive bucket to the index
    """
    db = sqlite3.connect(indexdb)
    c = db.cursor()
    c.execute("insert or replace into buckets (key, date) values (?, ?)",
              (self.key, date))
    db.commit()
    c.close()
