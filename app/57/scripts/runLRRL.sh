#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/

#loa. read_params.sh
. read_params.sh

if [ ! -f output_r_${1}.tif ]; then 
   echo "LRRL: MISSING FILE output_r_${1}.tif"
   exit 0
fi

#compute LRRL
echo "stereoLRRL output_${1}.tif output_r_${1}.tif output_mask_${1}_LRRL.png 1"
stereoLRRL output_${1}.tif output_r_${1}.tif output_mask_${1}_LRRL.png 1
