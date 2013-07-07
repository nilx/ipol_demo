#!/bin/bash

#loa. read_params.sh
. read_params.sh

ALGO=SSD-mean-SHIFT

echo "SUBPIXEL=$subpixel stereoSSD-mean -w $windowsize -h $windowsize -r $min_disparity -R $max_disparity  left_imagen.tif right_imagen.tif output_${ALGO}.tif output_corr_${ALGO}.tif  output_r_${ALGO}.tif output_r_corr_${ALGO}.tif"

SUBPIXEL=$subpixel stereoSSD-mean -w $windowsize -h $windowsize -r $min_disparity -R $max_disparity left_imagen.tif right_imagen.tif output_${ALGO}.tif output_corr_${ALGO}.tif  output_r_${ALGO}.tif output_r_corr_${ALGO}.tif 


echo "RUN MINFILTER TO COMPUTE THE SHIFTABLE WINDOWS"
MASK_THRES=1 minfilter $windowsize output_${ALGO}.tif output_corr_${ALGO}.tif output_${ALGO}.tif output_corr_${ALGO}.tif

MASK_THRES=1 minfilter $windowsize output_r_${ALGO}.tif output_r_corr_${ALGO}.tif output_r_${ALGO}.tif output_r_corr_${ALGO}.tif
