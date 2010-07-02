"""
helper tools
"""

#
# TINY STUFF
#

prod = lambda l : reduce(lambda a, b : a * b, l, 1)
# sum() is already defined
#sum = lambda l : reduce(lambda a, b : a + b, l, 0)

#
# INDEX DICTIONARY
#

import os.path
import ConfigParser
class index_dict(dict):
    """
    folder index as a dictionnary, read from an index.cfg file
    """
    def __init__(self, location):
        """ populate the dict from the index metadata file """

        dict.__init__(self)
        
        index = ConfigParser.RawConfigParser()
        index.read(os.path.join(location, 'index.cfg'))
        for section in index.sections():
            self[section] = dict(index.items(section))

#
# THUMBNAIL IMAGE CLASS
#

from PIL import Image
class tn_image(object):
    """
    thumbnail image
    """

    def __init__(self, location, size=(128, 128), ext=".png"):
        """
        read the image
        and automatically generate a thumbnail if needed
        """

        location = os.path.abspath(location)
        (folder, fname) = os.path.split(location)
        (basename, ext) = os.path.splitext(fname)

        self.fname = basename + ".__%ix%i__" % size + ext
        if not os.path.isfile(os.path.join(folder, self.fname)):
            im = Image.open(location)
            tn = Image.new('RGBA', size, (0, 0, 0, 0))
            im.thumbnail(size, resample=True)
            offset = ((size[0] - im.size[0]) / 2,
                      (size[1] - im.size[1]) / 2)
            box = offset + (im.size[0] + offset[0],
                            im.size[1] + offset[1])
            tn.paste(im, box)
            tn.save(os.path.join(folder, self.fname))

#
# IMAGE CLASS
#

class image(object):
    """
    manipulable image
    this class is basically a PIL abstraction
    nothing is written until explicitly asked
    """

    def __init__(self, location):
        """
        open the image
        """
        location = os.path.abspath(location)
        (self.folder, self.fname) = os.path.split(location)

        self.im = Image.open(location)

    def __getattr__(self, attr):
        """ 
        direct access to some image attributes 
        """
        if attr == 'size':
            return self.im.size
        else:
            return object.__getattribute__(self, attr)

    def crop(self, box):
        """
        crop the image, in-place
        """
        self.im = self.im.crop(box)
        return self

    def resize(self, size, mode='xy'):
        """
        resize the image, in-place
        """

        if mode == 'xy':
            # size must be a tuple (nx, ny)
            newsize = size
        elif mode == 'scale':
            # size must be an int/float scale ratio
            newsize = (self.im.size[0] * size, self.im.size[1] * size)
        elif mode == 'pixels':
            # size is a number of pixels
            newsize = (self.im.size[0] * size / prod(self.im.size),
                       self.im.size[1] * size / prod(self.im.size))

        self.im = self.im.resize(newsize, resample=True)
        return self

    def convert(self, mode):
        """
        convert the pixel format :
        * 1x1i : 1bit binary monochrome
        * 1x8i : 8bit gray
        * 3x8i : 8bit RGB
        * 1x32i : 32bit gray
        * 1x32f : 32bit float
        """
        # PIL mode keywords
        mode_kw = {'1x1i' : '1',
                   '1x8i' : 'L',
                   '3x8i' : 'RGB',
                   '1x32i' : 'I',
                   '1x32f' : 'F'}
        self.im = self.im.convert(mode_kw[mode])
        return self

    def save(self, fname, **kwargs):
        """
        save the image file
        """
        # TODO : handle external TIFF compression
        self.im.save(fname, **kwargs)

#
# ACTION DECORATOR TO HANDLE DEMO KEY
#

def get_check_key(func):
    """
    decorator to read the key,
    save it as a class attribute,
    and check the key validity
    """
    def checked_func(self, *args, **kwargs):
        """
        original function with a preliminary key check
        """
        self.key = kwargs.pop('key')
        self.check_key()
        return func(self, *args, **kwargs)
    return checked_func

#
# CHERRYPY REDIRECTION
#

import cherrypy
def http_redirect_303(url):
    """
    HTTP "303 See Other" redirection
    """
    cherrypy.response.status = "303 See Other"
    cherrypy.response.headers['Refresh'] = "0; %s" % url
