The scripts for running a method of filter or decision criteria allo follow the same structure: 

runALGO.sh

where ALGO is the SAME identifier used in the web template.

The parameter passing is mostly implicit. 
 * Most of the files have fixed names and the format is always tiff for data, and png for masks.
      left_image.tif      right_image.tif 
      ground_truth.tif    
      ground_truth_mask.png

 * The output also have fixed manes usually completed with _ALLGORITHM.tif
      FOR THE DISPARITIES: output_ALGO.tif output_r_ALGO.tif
      FOR THE COSTS      : output_corr_ALGO.tif output_r_corr_ALGO.tif
      FOR THE MASK       : output_mask_ALGO_DECISION.png
      FOR THE FILTERS    : output_ALGO_FILTER.png output_corr_ALGO_FILTER.tif

 * Before executing the script the parameters are written in the   params   file, 
      noise_sigma=      0.2887
      addednoisesigma=  0
      windowsize=       9
      min_disparity=    -90
      max_disparity=    30
      disp_range=       90
      gt=               ~/093A52/ground_truth.tif
      maxerrdiff=       4
      subpixel=         2
      isubpixel=        0.5



There are three classes of scripts: MATCHING, DECISION and FILTER
 * MATCHING methods take images and compute disparity and optionally cost maps.
   There scripts receive as input the left/right image and the names of its four outputs

 * DECISION methods take the images and disparity maps produced with a certain MATCHING. 
   The product are the rejection masks.
   The union of all the selected rejection masks in a run is also computed.

 * FILTER methods have access the images, disparity maps and all the rejection masks. 
   The product are refined disparity and eventyally cost maps.


