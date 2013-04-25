"""
IPOL SIFT
"""

from lib import base_app, build, http
from lib.misc import app_expose, ctime
from lib.base_app import init_app
from cherrypy import TimeoutError
import cherrypy
import os.path
import shutil

from .lib_demo_sift import draw_keys, draw_keys_oriented, \
    draw_matches, find_nearest_keypoint, illustrate_pair, \
    draw_one_match, Image

class app(base_app):
    """ demo app """
    title = "The Anatomy of the SIFT Method"
    input_nb = 2
    input_max_pixels = None
    input_max_method = 'zoom'
    input_dtype = '1x8i'
    input_ext = '.png'
    is_test = False

    xlink_article = "http://www.ipol.im/pub/pre/82/"
    xlink_src = "http://www.ipol.im/pub/pre/82/sift_20130403.zip"


    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        app_expose(base_app.index)
        app_expose(base_app.input_select)
        app_expose(base_app.input_upload)
        app_expose(base_app.params)

    def build(self):
        """
        program build/update
        """
        zip_filename = 'sift_20130403.zip'
        src_dir_name = 'sift_20130403/'
        prog_filename = 'sift'
        prog_filename2 = 'matching'
        prog_filename3 = 'extract_thumbnail_bis'
        # store common file path in variables
        tgz_file = self.dl_dir + zip_filename
        prog_file = self.bin_dir + prog_filename
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(app.xlink_src, tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s" % (self.src_dir + src_dir_name),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)

            # copy all the programs to the bin dir
            shutil.copy(self.src_dir + os.path.join(os.path.join(src_dir_name,'bin'),
                     prog_filename), os.path.join(self.bin_dir, prog_filename) )
            shutil.copy(self.src_dir + os.path.join(os.path.join(src_dir_name,'bin'),
                     prog_filename2), os.path.join(self.bin_dir, prog_filename2) )
            shutil.copy(self.src_dir + os.path.join(os.path.join(src_dir_name,'bin'),
                     prog_filename3), os.path.join(self.bin_dir, prog_filename3) )
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return




    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        run redirection
        """
        # Initialize default values
        self.cfg['param']['newrun'] = False
        self.cfg['param']['action'] = 'std_sift_matching'
        self.cfg['param']['show'] = 'result'
        self.cfg['param']['x'] = '-1' 
        self.cfg['param']['y'] = '-1'
        VALID_KEYS = [
                'newrun',
                'action',
                'show',
                'x',
                'y',
                'n_oct',
                'n_spo',
                'sigma_min',
                'delta_min',
                'sigma_in',
                'C_DoG',
                'C_edge',
                'n_bins',
                'lambda_ori',
                't',
                'n_hist',
                'n_ori',
                'lambda_descr',
                'flag_match',
                'C_match']
        
        if ('paradic' in self.cfg['param']):       
            self.cfg['param']['paradic'] = dict(eval(str(self.cfg['param']['paradic'])))  # deserialization !!
        else:
            self.load_standard_parameters()
        

                
        

        # PROCESS ALL THE INPUTS
        for prp in kwargs.keys():
            if( prp in VALID_KEYS ):
                if (prp == 'newrun'):
                    self.cfg['param']['newrun'] = kwargs[prp]
                elif (prp == 'action'):
                    self.cfg['param']['action'] = kwargs[prp]
                elif (prp == 'show'):
                    self.cfg['param']['show'] = kwargs[prp]
                elif (prp == 'x'):
                    self.cfg['param']['x'] = kwargs[prp]
                elif (prp == 'y'):
                    self.cfg['param']['y'] = kwargs[prp]
                else:
                    self.cfg['param']['paradic'][prp] = kwargs[prp]         
        self.cfg.save()
        

       
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")
    
    
    @cherrypy.expose
    @init_app
    def result(self, **kwargs):
        """
        display the algo results
        """
        VALID_KEYS = ['show']
        
        for prp in kwargs.keys():
            if( prp in VALID_KEYS ):
                if (prp == 'show'):
                    self.cfg['param']['show'] = kwargs[prp]
        self.cfg.save()
        
        show = self.cfg['param']['show']
        if (show == 'antmy_detect'):
            return self.tmpl_out("antmy_detect.html")
        elif (show == 'antmy_descr_match'):
            return self.tmpl_out("antmy_descr_match.html")
        elif (show == 'antmy_gauss_scsp'):
            return self.tmpl_out("antmy_gauss_scsp.html")
        else: # show == basic
            return self.tmpl_out("result.html")
    


    def load_standard_parameters(self):
        paradic = {'x':'0',
                'y':'0',
                'n_oct':'8',
                'n_spo':'3',
                'sigma_min':'0.8',
                'delta_min':'0.5',
                'sigma_in':'0.5',
                'C_DoG':'0.03',
                'C_edge':'10',
                'n_bins':'36',
                'lambda_ori':'1.5',
                't':'0.8',
                'n_hist':'4',
                'n_ori':'8',
                'lambda_descr':'6',
                'flag_match':'1',
                'C_match':'0.6'}
        self.cfg['param']['paradic'] = paradic
        self.cfg.save()



    @cherrypy.expose
    @init_app
    def run(self):
        """
          Accepted value for 'ACTION' flag
                std_sift_matching   :  run SIFT and MATCHING with default settings,
                cust_sift_matching  :  run SIFT and MATCHING with customized settings,
                cust_matching       :  run MATCHING with customized settings.
                
          Each action also runs the appropriate illustration routines.
          Accepted value for 'SHOW' flag
                result              :  standard results,
                antmy_detect        :  Anatomy of SIFT, keypoint detection,
                antmy_descr_match   :  Anatomy of SIFT, keypoint description and matching,
                antmy_gauss_scsp    :  Anatomy of SIFT, Gaussian scale-space.
        """
        
        
        # read (x,y) - Set SIFT parameters
        action = self.cfg['param']['action']
        x = self.cfg['param']['x'] # Expressed en PIL coordinates system  y|  x-
        y = self.cfg['param']['y']
        
        # hack 1
        # read image size and store them in 'param' dict to control html rendering
        work_dir = self.work_dir
        [w1, h1] = Image.open(work_dir+'input_0.orig.png').size
        [w2, h2] = Image.open(work_dir+'input_1.orig.png').size
        wdth = max(w1, w2)
        hght = max(h1, h2)
        wpair = int(w1+w2+max(w1, w2)/10)
        self.cfg['param']['hght'] = hght
        self.cfg['param']['wdth'] = wdth

        self.cfg.save()
        
        
        # hack 2
        # Convert x y provided by the form <input type=image ..; > 
        # We assume that the width of the html body is assumed width is 920px
        x = x*wpair/920
        y = y*wpair/920
        self.cfg['param']['x'] = x
        self.cfg['param']['y'] = y
        self.cfg.save()
        
        
        print 30*'r'
        print 'x='+str(x)
        print 'y='+str(y)
        print 'wpair='+str(wpair)
        print 30*'='
        
        
        
        if (action == 'std_sift_matching'):
            try:
                self.load_standard_parameters()
                self.run_std_sift()
                self.run_matching()
                self.illustrate_std_sift()
                self.illustrate_matching()
            except TimeoutError:
                return self.error(errcode='timeout', errmsg="Try again with simpler images.")
            except RuntimeError:
                return self.error(errcode='runtime', errmsg="Runtime error in std_sift_matching.")
            
        
        elif (action == "cust_sift_matching"):
            try:
                self.run_sift()
                print "after run_sift()"
                self.run_matching()
                print "after run_matching()"
                self.illustrate_sift()
                print "after illustrate_sift()"
                self.illustrate_matching()
                self.detail_matching()
            except TimeoutError:
                return self.error(errcode='timeout', errmsg="Try with simpler images.")
            except RuntimeError:
                return self.error(errcode='runtime', errmsg="Runtime error in cust_sift_matching.")
        
        elif (action == "cust_matching"):   
            try:
                self.run_matching()
                self.illustrate_matching()
            except TimeoutError:
                return self.error(errcode='timeout', errmsg="Try with simpler images.")
            except RuntimeError:
                return self.error(errcode='runtime', errmsg="Runtime error in cust_matching.")
        else:
            try:
                self.detail_matching()
            except TimeoutError:
                return self.error(errcode='timeout', errmsg="Try with simpler images.")
            except RuntimeError:
                return self.error(errcode='runtime', errmsg="Runtime error in else (you know).")
            
        
        ## archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.png", info="first input image")
            ar.add_file("input_1.png", info="second input image")
            ar.add_file("input_0.orig.png", info="first uploaded image")
            ar.add_file("input_1.orig.png", info="second uploaded image")
            ar.add_file("OUTmatches.png", info="matches")
            ar.add_file("keys_im0.txt", compress=True)
            ar.add_file("keys_im1.txt", compress=True)
            ar.add_file("OUTmatches.txt", compress=True)
            ar.save()
        


        self.cfg.save()



    
        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html")

        
        

        


    def run_std_sift(self):
        """
        Run the SIFT algorithm on each of the two images
        with standard parameters
        """ 
        for i in range(2):
            image = 'input_'+str(i)+'.png'
            label = 'im'+str(i)
            f = open(self.work_dir+'keys_'+label+'.txt','w')
            sift = self.run_proc(['sift', image], stdout=f)
            self.wait_proc(sift, timeout=self.timeout)
        return 1
    
    
    def run_sift(self):
        """
        Run the SIFT algorithm on each of the two images
        with custom parameters
        """
        paradic = dict(eval(str(self.cfg['param']['paradic'])))  
        for i in range(2):
            image = 'input_'+str(i)+'.png'
            label = 'im'+str(i)
            f = open(self.work_dir+'keys_'+label+'.txt','w')
            sift = self.run_proc(['sift', image, label,
                                  str(paradic['n_oct']),
                                  str(paradic['n_spo']),
                                  str(paradic['sigma_min']),
                                  str(paradic['delta_min']),
                                  str(paradic['sigma_in']),
                                  str(paradic['C_DoG']),
                                  str(paradic['C_edge']),
                                  str(paradic['n_bins']),
                                  str(paradic['lambda_ori']),
                                  str(paradic['t']),
                                  str(paradic['n_hist']),
                                  str(paradic['n_ori']),
                                  str(paradic['lambda_descr'])],
                                  stdout=f)                
            self.wait_proc(sift, timeout=self.timeout)   
        return 1
    
    
    def run_matching(self):  
        """
        Run the matching algorithm on a pair of keypoint.
        input : keys_im0.txt
                keys_im1.txt
        argument : flag_match , method flag
                   C_match    , threshold
        extra argument :
                   n_hist n_ori to read the feature fector and
                                to save in ASCII files the keypoints feature vectors,
                   n_bins       to save in ASCII files the keypoints orientation histograms
        """
        paradic = dict(eval(str(self.cfg['param']['paradic'])))
        print 'in run_matching()   n_bins = ' +str(paradic['n_bins'])
        
        
        f = open(self.work_dir+'matches.txt','w')
        matching = self.run_proc(['matching', 'keys_im0.txt',
                                              'keys_im1.txt',
                                              str(paradic['flag_match']),
                                              str(paradic['C_match']),
                                              str(paradic['n_hist']),
                                              str(paradic['n_ori']),
                                              str(paradic['n_bins'])],
                                              stdout=f)
        self.wait_proc(matching, timeout=self.timeout)
        return 1          


    def illustrate_matching(self):
        """
        Draw matching keypoints in each image.
        Draw matches on the pair of images.
        """
        work_dir = self.work_dir
        draw_keys_oriented(work_dir+'matching_keys_im0.txt', work_dir+'input_0.orig.png', work_dir+'matching_keys_im0.png')
        draw_keys_oriented(work_dir+'matching_keys_im1.txt', work_dir+'input_1.orig.png', work_dir+'matching_keys_im1.png')
        draw_matches(work_dir+'matches.txt', work_dir+'input_0.orig.png', work_dir+'input_1.orig.png', work_dir+'OUTmatches.png')
        return 1


    def illustrate_std_sift(self):
        """
        Draw detected keypoints in each image.
        """
        work_dir = self.work_dir
        draw_keys_oriented(work_dir+'keys_im0.txt', work_dir+'input_0.orig.png', work_dir+'keys_im0.png')
        draw_keys_oriented(work_dir+'keys_im1.txt', work_dir+'input_1.orig.png', work_dir+'keys_im1.png')
        return 1
        

    def illustrate_sift(self):
        """
        Draw keypoints at each stage on each image
         TODO Plot the distribution of detections along scales
        """
        
        print 'passe illustrate sift in'
        
        work_dir = self.work_dir
        draw_keys_oriented(work_dir+'keys_im0.txt', work_dir+'input_0.orig.png', work_dir+'keys_im0.png')
        draw_keys_oriented(work_dir+'keys_im1.txt', work_dir+'input_1.orig.png', work_dir+'keys_im1.png')
        
        print 'passe illustrate sift in'
        
        
        for im in ['0','1']:
            for kypts in ['NES', 'DoGSoftThresh', 'ExtrInterp',
                          'ExtrInterpREJ', 'DoGThresh', 'OnEdgeResp',
                          'OnEdgeRespREJ']:
#                          'DoGThresh','OnEdgeResp','OnEdgeRespREJ', 'DoGSoftThreshREJ','DoGThreshREJ' ]:
                draw_keys(work_dir+'extra_'+kypts+'_im'+im+'.txt',
                          work_dir+'input_'+im+'.orig.png',
                          work_dir+'extra_'+kypts+'_im'+im+'.png')    
             
            draw_keys_oriented(work_dir+'extra_OriAssignedMULT_im'+im+'.txt',
                               work_dir+'input_'+im+'.orig.png',
                               work_dir+'extra_OriAssignedMULT_im'+im+'.png')
            #draw_keys_oriented(work_dir+'extra_im'+im+'.txt', work_dir+'input_'+im+'.orig.png',work_dir+'extra_im'+im+'.png')
        
        print 'passe illustrate sift out'
            
        return 1




    def detail_matching(self):
        """
        Draw keypoints at each stage on each image
        Draw matches on the pair of image
        """
        paradic = dict(eval(str(self.cfg['param']['paradic'])))
        work_dir = self.work_dir
        
        x = float(self.cfg['param']['x'])   # selected pixel in the first image
        y = float(self.cfg['param']['y'])
        
        # sift parameters
        n_bins = int(paradic['n_bins'])  # number of bins in the orientation histogram
        n_hist = int(paradic['n_hist'])  
        n_ori  = int(paradic['n_ori'])   # descriptor of n_hist X n_hist weighted histograms with n_ori
        delta_min = float(paradic['delta_min'])
        sigma_min = float(paradic['sigma_min'])
        sigma_in  = float(paradic['sigma_in'])
        lambda_ori   = float(paradic['lambda_ori'])
        lambda_descr = float(paradic['lambda_descr'])
        t      = float(paradic['t'])  #threshold defining reference orientations
        n_spo  = int(paradic['n_spo'])
        
        # Read feature vectors from output files
        if (os.path.getsize(work_dir+'OUTmatches.txt') > 0 ):
            pairdata = find_nearest_keypoint(work_dir+'OUTmatches.txt', y, x)
        
            # Plot the weighted histograms and the orientation histograms for each key
            illustrate_pair(pairdata, n_bins, t, n_hist, n_ori, work_dir)
            
            # Read keys coordinates.
            d = 6+n_bins+n_hist*n_hist*n_ori # size of keydata inside pairdata
            v = n_hist*n_hist*n_ori
            [x1, y1, sigma1, theta1] = [float(x) for x in pairdata[0:4]]
            [o1, s1] = [float(x) for x in pairdata[4+v:4+v+2]]
            [x2a, y2a, sigma2a, theta2a]  = [float(x) for x in pairdata[d:d+4]]
            [o2a, s2a] = [float(x) for x in pairdata[d+4+v:d+4+v+2]]
            [x2b, y2b, sigma2b, theta2b] = [float(x) for x in pairdata[2*d:2*d+4]]
            [o2b, s2b] = [float(x) for x in pairdata[2*d+4+v:2*d+4+v+2]]
            
            draw_one_match(pairdata, work_dir+'input_0.png', work_dir+'input_1.png', d, lambda_ori, lambda_descr, n_hist, work_dir+'OUTonepair.png')
                
            
            # Extract thumbnails.
            # keypoint 1 (image 1)
            print ' '.join(['extract_thumbnail_bis', work_dir+'input_0.png',
                                                str(x1), str(y1), str(sigma1), str(theta1), str(o1), str(s1),
                                                str(delta_min), str(sigma_min), str(sigma_in), str(n_spo),
                                                str(lambda_ori), str(lambda_descr), str(n_hist),
                                                work_dir+"detail_im1"])
            proc = self.run_proc(['extract_thumbnail_bis', work_dir+'input_0.png',
                                                str(x1), str(y1), str(sigma1), str(theta1), str(o1), str(s1),
                                                str(delta_min), str(sigma_min), str(sigma_in), str(n_spo),
                                                str(lambda_ori), str(lambda_descr), str(n_hist),
                                                work_dir+"detail_im1"])
            self.wait_proc(proc, timeout=self.timeout)
                                                
            # keypoint 2a (nearest neighbor in image 2)
            print ' '.join(['extract_thumbnail_bis', work_dir+'input_1.png',
                                                str(x2a), str(y2a), str(sigma2a), str(theta2a), str(o2a), str(s2a),
                                                str(delta_min), str(sigma_min), str(sigma_in), str(n_spo),
                                                str(lambda_ori), str(lambda_descr), str(n_hist),
                                                work_dir+"detail_im2a"])
            proc = self.run_proc(['extract_thumbnail_bis', work_dir+'input_1.png',
                                                str(x2a), str(y2a), str(sigma2a), str(theta2a), str(o2a), str(s2a),
                                                str(delta_min), str(sigma_min), str(sigma_in), str(n_spo),
                                                str(lambda_ori), str(lambda_descr), str(n_hist),
                                                work_dir+"detail_im2a"])
            self.wait_proc(proc, timeout=self.timeout)                                   
                                                
            # keypoint 2b (second nearest neighbor in image 2)
            proc = self.run_proc(['extract_thumbnail_bis', work_dir+'input_1.png',
                                                str(x2b), str(y2b), str(sigma2b), str(theta2b), str(o2b), str(s2b),
                                                str(delta_min), str(sigma_min), str(sigma_in), str(n_spo),
                                                str(lambda_ori), str(lambda_descr), str(n_hist),
                                                work_dir+"detail_im2b"])
            self.wait_proc(proc, timeout=self.timeout)                                   
            
            # Interpolate the thumbnails for better visualization.
            #self.run_proc(['bilin_interp', work_dir+"detail_im1_thumbnail_ori_hist.png",
                                #work_dir+"detail_im1_thumbnail_ori_histA.png"])
            #self.run_proc(['bilin_interp', work_dir+"detail_im2a_thumbnail_ori_hist.png",
                                #work_dir+"detail_im2a_thumbnail_ori_histA.png"])
            #self.run_proc(['bilin_interp', work_dir+"detail_im2b_thumbnail_ori_hist.png",
                                #work_dir+"detail_im2b_thumbnail_ori_histA.png"])
                                
            #self.run_proc(['bilin_interp', work_dir+"detail_im1_thumbnail_weighted_hists.png",
                                #work_dir+"detail_im1_thumbnail_weighted_histsA.png"])
            #self.run_proc(['bilin_interp', work_dir+"detail_im2a_thumbnail_weighted_hists.png",
                                #work_dir+"detail_im2a_thumbnail_weighted_histsA.png"])
            #self.run_proc(['bilin_interp', work_dir+"detail_im2b_thumbnail_weighted_hists.png",
                                #work_dir+"detail_im2b_thumbnail_weighted_histsA.png"])                             
            
        return 1
 


                    
      
