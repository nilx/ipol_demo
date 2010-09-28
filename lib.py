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
    def __init__(self, location, fname='index.cfg'):
        """ populate the dict from the index metadata file """

        dict.__init__(self)
        self.fname = os.path.join(location, fname)

        index = ConfigParser.RawConfigParser()
        index.read(self.fname)
        for section in index.sections():
            self[section] = dict(index.items(section))

    def save(self):
        """ save the (updated) dict to the index metadata file """

        dict.__init__(self)
        
        index = ConfigParser.RawConfigParser()
        for section in self.keys():
            index.add_section(section)
            for option in self[section].keys():
                index.set(section, option,
                          self[section][option])
        index_file = open(self.fname, 'w')
        index.write(index_file)
        index_file.close()

#
# THUMBNAIL IMAGE CLASS
#

from PIL import Image

def tn_image(location, size=(128, 128), ext=".png"):
    """
    image thumbnailing function

    @param location full-size file name
    @param size thumbnail size, default 128x128
    @param ext thumbnail file extension (and format), default ".png"

    @return thumbnail file name
    """

    # parse the file name
    location = os.path.abspath(location)
    (folder, fname) = os.path.split(location)
    (basename, extension) = os.path.splitext(fname)

    tn_location = os.path.join(folder,
                               basename + ".__%ix%i__" % size + ext)
    if not os.path.isfile(tn_location):
        # no thumbnail, create it
        im = Image.open(location)
        tn = Image.new('RGBA', size, (0, 0, 0, 0))
        im.thumbnail(size, resample=True)
        offset = ((size[0] - im.size[0]) / 2,
                  (size[1] - im.size[1]) / 2)
        box = offset + (im.size[0] + offset[0],
                        im.size[1] + offset[1])
        tn.paste(im, box)
        tn.save(tn_location)

    return tn_location
    
#
# IMAGE CLASS
#

class image(object):
    """
    manipulable image
    this class is basically a PIL abstraction
    nothing is written until explicitly asked
    """

    def __init__(self, src=None):
        """
        open the image
        src not specified : empty image
        src is a string : read the file
        src is a PIL Image : use it
        """
        if isinstance(src, Image.Image):
            self.im = src
        if isinstance(src, str):
            self.im = Image.open(src)

    def __getattr__(self, attr):
        """ 
        direct access to some image attributes 
        """
        if attr == 'size':
            return self.im.size
        else:
            return object.__getattribute__(self, attr)

    def save(self, fname, **kwargs):
        """
        save the image file
        """
        # TODO : handle external TIFF compression
        self.im.save(fname, **kwargs)
        return fname

    def crop(self, box):
        """
        crop the image, in-place
        """
        self.im = self.im.crop(box)
        return self

    def resize(self, size):
        """
        resize the image, in-place
        """

        if isinstance(size, int):
            # size is a number of pixels -> convert to a float scale
            size = (float(size) / (self.im.size[0] * self.im.size[1])) ** .5

        if isinstance(size, float):
            # size is a scale -> convert to (x, y)
            size = (int(self.im.size[0] * size),
                    int(self.im.size[1] * size))

        self.im = self.im.resize(size, Image.BICUBIC)
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

    def split(self, nb, margin=0, fname=None):
        """
        split an image vertically into nb tiles,
        with an optional margin
        returns a list of images if fname is not specified,
        or a list of filenames where these images are saved
        """
        
        assert (nb >= 2)
        xmax, ymax = self.im.size
        dy = float(ymax) / nb
        
        # list of the crop boxes
        boxes = [(0, 0, xmax, int(dy) + margin)]
        boxes += [(0, int(n * dy) - margin, xmax, int((n + 1) * dy) + margin)
                 for n in range(1, nb - 1)]
        boxes += [(0, int((nb - 1) * dy) - margin, xmax, ymax)]
        
        # cut the image
        tiles = [image(self.im.crop(box)) for box in boxes]

        if not fname:
            return tiles
        else:
            basename, ext = os.path.splitext(fname)
            return [tiles[i].save(basename + ".__%0.2i__" % i + ext)
                    for i in range(len(tiles))]

    def join(self, tiles, margin=0):
        """
        read tiles and join them vertically
        """
        
        # compute the full image size
        xmax = tiles[0].im.size[0]
        ymax = 0
        for tile in tiles:
            assert (tile.im.size[0] == xmax)
            ymax += tile.im.size[1] - 2 * margin
        ymax += 2 * margin

        self.im = Image.new(tiles[0].im.mode, (xmax, ymax))

        # join the images
        ystart = 0
        tile = tiles[0].im
        dy = tile.size[1] - margin
        self.im.paste(tile.crop((0, 0, xmax, dy)), (0, ystart))
        ystart += dy
        for tile in tiles[1:-1]:
            tile = tile.im
            dy = tile.size[1] - 2 * margin
            self.im.paste(tile.crop((0, margin, xmax, dy + margin)),
                          (0, ystart))
            ystart += dy
        tile = tiles[-1].im
        dy = tile.size[1] - margin
        self.im.paste(tile.crop((0, margin, xmax, dy + margin)),
                      (0, ystart))

        return self

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
        self.key = kwargs.pop('key', '')
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

#
# BASE_APP REUSE
#

def app_expose(function):
    """
    shortcut to expose app actions from the base class
    """
    function.im_func.exposed = True

#
# EXCEPTIONS
#

class TimeoutError(Exception):
    pass
class RuntimeError(Exception):
    pass
