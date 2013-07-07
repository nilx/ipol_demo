#!/bin/bash

#loa. read_params.sh
. read_params.sh

if [ "${1}" != "" ]
then
   ALGO=$1
else
   ALGO=${block_match_method}
fi





echo "SUBPIXEL=$subpixel simplestereo -t $ALGO -w $windowsize -h $windowsize -r $min_disparity -R $max_disparity  left_imagen.tif right_imagen.tif output_${ALGO}.tif output_corr_${ALGO}.tif  output_r_${ALGO}.tif output_r_corr_${ALGO}.tif"

SUBPIXEL=$subpixel \
/usr/bin/time -p \
simplestereo -t $ALGO -w $windowsize -h $windowsize -r $min_disparity -R $max_disparity left_imagen.tif right_imagen.tif output_${ALGO}.tif output_corr_${ALGO}.tif  output_r_${ALGO}.tif output_r_corr_${ALGO}.tif \
2>&1 | grep user > $ALGO.time.txt

