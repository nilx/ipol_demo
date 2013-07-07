#!/bin/bash

#loa. read_params.sh
. read_params.sh


Disp=$1
Filt=MF

# generate the distance map corresponding to the disparity
if [ ! -f output_corr_${Disp}.tif ]; then 
   echo "MINFILT: MISSING FILE output_corr_${Disp}.tif"
   echo "compute_distances_subpix left_imagen.tif right_imagen.tif output_${Disp}.tif output_corr_${Disp}.tif $windowsize ${Disp}"
   compute_distances_subpix left_imagen.tif right_imagen.tif output_${Disp}.tif output_corr_${Disp}.tif $windowsize ${Disp}
   compute_distances_subpix right_imagen.tif left_imagen.tif output_r_${Disp}.tif output_r_corr_${Disp}.tif $windowsize ${Disp}
fi

echo "minfilter $windowsize output_${Disp}.tif output_corr_${Disp}.tif output_${Disp}.tif output_corr_${Disp}.tif"
minfilter $windowsize output_${Disp}.tif output_corr_${Disp}.tif output_${Disp}.tif output_corr_${Disp}.tif 
minfilter $windowsize output_r_${Disp}.tif output_r_corr_${Disp}.tif output_r_${Disp}.tif output_r_corr_${Disp}.tif 

