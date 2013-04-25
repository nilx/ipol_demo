#!/usr/bin/python
# -*- coding: utf-8 -*-

import Image, ImageDraw
from math import cos, sin, pi, floor
from os import system, remove

from numpy import loadtxt, ones, argmin, histogram, multiply




def draw_matches(pairs, image1, image2, imout):
    """
    Map keypoints and matches
        
        expected format for pairs is :
          x1 y1 sigma1 theta1 x2 y2 sigma2 theta2
        
    """
    radfact = 1
    # image1 and image2 put side by side
    image1 = Image.open(image1)
    image2 = Image.open(image2)
    [w1, h1] = image1.size
    [w2, h2] = image2.size
    ofst = w1+max(w1, w2)/10   # width of empty band between the two images put side by side
    [w, h] = [ofst+w2, max(h1, h2)]
    #image = Image.new('RGB',[w,h],"white")
    image = Image.new('RGBA', [w, h])
    image.paste(image1, (0, 0))
    image.paste(image2, (ofst, 0))
    draw = ImageDraw.Draw(image)
    
    # Matching pairs
    f = file(pairs)
    for pair in f:
        
        # read pair
        pair = pair.split()
        [x1, y1, sigma1, theta1, x2, y2, sigma2, theta2] = [float(x) for x in pair[0:8]]
        
        if (max(x1, y1, sigma1, x2, y2, sigma2) > w):
            break
        
        # draw matches
        draw.line((y1, x1, y2+ofst, x2), fill=(255, 0, 0))
        
        # draw keypoints in image 1
        r = radfact*sigma1
        coord = [int(x) for x in (y1-r, x1-r, y1+r, x1+r)]
        draw.arc(coord, 0, 360, fill=(0, 255, 0))  # detection size (green circle)
        draw.line([(y1, x1), (y1+r*sin(theta1), x1+r*cos(theta1))], fill=(0, 255, 0)) # reference orientation (blue arrow)
        
        # draw keypoints in image 2
        r = radfact*sigma2
        coord = [int(x) for x in (y2+ofst-r, x2-r, y2+ofst+r, x2+r)]
        draw.arc(coord, 0, 360, fill=(0, 255, 0)) 
        draw.line([(y2+ofst, x2), (y2+ofst+r*sin(theta2), x2+r*cos(theta2))], fill=(0, 255, 0))
        
    del draw
    image.save(imout)






def draw_rotatedbox(draw, x, y, radius, angle, colorvec):
    xA = int(x + radius*( (-1)*cos(angle)-(+1)*sin(angle)) )
    yA = int(y + radius*( (-1)*sin(angle)+(+1)*cos(angle)) )
    xB = int(x + radius*( (+1)*cos(angle)-(+1)*sin(angle)) )
    yB = int(y + radius*( (+1)*sin(angle)+(+1)*cos(angle)) )
    xC = int(x + radius*( (+1)*cos(angle)-(-1)*sin(angle)) )
    yC = int(y + radius*( (+1)*sin(angle)+(-1)*cos(angle)) )
    xD = int(x + radius*( (-1)*cos(angle)-(-1)*sin(angle)) )
    yD = int(y + radius*( (-1)*sin(angle)+(-1)*cos(angle)) )
    draw.line((yA, xA, yB, xB), fill=colorvec)
    draw.line((yB, xB, yC, xC), fill=colorvec)
    draw.line([(yC, xC), (yD, xD)], fill=colorvec)
    draw.line([(yA, xA), (yD, xD)], fill=colorvec)    
    
    



def draw_one_match(pairdata, image1, image2, d, lambda_ori, lambda_descr, n_hist, imout):
    """
     Map a keypoint in one image along its best matches in the second image
        
        Expected format for pairs is :
              x1 y1 sigma1 theta1 x2 y2 sigma2 theta2
        - d : length of the keydata structure 
        
        - n_hist : the feature vector is composed of n_hist X n_hist weighted histograms.
        - lambda_descr : the patch used for the description has a width of 
                       2*lambda_descr*sigma
        
        - lambda_ori : the patch used for reference orientation attribution has a width of
                       2*3*lambda_ori*sigma
                  
    """
    
    # image1 and image2 put side by side
    image1 = Image.open(image1)
    image2 = Image.open(image2)
    [w1, h1] = image1.size
    [w2, h2] = image2.size
    ofst = w1+max(w1, w2)/10   # width of empty band between the two images put side by side
    [w, h] = [ofst+w2, max(h1, h2)]
    image = Image.new('RGBA', [w, h])
    draw = ImageDraw.Draw(image)
  

    [x1,  y1,  sigma1,  theta1]  = [float(x) for x in pairdata[0:4]]
    [x2a, y2a, sigma2a, theta2a] = [float(x) for x in pairdata[d:d+4]]
    [x2b, y2b, sigma2b, theta2b] = [float(x) for x in pairdata[2*d:2*d+4]]
    #[o1,s1]   = pairdata[4+v:6+v]
    #[o2a,s2a] = pairdata[4+v+d:6+v+d]
    #[o2b,s2b] = pairdata[4+v+2*d:6+v+2*d]
    
    # draw matches
    draw.line((y1, x1, y2a+ofst, x2a), fill=(255, 0, 0))

    # draw 'description patches' and 'reference orientation' arrows
    # keypoint
    r = (1+1/n_hist)*lambda_descr*sigma1 
    draw_rotatedbox(draw, x1, y1, r, theta1,(255, 140, 0))  
    draw.line([(y1, x1),(y1+r*sin(theta1), x1+r*cos(theta1))], fill=(255, 140, 0))  
    # nearest neighbor
    r = (1+1/n_hist)*lambda_descr*sigma2a
    draw_rotatedbox(draw, x2a, ofst+y2a, r, theta2a,(255, 140, 0))  
    draw.line([(ofst+y2a, x2a),(ofst+y2a+r*sin(theta2a), x2a+r*cos(theta2a))], fill=(255, 140, 0))
    # second nearest neighbor
    r = (1+1/n_hist)*lambda_descr*sigma2b
    draw_rotatedbox(draw, x2b, ofst+y2b, r, theta2b,(255, 140, 0))   
    draw.line([(ofst+y2b, x2b),(ofst+y2b+r*sin(theta2b), x2b+r*cos(theta2b))], fill=(255, 140, 0))
    
    # draw 'orientation' patches
    r = 3*lambda_ori*sigma1
    draw_rotatedbox(draw, x1, y1, r, 0,(155, 140, 200))   # keypoint
    r = 3*lambda_ori*sigma2a
    draw_rotatedbox(draw, x2a, y2a+ofst, r, 0,(155, 140, 200))   # nearest neighbor
    r = 3*lambda_ori*sigma2b
    draw_rotatedbox(draw, x2b, y2b+ofst, r, 0 ,(155, 140, 200))   # second nearest neighbor
    
    del draw
    image.save(imout)


def draw_keys(keys, image, imout):
    """
    Map keypoints without orientation
      expected format for pairs is :
        (x y sigma...)
       
        @param keys  : ASCII file  [x y sigma ...]
        @param image : input image
        @param imout : output image
        
    """
    radfact = 1
    temp = Image.open(image)
    image = Image.new('RGB', temp.size)
    image.paste(temp,(0, 0))
    draw = ImageDraw.Draw(image)
    f = file(keys)
    for key in f:
        key = key.split()
        
     #  [y,x,sigma] = map(float,key[0:3])
        [x, y, sigma] = [float(x) for x in key[0:3]]
    
    #    if (max(x,y,sigma) > image.size[0]:
    #        print "out " +str(x)+str(y)+str(sigma)
    #        print '0:  ' + str(image.size[0])
    #        print '1:  ' + str(image.size[1])
    #        break
        
        
        r = radfact*sigma
        coord = [int(x) for x in (y-r, x-r, y+r, x+r)]
        draw.arc(coord, 0, 360, fill=(0, 255, 0))
        
    del draw
    image.save(imout)
    return 1


def draw_keys_oriented(keys, image, imout):
    """
    Map keypoints without orientation
      expected format for pairs is :
      (x y sigma theta...)
    """
    radfact = 1
    temp = Image.open(image)
    image = Image.new('RGB', temp.size)
    image.paste(temp,(0, 0))
    draw = ImageDraw.Draw(image)
    f = file(keys)
    for key in f:
        key = key.split()
        [x, y, sigma, theta] = [float(x) for x in key[0:4]]
        r = radfact*sigma
        coord = [int(x) for x in (y-r, x-r, y+r, x+r)]
        draw.arc(coord, 0, 360, fill=(0, 255, 0))
        draw.line([(y, x),(y+r*sin(theta), x+r*cos(theta))], fill=(0, 255, 0))
    del draw
    image.save(imout)
    return 1





    
def find_nearest_keypoint(keys, x, y):
    """
    Find the nearest keypoint in the list
    Output the corresponding line from 'keys' Or 'pairs'
       expected format
       (x y ...)
       (x y sigma theta descr[] ori[] oct sca)
 
    """
    X = loadtxt(keys, usecols=(0,))
    Y = loadtxt(keys, usecols=(1,))
    X0 = float(x)*ones(len(X))
    Y0 = float(y)*ones(len(Y))
    idx = argmin((X-X0)*(X-X0) + (Y-Y0)*(Y-Y0))  # minimum of Euclidean distance
    f = file(keys)
    for i in range(idx):
        f.readline()
        i = i # mape pylint happy
    return [float(x) for x in f.readline().split()]


def illustrate_pair(pairdata, n_bins, t, n_hist, n_ori, label):
    """
    Plot weighted histograms
    Plot orientation histogram
    expected format in the same line 
       (x,y,sigma,theta, o,s, descr, orihist) for keypoint 1 ..
          .. (x,y,sigma,theta, o,s, descr, orihist) for keypoint 2a ..
                .. (x,y,sigma,theta, o,s, descr, orihist) for keypoint 2b ..
                 
    """
    d = 6+n_hist*n_hist*n_ori+n_bins
    keydata1  = pairdata[0:d]
    keydata2a = pairdata[d:2*d] 
    keydata2b = pairdata[2*d:3*d]    
    illustrate_keypoint(keydata1 , n_bins, t, n_hist, n_ori, label+'detail_im1')
    illustrate_keypoint(keydata2a, n_bins, t, n_hist, n_ori, label+'detail_im2a')
    illustrate_keypoint(keydata2b, n_bins, t, n_hist, n_ori, label+'detail_im2b')
    return 1




def illustrate_keypoint(keydata, n_bins, t, n_hist, n_ori, label):
    """
    Plot weighted histograms
    Plot orientation histogram
     (? Draw descriptor grid on the image ?)
    Input :
        keydata : tab of float
     expected keydata format : 
       x,y,sigma,theta, descr, o,s, orihist
    
    """
    dim = n_hist*n_hist*n_ori
    theta   = keydata[3]
    descr   = keydata[4:4+dim]  # feature vector
    orihist = keydata[6+dim:6+dim+n_bins] # orientation histogram
    plot_featurevec(descr, label+'_weighted_hists', n_hist, n_ori)
    plot_orientation_hist(orihist, theta, label+'_ori_hist', n_bins, t)
#    
#    #experimental
#    lambda_descr = 6
#    lambda_ori = 1.5
#    plot_field_ori(label+'_gradient_field_descr.t',(1+1/n_hist)*lambda_descr)
#    plot_field_ori(label+'_gradient_field_ori.t',3*lambda_ori)
#    
    return 1
    
    
def hsv_2_hexrgb( h, s, v ):
    '''
    Conversion HSV to RGB converted in exa
       0 <= h < 360.
       0 <= s < 1.
       0 <= v < 1.
    '''
    if h < 60.:
        r = v
        g = v*(1-s*(1+floor(h/60.)-h/60.))
        b = v*(1-s)
    elif h < 120.:
        r = v*(1-s*(h/60.-floor(h/60.)))
        g = v
        b = v*(1-s)
    elif h < 180.:
        r = v*(1-s)
        g = v
        b = v*(1-s*(1+floor(h/60.)-h/60.))
    elif h < 240.:
        r = v*(1-s)
        g = v*(1-s*(h/60.-floor(h/60.)))
        b = v
    elif h < 300.:
        r = v*(1-s*(1+floor(h/60.)-h/60.))
        g = v*(1-s)
        b = v
    elif h < 360:
        r = v
        g = v*(1-s)
        b = v*(1-s*(h/60-floor(h/60.)))
    elif h == 360:
        r = v
        g = v*(1-s)
        b = v*(1-s)
    return "#%02X%02X%02X" % (255*r, 255*g, 255*b) 
    
    
  

def plot_featurevec(descr, label, n_hist, n_ori):
    """
    gnuplot wrapper
     input : feature vector of n_hist*n_hist*n_ori coefficients in one line
     output : png? image, its name is output
     
     note : creates 2 temporary files:
            - plot_featurevec.gnu (gnuplot script)
            - featurevec.data (reformatted feature vector)
    
    """   
    data = open(label+'_reformated.data','w')
    # Reformatting data.
    # one column per weighted histogram.
    for ang in range(n_ori):
        for ij in range(n_hist*n_hist):
            data.write('%10.3i'%(descr[ij*n_ori+ang]))
        data.write("\n") 
    data.close()
    # Write gnuplot script file.
    gnu = open(label+'plot_featurevec.gnu','w')
    gnu.write('set size ratio +1\n')
    gnu.write('set terminal pngcairo transparent size 300,300 \n')
    gnu.write("set output '"+label+".png'\n")
    gnu.write('set multiplot layout '+str(n_hist)+','+str(n_hist)+'\n')
    gnu.write('set style fill transparent solid 1 border -6.0 \n')
    gnu.write('unset xtics \nunset ytics\n')
    gnu.write('set yrange [0:265]\n')
    gnu.write('set lmargin 0 \nset rmargin 0 \nset bmargin 0 \nset tmargin 0\n')
   
    # palette definition 
    gnu.write('set palette defined (')
    N = 2*n_ori
    for q in range(N):
        gnu.write( str(float(q)/float(N)*n_ori)+' \''+hsv_2_hexrgb(float(q)/float(N)*360., 1, 1)+'\', ') 
    gnu.write( str(n_ori)+'  \''+hsv_2_hexrgb(360., 1, 1)+'\' )\n')
    gnu.write('set cbrange [0:%d]\n'%n_ori)
    
    gnu.write('unset colorbox\n') # to eliminate the color legend form the graph
    #gnu.write(' set palette model HSV \n')
    # plotting commands
    for ij in range(1, 1+n_hist*n_hist):
        gnu.write("plot '"+label+"_reformated.data' using ($0):"+str(ij)+":($0) with boxes notitle lc palette \n")
        # TODO ajouter le style ' lc rgb variable' qui prend un triplet rgb comme valeur des variables
    gnu.close()
    # Run gnuplot script and clean up.
    system('gnuplot '+label+'plot_featurevec.gnu')
    #remove('plot_featurevec.gnu')
    #remove(label+'_reformated.data')

    

def plot_orientation_hist(hist, theta, label, n_bins, t):
    """
    gnuplot wrapper
     input : - orientation histogram of n_bins coefficients
             - reference orientation selected
     parameters : -n_bins : number of bins
                  -t : threshold defining which local maximum is a reference orientation
                  
     output : png? image, its name is output
     
     note : creates 2 temporary files:
            - plot_orientation_hist.gnu (gnuplot script)
            - orientation_hist_REFORMATED.data (one column data file)
    """
    data = open(label+'_reformated.data','w')
    # Reformatting data - one column data file'''
    for k in range(n_bins):
        if (k%4 == 0):
            data.write('%10.3f  %i \n'%(hist[k], (k+0.5)*360/n_bins))
        else:
            data.write('%10.3f \n'%hist[k])
    data.close()

    
    # Gnuplot script file
    gnu = open(label+'plot_orientation_hist.gnu','w')
    gnu.write('set size ratio +1\n')
    gnu.write('set terminal pngcairo transparent size 512,512 \n')
    gnu.write("set output '"+label+".png'\n")
    #gnu.write('set lmargin 0 \nset rmargin 0 \nset tmargin 3\n')
    gnu.write('set style fill transparent solid 1 border -3.0\n')
       
    
    # Setting the palette
    gnu.write('set palette defined (')
    N = n_bins
    for q in range(N):
        gnu.write( str(float(q)/float(N)*n_bins)+' \''+hsv_2_hexrgb(float(q)/float(N)*360., 1, 1)+'\', ') 
    gnu.write( str(n_bins)+'  \''+hsv_2_hexrgb(360., 1, 1)+'\' )\n')
    gnu.write('set cbrange [0:%d]\n'%n_bins)
    
    
    gnu.write('unset colorbox\n')
    gnu.write('unset ytics\n')
    gnu.write('set yrange [0:1.2]\n')
    gnu.write('set xrange [-1:'+str(n_bins)+']\n')
    gnu.write('set trange [0:100]\n')
    gnu.write('set parametric \n')
    gnu.write("plot '"+label+"_reformated.data' using ($0):1:($0):xticlabel(2) with boxes notitle lc palette,")
    gnu.write("     t,"+str(t)+" lc rgb 'blue', ")
    gnu.write("    "+"%4.2f"%(theta*(float(n_bins)-0.5)/(2*pi))+",t lc rgb 'blue' lt 5;\n")
    #gnu.write("    "+"%4.2f"%(2*pi/(2*pi)*(n_bins-1))+",t lc rgb 'blue' lt 5;\n")
    
    gnu.close()
    system('gnuplot '+label+'plot_orientation_hist.gnu')
    #remove(label+'plot_orientation_hist.gnu')
    #remove(label+'_reformated.data')



def plot_field_ori(infile, radius):
    """
    gnuplot wrapper
    
     input : infile
              ASCII file with all samples considered
               [ x , y , dx ,dy , gradient norm ]
     parameters : radius
                   printed range of the descriptor
     
     note : creates a gnuplot script temporary files:
    """
    # Gnuplot script file
    gnu = open(infile+'draw.gnu','w')
    
    gnu.write('set terminal pngcairo transparent size 512,512\n ')
    gnu.write('set size ratio +1\n ')
    
    gnu.write("set output '"+infile+".png'\n ")
    gnu.write('unset key\n ')
    gnu.write('set border 0\n ')
    gnu.write('unset tics\n ')
    gnu.write('unset colorbox\n ')
    gnu.write('set xrange [%d:%d]\n'%(-radius, radius) )
    gnu.write('set yrange [%d:%d]\n'%(-radius, radius) )
    gnu.write("set palette defined (1 '#fffcf6', 2 '#fff7db', 3 '#fff4c2', 4 '#feecae', 5 '#f8ca8c', 6 '#f0a848', 7 '#c07860', 8 '#a86060', 9 '#784860', 10 '#604860') \n")
    gnu.write('plot "'+infile+'" u ($2-$4/10):(-$1+$3/10):($4/5):(-$3/5):5 with vectors head size  0.01,1,40  filled lc palette\n ')
    gnu.close()
    system('gnuplot '+infile+'draw.gnu')



def countdetections(keys, n_spo):
    """
    Accumulate the number of detection into a scale histogram
    """
    O = [int(x) for x in loadtxt(keys, usecols=(4,))]
    S = [int(x) for x in loadtxt(keys, usecols=(5,))]
    return multiply(O, n_spo)+S



def plot_detection_hists(keysBefore, keysAfter, label, n_oct, n_spo):
    """
    Plot the detections histograms for two sets of detections
      input:
        keysBefore : file of keypoint with extra information
        keysAfter
        
      output:
        image histogram, its name labelBefore
        image            its name labelAfter

     
     note : creates 2 temporary files:
            - plot_detection_hists.gnu (gnuplot script)
            - detection_hist_reformated.data (one column data file)
    """
    O = [int(x) for x in loadtxt(keysBefore, usecols=(4,))]
    S = [int(x) for x in loadtxt(keysBefore, usecols=(5,))]  
    histBefore = histogram(multiply(O, n_spo)+S, n_oct*n_spo)[0]
    O = [int(x) for x in loadtxt(keysAfter, usecols=(4,))]
    S = [int(x) for x in loadtxt(keysAfter, usecols=(5,))]
    histAfter = histogram(multiply(O, n_spo)+S, n_oct*n_spo)[0]
    
    data = open('detection_hist_reformated.data','w')
    # Reformatting data - one column per histogram'''
    for i in range(n_oct*n_spo):
        data.write('%i  %i\n'%(histBefore[i], histAfter[i]))
    data.close()
    # Gnuplot script file
    gnu = open('plot_detection_hists.gnu','w')
    gnu.write('set size ratio +1\n')
    gnu.write('set terminal png size 800,800 \n')
    gnu.write("set output '"+label+".png'\n")
    gnu.write('set style fill solid border -3.0\n')
    gnu.write('unset xtics\n')
    gnu.write('unset ytics\n')
    # gnu.write('set lmargin 0, rmargin 0, tmargin 0 \n')
    gnu.write("plot 'detection_hist_reformated.data' using 1:xtic(1) with boxes notitle,")
    gnu.write("     'detection_hist_reformated.data' using 0:1:1 with labels center offset 0,0.4 notitle,")   
    gnu.write("     'detection_hist_reformated.data' using 2:xtic(2) with boxes notitle,")
    gnu.write("     'detection_hist_reformated.data' using 0:2:2 with labels center offset 0,-0.4 notitle")    
    gnu.close()
    system('gnuplot plot_detection_hists.gnu')
    remove('plot_detection_hists.gnu')
    remove('detection_hist_reformated.data')
    
    
    




    


def keys2hist(keys_file, n_oct, n_spo):
    """
    Accumulate the number of detection into a scale histogram
    """
    f = open(keys_file,'r')
    hist = [0]*(n_oct*n_spo)
    for line in f:
        key = line.split()
        o = int(key[3])
        s = int(key[4])
        hist[o*n_spo+(s-1)] = hist[o*n_spo+(s-1)]+1
    return hist   



def keys_distribution(kA_file, kB_file, plotfilename, n_oct, n_spo):
    histA =  keys2hist(kA_file, n_oct, n_spo)
    histB =  keys2hist(kB_file, n_oct, n_spo)  
    histfile = open('hist.txt','w')
    for i in range(n_oct*n_spo):
        histfile.write(str(histA[i])+'    '+str(histB[i])+'\n')
    histfile.close()
    gpf = open('scriptA.gp','w')
    gpf.write('set size ratio +1\n')
    gpf.write('set terminal png size 600,600\n')
    gpf.write("set output '"+plotfilename+"'\n")
    gpf.write('set multiplot \n')
    gpf.write('set style fill solid 1.00 border -1 \n')
    gpf.write('unset ytics, xtics\n')
    gpf.write("plot 'hist.txt' using 1:xtic(1) with boxes notitle,")
    gpf.write("     'hist.txt' using 0:1:1 with labels center offset 0,0.4 notitle,")   
    gpf.write("     'hist.txt' using 2:xtic(2) with boxes notitle,")
    gpf.write("     'hist.txt' using 0:2:2 with labels center offset 0,-0.4 notitle") 
    gpf.close()
    system('gnuplot scriptA.gp')


   






    
#def draw_rotatedbox(draw,x,y,radius,angle,colorvec):
    #xA = int(x + radius*( (-1)*cos(angle)-(+1)*sin(angle)) )
    #yA = int(y + radius*( (-1)*sin(angle)+(+1)*cos(angle)) )
    #xB = int(x + radius*( (+1)*cos(angle)-(+1)*sin(angle)) )
    #yB = int(y + radius*( (+1)*sin(angle)+(+1)*cos(angle)) )
    #xC = int(x + radius*( (+1)*cos(angle)-(-1)*sin(angle)) )
    #yC = int(y + radius*( (+1)*sin(angle)+(-1)*cos(angle)) )
    #xD = int(x + radius*( (-1)*cos(angle)-(-1)*sin(angle)) )
    #yD = int(y + radius*( (-1)*sin(angle)+(-1)*cos(angle)) )
    #draw.line((yA,xA,yB,xB),fill=colorvec)
    #draw.line((yB,xB,yC,xC),fill=colorvec)
    #draw.line([(yC,xC),(yD,xD)],fill=colorvec)
    #draw.line([(yA,xA),(yD,xD)],fill=colorvec)
    
    
    
    
    
def draw_descriptorgrid(draw, x, y, sigma, ori, nhist, lambda_descr):
    # sigma = 4*sigma    
    # rgb coordinates at corners of the descriptor grid for linear interpolation in the RGB scale
    # A-B    red - blue
    # D-C    yellow - vert
    A = (255, 0, 0)
    B = (90, 90, 255)
    C = (200, 150, 122)
    D = (0, 255, 0)
    for i in range(-nhist/2, +nhist/2):
        for j in range(-nhist/2, +nhist/2):
            #print 'in '+str(i)
            # center of the area covered by an histogram
            Xcenter = (cos(ori)*(1./2 + i)-sin(ori)*(1./2 + j))*3*sigma
            Ycenter = (sin(ori)*(1./2 + i)+cos(ori)*(1./2 + j))*3*sigma
            #print 'XCENTER '+str(Xcenter)+' YCENTER '+str(Ycenter)
            #print 'GRID Centers Coordinates'+str((Xcenter,Ycenter))
            # color interpolation
            #print i
            alpha = (i - (-nhist/2))/float(nhist)
            beta = (j - (-nhist/2))/float(nhist)
            #print 'alpha '+str(alpha)
            #print 'beta '+str(beta)
            colorvec = tuple([int(round((1-alpha)*(1-beta)*A[k]+(1-alpha)*beta*B[k] + alpha*(1-beta)*C[k] + alpha*beta*D[k])) for k in range(3)])
            #print 'COLORVEC'+str(colorvec)
            
            draw_rotatedbox(draw, x+Xcenter, y+Ycenter, lambda_descr/nhist*sigma, +ori, colorvec)
    radius = 2*lambda_descr*(nhist+1)/nhist*sigma
    draw.line([(y, x),(y+radius*sin(ori), x+radius*cos(ori))], fill=(0, 255, 0))

