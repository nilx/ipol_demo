"""
piecewise affine equalization ipol demo web app
"""

from lib import base_app, build, http, image
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time
import PIL.Image
import PIL.ImageDraw

class app(base_app):
    """ piecewise affine equalization app """

    title = "Color and Contrast Enhancement by Controlled Piecewise Affine Histogram Equalization"
    xlink_article = 'http://www.ipol.im/pub/art/2012/lps-pae/'

    input_nb = 1
    input_max_pixels = 700 * 700 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = False

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() and input_xxx() are generic
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True
 
    def build(self):
        """ 
        program build/update
        """
        # store common file path in variables
        tgz_url = "http://www.ipol.im/pub/art/2012/lps-pae/piecewise_eq.tgz"
        tgz_file = self.dl_dir + "piecewise_eq.tgz"
        progs = ["piecewise_equalization"]
        src_bin = dict([(self.src_dir + 
                         os.path.join("piecewise_eq", prog),
                         self.bin_dir + prog)
                        for prog in progs])
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if any dest file is missing, or too old
        if all([(os.path.isfile(bin_file)
                 and ctime(tgz_file) < ctime(bin_file))
                for bin_file in src_bin.values()]):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the programs
            build.run("make -j4 -C %s %s"
                      % (self.src_dir + "piecewise_eq", 
                      " ".join(progs)),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for (src, dst) in src_bin.items():
		#print "copy %s to %s" % (src, dst) 
                shutil.copy(src, dst)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)

        return


    #
    # PARAMETER HANDLING
    #
    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, s1="0", s2="3.0"):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

        return self.tmpl_out("params.html", msg=msg, s1=s1, s2=s2)

    @cherrypy.expose
    @init_app
    def wait(self, s1="0", s2="3.0"):
        """
        params handling and run redirection
        """
        # save the parameters
        try:
            self.cfg['param'] = {'s1' : float(s1), 
				 's2' : float(s2)}
            self.cfg.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        # read the parameters
        s1 = self.cfg['param']['s1']
        s2 = self.cfg['param']['s2']
        # run the algorithm
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(s1, s2, stdout=stdout, timeout=self.timeout)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="uploaded image")
            ar.add_file("input_0.png", info="original image")
            ar.add_file("output_1_N2.png", info="result image 1 N=2 (RGB)")
            ar.add_file("output_2_N2.png", info="result image 2 N=2 (I)")
            ar.add_file("output_1_N3.png", info="result image 1 N=3 (RGB)")
            ar.add_file("output_2_N3.png", info="result image 2 N=3 (I)")
            ar.add_file("output_1_N4.png", info="result image 1 N=4 (RGB)")
            ar.add_file("output_2_N4.png", info="result image 2 N=4 (I)")
            ar.add_file("output_1_N5.png", info="result image 1 N=5 (RGB)")
            ar.add_file("output_2_N4.png", info="result image 2 N=5 (I)")
            ar.add_file("output_1_N10.png", info="result image 1 N=10 (RGB)")
            ar.add_file("output_2_N10.png", info="result image 2 N=10 (I)")
            ar.add_file("output_1_HE.png", info="result image 1 HE (RGB)")
            ar.add_file("output_2_HE.png", info="result image 2 HE (I)")
            ar.add_info({"smin": s1})
            ar.add_info({"smax": s2})
            ar.save()

        return self.tmpl_out("run.html")

    def drawtransformImages(self, imname0, imname1, channel, scale, fname=None):
        """
        Compute transform that converts values of image 0 to values of image 1, for the specified channel
        Images must be of the same size
        """
                
        #load images
        im0 = PIL.Image.open(imname0)
        im1 = PIL.Image.open(imname1)
    
        #check image size
        if im0.size != im1.size:
            raise ValueError("Images must be of the same size")
        
        # check image mode
        if im0.mode not in ("L", "RGB"):
            raise ValueError("Unsuported image mode for histogram equalization")
        if im1.mode not in ("L", "RGB"):
            raise ValueError("Unsuported image mode for histogram equalization")

        #load image values
        rgb2I = (0.333333, 0.333333, 0.333333, 0,
                 0, 0, 0, 0,
                 0, 0, 0, 0 )
        rgb2r = (1, 0, 0, 0,
                 0, 0, 0, 0,
                 0, 0, 0, 0 )
        rgb2g = (0, 1, 0, 0,
                 0, 0, 0, 0,
                 0, 0, 0, 0 )
        rgb2b = (0, 0, 1, 0,
                 0, 0, 0, 0,
                 0, 0, 0, 0 )

        if im0.mode == "RGB":
            if channel == "I":
                # compute gray level image: I = (R + G + B) / 3
                im0L = im0.convert("L", rgb2I)
            elif channel == "R":
                im0L = im0.convert("L", rgb2r)
            elif channel == "G":
                im0L = im0.convert("L", rgb2g)
            else:
                im0L = im0.convert("L", rgb2b)
            h0 = im0L.histogram()
        else: 
            #im0.mode == "L":
            h0 = im0.histogram()

        if im1.mode == "RGB":
            if channel == "I":
                # compute gray level image: I = (R + G + B) / 3
                im1L = im1.convert("L", rgb2I)
            elif channel == "R":
                im1L = im1.convert("L", rgb2r)
            elif channel == "G":
                im1L = im1.convert("L", rgb2g)
            else:
                im1L = im1.convert("L", rgb2b)
            h1 = im1L.histogram()
        else:
            #im1.mode == "L":
            h1 = im1.histogram()

        #compute correspondences between image values 
        T = [i for i in range(256)]
        hacum0 = [0 for i in range(256)]
        hacum1 = [0 for i in range(256)]
        hacum0[0] = h0[0]
        hacum1[0] = h1[0]
        for i in range(1, 256):
            hacum0[i] = h0[i]+hacum0[i-1]
            hacum1[i] = h1[i]+hacum1[i-1]

        jprev = 0
        for i in range(0, 256):
            href = hacum0[i]
            j = jprev
            #while (j < 256) and (hacum1[j] <= href):
            while (j < 256) and (hacum1[j] < href):
                j += 1
            #if j > 0:
                #j-=1
            T[i] = j
            jprev = j

        #draw correspondences
        size = (256/scale, 256/scale)
        imout = PIL.Image.new('RGB', size, (255, 255, 255))
        draw = PIL.ImageDraw.Draw(imout)

        x1 = 0
        y1 = 0
        for k in range(256):
            if (h0[k] != 0):
                x2 = k
                y2 = T[k]
                draw.line([(x1/scale, 255/scale-y1/scale), 
                           (x2/scale, 255/scale-y2/scale)], fill=(0, 255, 0))
                x1 = x2
                y1 = y2
        draw.line([(x1/scale, 255/scale-y1/scale), (255/scale, 0)], 
                  fill=(0, 255, 0))

        #draw reference (red line)
        draw.line([(0, 255/scale), (255/scale, 0)], fill=(255, 0, 0))

        if fname != None:
            #draw stored transformation
            data = open(fname)
            lines = [line.strip() for line in data]
            N = int(lines[0])
        
            offset = {"I":0, "R":N+3, "G":2*(N+3), "B":3*(N+3)}
        
            for k in range (1+offset[channel], N+2+offset[channel]):
                line = lines[k].split()
                x1 = int(float(line[0]))/scale
                y1 = 255/scale-int(float(line[2]))/scale
                #if y1 < 0:
                    #y1 = 0
                x2 = int(float(line[1]))/scale
                y2 = 255/scale-int(float(line[3]))/scale
                #if y2 < 0:
                    #y2 = 0
                draw.ellipse((x1-3, y1-3, x1+3, y1+3), fill=(0, 0, 255))
                draw.ellipse((x2-3, y2-3, x2+3, y2+3), fill=(0, 0, 255))
                draw.line([(x1, y1), (x2, y2)], fill=(0, 0, 255))
                if k == 1+offset[channel]:
                    draw.line([(0, 255/scale), (x1, y1)], fill=(0, 0, 255))
                if k == N+1+offset[channel]:
                    draw.line([(x2, y2), (255/scale, 0)], fill=(0, 0, 255))
            data.close()

        #return result
        return imout


    def drawtransform(self, imname0, imname1, fname, scale, hmargin, type):

        if type == 'I':
            imR = self.drawtransformImages(imname0, imname1, 'R', scale)
            imG = self.drawtransformImages(imname0, imname1, 'G', scale)
            imB = self.drawtransformImages(imname0, imname1, 'B', scale)
            imI = self.drawtransformImages(imname0, imname1, 'I', scale, fname)
        else:
            #type='RGB'
            imR = self.drawtransformImages(imname0, imname1, 'R', scale, fname)
            imG = self.drawtransformImages(imname0, imname1, 'G', scale, fname)
            imB = self.drawtransformImages(imname0, imname1, 'B', scale, fname)
            imI = self.drawtransformImages(imname0, imname1, 'I', scale)    
    
        im = PIL.Image.new('RGB', (imR.size[0], 4*imR.size[1]+3*hmargin), 
                           (255, 255, 255))
        im.paste(imR, (0, 0, imR.size[0], imR.size[1]))
        im.paste(imG, (0, hmargin+imR.size[1], imR.size[0], 
                       hmargin+2*imR.size[1]))
        im.paste(imB, (0, 2*hmargin+2*imR.size[1], imR.size[0], 
                       2*hmargin+3*imR.size[1]))
        im.paste(imI, (0, 3*hmargin+3*imR.size[1], imR.size[0], 
                       3*hmargin+4*imR.size[1]))

        return im



    def run_algo(self, s1, s2, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        N = 2
        p1 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N),
                           'input_0.png', 'output_1_N2.png', 'output_2_N2.png', 
                           'pointsN2.txt'], stdout=None, stderr=None)

        N = 3
        p2 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N), 
                            'input_0.png', 'output_1_N3.png', 'output_2_N3.png',
                            'pointsN3.txt'], stdout=None, stderr=None)

        N = 4
        p3 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N),
                            'input_0.png', 'output_1_N4.png', 'output_2_N4.png',
                            'pointsN4.txt'], stdout=None, stderr=None)

        N = 5
        p4 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N),
                            'input_0.png', 'output_1_N5.png', 'output_2_N5.png',
                            'pointsN5.txt'], stdout=None, stderr=None)

        N = 10
        p5 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N),
                            'input_0.png', 'output_1_N10.png', 'output_2_N10.png',
                            'pointsN10.txt'], stdout=None, stderr=None)

        N = -1
        p6 = self.run_proc(['piecewise_equalization', str(s2), str(s1), str(N),
                            'input_0.png', 'output_1_HE.png', 'output_2_HE.png',
                            'pointsHE.txt'], stdout=None, stderr=None)

        self.wait_proc([p1, p2, p3, p4, p5, p6], timeout)


        #Compute histograms of images
        im0 = image(self.work_dir + 'input_0.png')
        im1N2 = image(self.work_dir + 'output_1_N2.png')
        im1N3 = image(self.work_dir + 'output_1_N3.png')
        im1N4 = image(self.work_dir + 'output_1_N4.png')
        im1N5 = image(self.work_dir + 'output_1_N5.png')
        im1N10 = image(self.work_dir + 'output_1_N10.png')
        im1HE = image(self.work_dir + 'output_1_HE.png')
        im2N2 = image(self.work_dir + 'output_2_N2.png')
        im2N3 = image(self.work_dir + 'output_2_N3.png')
        im2N4 = image(self.work_dir + 'output_2_N4.png')
        im2N5 = image(self.work_dir + 'output_2_N5.png')
        im2N10 = image(self.work_dir + 'output_2_N10.png')
        im2HE = image(self.work_dir + 'output_2_HE.png')
        #compute maximum of histogram values
        maxH = im0.max_histogram(option="all")
        #draw all the histograms using the same reference maximum
        im0.histogram(option="all", maxRef=maxH)
        im0.save(self.work_dir + 'input_0_hist.png')
        im1N2.histogram(option="all", maxRef=maxH)
        im1N2.save(self.work_dir + 'output_1_N2_hist.png')
        im1N3.histogram(option="all", maxRef=maxH)
        im1N3.save(self.work_dir + 'output_1_N3_hist.png')
        im1N4.histogram(option="all", maxRef=maxH)
        im1N4.save(self.work_dir + 'output_1_N4_hist.png')
        im1N5.histogram(option="all", maxRef=maxH)
        im1N5.save(self.work_dir + 'output_1_N5_hist.png')
        im1N10.histogram(option="all", maxRef=maxH)
        im1N10.save(self.work_dir + 'output_1_N10_hist.png')
        im1HE.histogram(option="all", maxRef=maxH)
        im1HE.save(self.work_dir + 'output_1_HE_hist.png')
        im2N2.histogram(option="all", maxRef=maxH)
        im2N2.save(self.work_dir + 'output_2_N2_hist.png')
        im2N3.histogram(option="all", maxRef=maxH)
        im2N3.save(self.work_dir + 'output_2_N3_hist.png')
        im2N4.histogram(option="all", maxRef=maxH)
        im2N4.save(self.work_dir + 'output_2_N4_hist.png')
        im2N5.histogram(option="all", maxRef=maxH)
        im2N5.save(self.work_dir + 'output_2_N5_hist.png')
        im2N10.histogram(option="all", maxRef=maxH)
        im2N10.save(self.work_dir + 'output_2_N10_hist.png')
        im2HE.histogram(option="all", maxRef=maxH)
        im2HE.save(self.work_dir + 'output_2_HE_hist.png')

        #compute value transforms
        scale = 2
        hmargin = 10
        
        imG0 = self.drawtransform(self.work_dir + 'input_0.png', 
                                  self.work_dir + 'input_0.png',
                                  None,
                                  scale, hmargin, 'I')
        imG0.save(self.work_dir + 'identity.png')
        imG2 = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_1_N2.png',
                                        self.work_dir + 'pointsN2.txt',
                                        scale, hmargin, 'I')
        imG2.save(self.work_dir + 'pointsN2.png')
        imG3 = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_1_N3.png',
                                        self.work_dir + 'pointsN3.txt',
                                        scale, hmargin, 'I')
        imG3.save(self.work_dir + 'pointsN3.png')
        imG4 = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_1_N4.png',
                                        self.work_dir + 'pointsN4.txt',
                                        scale, hmargin, 'I')
        imG4.save(self.work_dir + 'pointsN4.png')
        imG5 = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_1_N5.png',
                                        self.work_dir + 'pointsN5.txt',
                                        scale, hmargin, 'I')
        imG5.save(self.work_dir + 'pointsN5.png')
        imG10 = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_1_N10.png',
                                        self.work_dir + 'pointsN10.txt',
                                        scale, hmargin, 'I')
        imG10.save(self.work_dir + 'pointsN10.png')
        imGHE = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_1_HE.png',
                                        None,
                                        scale, hmargin, 'I')
        imGHE.save(self.work_dir + 'pointsHE.png')


        imRGB2 = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_2_N2.png',
                                        self.work_dir + 'pointsN2.txt',
                                        scale, hmargin, 'RGB')
        imRGB2.save(self.work_dir + 'pointsN2RGB.png')
        imRGB3 = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_2_N3.png',
                                        self.work_dir + 'pointsN3.txt',
                                        scale, hmargin, 'RGB')
        imRGB3.save(self.work_dir + 'pointsN3RGB.png')
        imRGB4 = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_2_N4.png',
                                        self.work_dir + 'pointsN4.txt',
                                        scale, hmargin, 'RGB')
        imRGB4.save(self.work_dir + 'pointsN4RGB.png')
        imRGB5 = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_2_N5.png',
                                        self.work_dir + 'pointsN5.txt',
                                        scale, hmargin, 'RGB')
        imRGB5.save(self.work_dir + 'pointsN5RGB.png')
        imRGB10 = self.drawtransform(self.work_dir + 'input_0.png', 
                                        self.work_dir + 'output_2_N10.png',
                                        self.work_dir + 'pointsN10.txt',
                                        scale, hmargin, 'RGB')
        imRGB10.save(self.work_dir + 'pointsN10RGB.png')
        imRGBHE = self.drawtransform(self.work_dir + 'input_0.png', 
                                          self.work_dir + 'output_2_HE.png',
                                          None,
                                          scale, hmargin, 'RGB')
        imRGBHE.save(self.work_dir + 'pointsHERGB.png')
       
       
        
	
    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        # read the parameters
        s1 = self.cfg['param']['s1']
        s2 = self.cfg['param']['s2']
        sizeY = image(self.work_dir + 'input_0.png').size[1]
        sizeYhist = image(self.work_dir + 'input_0_hist.png').size[1]
        # add 20 pixels to the histogram size to take margin into account
        sizeYmax = max(sizeY, sizeYhist+60)

        return self.tmpl_out("result.html", s1=s1, s2=s2,
                             sizeY="%i" % sizeYmax)



