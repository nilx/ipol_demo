"""
image tools
"""
# pylint: disable=C0103

#
# IMAGE THUMBNAILER
#

from .misc import ctime

import os.path
import PIL.Image
import PIL.ImageOps
import PIL.ImageDraw

def _deinterlace_png(path):
    """
    PIL 1.6 can't handle interlaced PNG
    temporary workaround, fixed in PIL 1.7
    """
    im = PIL.Image.open(path)
    if im.format == 'PNG':
        try:
            im.getpixel((0, 0))
        except IOError:
            # check the file exists
            assert os.path.isfile(path)
            # convert it to non-interlaced
            os.system("/usr/bin/convert %s %s" 
                      % (path, path))
            im = PIL.Image.open(path)
            # try once again, in case there is another problem
            im.getpixel((0, 0))
    return
    

def thumbnail(path, size=(128, 128), ext=".png"):
    """
    image thumbnailing function

    @param path: full-size file name
    @param size: thumbnail size, default 128x128
    @param ext: thumbnail file extension (and format), default ".png"

    @return: thumbnail file name
    """
    # parse the file name
    path = os.path.abspath(path)
    _deinterlace_png(path)
    (folder, fname) = os.path.split(path)
    basename = os.path.splitext(fname)[0]

    tn_path = os.path.join(folder, ".__%ix%i__" % size
                           + basename + ext)
    if not (os.path.isfile(tn_path)
            and ctime(path) < ctime(tn_path)):
        # no thumbnail, create it
        im = PIL.Image.open(path)
        tn = PIL.Image.new('RGBA', size, (0, 0, 0, 0))
        im.thumbnail(size, resample=True)
        offset = ((size[0] - im.size[0]) / 2,
                  (size[1] - im.size[1]) / 2)
        box = offset + (im.size[0] + offset[0],
                        im.size[1] + offset[1])
        tn.paste(im, box)
        tn.save(tn_path)

    return tn_path
    
#
# IMAGE CLASS
#

class image(object):
    """
    manipulable image object

    This class is basically a PIL abstraction, with a different
    method model: each method is an action modifying the object.
    Nothing is written to a file until explicitly asked.
    """

    im = None

    def __init__(self, src=None):
        """
        initialize an image from a file

        @param src: origin image, can be
          - a string : it is read as an image file name
          - a  PIL image object : it is used as the internal image structure
          - omitted : the image is initialy empty
        """
        if isinstance(src, PIL.Image.Image):
            self.im = src
        if isinstance(src, str):
            _deinterlace_png(src)
            self.im = PIL.Image.open(src)

    def __getattr__(self, attr):
        """
        direct access to some image attributes
        """
        if attr == 'size':
            return self.im.size
        else:
            return object.__getattribute__(self, attr)

    def save(self, fname):
        """
        save the image file

        @param fname: file name
        """
        # TODO handle optional arguments
        # TODO handle external TIFF compression
        self.im.save(fname)
        return fname

    def crop(self, box):
        """
        crop the image, in-place

        @param box: crop coordinates (x0, y0, x1, x1)
        """
        self.im = self.im.crop(box)
        return self

    def resize(self, size, method="bicubic"):
        """
        resize the image, in-place

        @param size: target size, given as an integer number of pixels,
        a float scale ratio, or a pair (width, height)
        @param method: interpolation method, can be "nearest",
                       "bilinear", "bicubic" or "antialias"
        """
        if isinstance(size, int):
            # size is a number of pixels -> convert to a float scale
            size = (float(size) / (self.im.size[0] * self.im.size[1])) ** .5

        if isinstance(size, float):
            # size is a scale -> convert to (x, y)
            size = (int(self.im.size[0] * size),
                    int(self.im.size[1] * size))

        try:
            method_kw = {"nearest" : PIL.Image.NEAREST,
			 "bilinear" : PIL.Image.BILINEAR,
                         "bicubic" : PIL.Image.BICUBIC,
			 "antialias" : PIL.Image.ANTIALIAS}[method]
        except KeyError:
            raise KeyError('method must be "nearest", "bilinear", "bicubic" or "antialias"')

        self.im = self.im.resize(size, method_kw)
        return self

    def convert(self, mode):
        """
        convert the image pixel array to another numeric type

        @param mode: the data type, can be '1x8i' (8bit gray) or '3x8i'
        (RGB)
        """
        # TODO handle other modes (binary, 16bits, 32bits int/float)
        # TODO rename param to dtype
        try:
            mode_kw = {'1x8i' : 'L',
                       '3x8i' : 'RGB'}[mode]
        except KeyError:
            raise KeyError('mode must be "1x8i" or "3x8i"')
        self.im = self.im.convert(mode_kw)
        return self

    def split(self, nb, margin=0, fname=None):
        """
        split an image vertically into tiles tiles,
        with an optional margin

        @param nb: number of strips
        @param margin: overlapping margin, default 0

        @return: list of images if fname is not specified,
        or a list of filenames where these images are saved
        """
        # TODO refactor, don't automatically save
        
        try:
            assert (nb >= 2)
        except AssertionError:
            raise ValueError('nb must be >= 2')

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
        read some tiles and join them vertically

        @param tiles: a list of images
        @param margin: overlapping margin, default 0
        """
        # compute the full image size
        xmax = tiles[0].im.size[0]
        ymax = 0
        for tile in tiles:
            assert (tile.im.size[0] == xmax)
            ymax += tile.im.size[1] - 2 * margin
        ymax += 2 * margin

        self.im = PIL.Image.new(tiles[0].im.mode, (xmax, ymax))

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

    def draw_line(self, coords, color="white"):
        """
        draw a line in an image

        @param coords: a list of coordinates [(x1,y1), (x2,y2), ...]
        @param color: an optional color code, following PIL syntax[1],
        default white
        @return: the image object

        [1]http://www.pythonware.com/library/pil/handbook/imagedraw.htm
        """
        draw = PIL.ImageDraw.Draw(self.im)
        draw.line(coords, fill=color)
        del draw
        return self

    def draw_grid(self, step, offset=(0, 0), color="white"):
        """
        draw a grid on the input image

        @param step: the grid step
        @param offset: the grid offset
        @param color: the grid color
        @return: the image object
        """
        assert (step > 0)
        # vertical lines
        y = self.im.size[1]
        for x in range(offset[0], self.im.size[0], step):
            self.draw_line(((x, 0), (x, y)), color)
        # horizontal lines
        x = self.im.size[0]
        for y in range(offset[1], self.im.size[1], step):
            self.draw_line(((0, y), (x, y)), color)
        return self

    def draw_cross(self, position, size=2, color="white"):
        """
        draw a cross on the input image

        @param position: the cross center position
        @param size: the cross size (length of each branch)
        @param color: the grid color
        @return: the image object
        """
        assert (size >= 0)
        (x, y) = position
        # vertical line
        self.draw_line(((x, y - size), (x, y + size)), color=color)
        # horizontal
        self.draw_line(((x - size, y), (x + size, y)), color=color)
        return self

    def invert(self):
        """
        invert the image colors
        @return: the inverted image object
        """
        self.im = PIL.ImageOps.invert(self.im)
        return self
