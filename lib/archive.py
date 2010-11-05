"""
archive bucket class
"""
# pylint: disable=C0103


import os.path
import time
import shutil
from .misc import index_dict
import gzip

class bucket(object):
    """
    archive bucket class
    """
    def __init__(self, path, cwd):
        """
        initalize the archive bucket

        an archive bucket is
        * a set of files
        * a config dict, with these 3 sections:
          * info : free-form informations
          * file : file legends
          * meta : archive meta-information:
            * date : archive date

        @param path: folder containing this config file
        @param cwd: working directory used when adding files
        """
        # archive path
        self.path = os.path.abspath(path)
        # create the folder if needed
        if not os.path.isdir(path):
            os.makedirs(self.path)
        # working directory
        self.cwd = os.path.abspath(cwd)
        assert os.path.isdir(self.cwd)
        # config dictionary
        self.cfg = index_dict(self.path)
        self.cfg.setdefault('info', {})
        self.cfg.setdefault('file', {})
        self.cfg.setdefault('meta', {})
        self.cfg['meta'].setdefault('date', time.strftime("%Y/%m/%d %H:%M"))

    def add_file(self, src, dst=None, legend='', compress=False):
        """
        save a file in the archive bucket
        the file is copied from self.cwd to self.path
        """
        # source filename
        src = os.path.basename(src)
        src_fname = os.path.join(self.cwd, src)
        assert os.path.isfile(src_fname)
        # destination filename
        if dst is None:
            dst = src
        dst = os.path.basename(dst)
        if compress:
            dst += '.gz'
        dst_fname = os.path.join(self.path, dst)
        # copy the file
        if not compress:
            shutil.copy(src_fname, dst_fname)
        else:
            f_in = open(src, 'rb')
            f_out = gzip.open(dst_fname, 'wb')
            f_out.writelines(f_in)
            f_out.close()
            f_in.close()
        # save the file legend
        self.cfg['file'][dst] = legend

    def add_info(self, info):
        """
        add an info {key: value} in the archive config dict
        """
        self.cfg['info'].update(info)
        self.cfg.save()
