#!/usr/bin/env python
#
# Adds a grayscale scale with a legend of minval maxval
# Does not alter the image, just adds the scale.
#
# ./addscale.py INFILE.png OUTFILE.png minval maxval
#  


def image_add_note(im, textstring, color=255):
   """
   add a note on the upper left corner of the image
   """
   import ImageDraw
   draw = ImageDraw.Draw(im)
   sz = draw.textsize(textstring)
   draw.rectangle(((0,0), sz) ,fill=0) 
   draw.text((0,0), textstring, fill=color)
   del draw
   return im



def image_add_scale(im, imrange, color=255, Rwidth=128):
   """
   add a scale on the upper left corner of the image
   """
   if im.size[0] > 128:
      import ImageDraw
      draw = ImageDraw.Draw(im)
      sz = draw.textsize(str(imrange))
      for i in range(0,3):
         DIF=imrange[1]-imrange[0]
         draw.text(  (int(i*(Rwidth-18)/2),sz[1]) , "%.1f" % (float(i)/2*DIF + imrange[0]), fill=0)
      for i in range(0,Rwidth):
         draw.rectangle(((i,0), (i,sz[1])) ,fill=int (color*i/Rwidth) ) 
      del draw
   return im



import sys


if len(sys.argv) > 3:
   outFile  = sys.argv[1]
   minval  = float(sys.argv[2])
   maxval  = float(sys.argv[3])
else: 
   print "Incorrect syntax, use:"
   print '  > ' + sys.argv[0] + " OUTSCALE.png minval maxval"
   sys.exit(1)


import Image 
im=Image.new('I', [280,22], 255)

textstring = 'RANGE:['+str(minval) +','+ str(maxval)+']'
#im=image_add_note(im,textstring,color=65535)
im=image_add_scale(im,(minval,maxval),color=255,Rwidth=256)
im.save(outFile)

sys.exit(0)

