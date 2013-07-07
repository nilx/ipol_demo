#!/bin/bash


# usage:
# /path/to/run.sh 
# READS THE PARAMETERS FROM  index.cfg  including block_match_method

# IMPLICIT INPUT FILES
#  right_image.png
#  left_image.png
#  ground_truth.tif
#
export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin/
. read_params.sh




#####################################
#  PREPROCESS 

# generate noisy images for the experiment
addnoise left_image.tif $addednoisesigma left_imagen.tif &
addnoise right_image.tif $addednoisesigma right_imagen.tif &
wait

# convert to mono
if [ "${preprocess}" == "MONOCHROME" ] 
then
   runMONOCHROME.sh
fi

# run midway if necessary
if [ "${preprocess}" == "MIDWAY" ] 
then
   runMIDWAY.sh
fi

# update/generate previews
genpreview.sh left_imagen.tif  left_imagen.png &
genpreview.sh right_imagen.tif right_imagen.png &
