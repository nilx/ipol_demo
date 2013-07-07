#!/bin/bash

# zip the results

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin/

. read_params.sh


if [ "$1" != "" ]; then
   echo "zip $1 *_mask_*.png left*.tif right*.tif out*.tif index.cfg"
   /usr/bin/env zip $1 *_mask_*.png left*.tif right*.tif out*.tif index.cfg 
fi

# now remove the tiff files
rm output*.tif
