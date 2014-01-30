#!/bin/bash

# usage:
# /path/to/run.sh 
# READS THE PARAMETERS FROM  index.cfg  including block_match_method

# IMPLICIT INPUT FILES
#  right_imagen.tif
#  left_imagen.tif
#  ground_truth.tif
#
# IMPLICIT OUTPUT FILES
#
#  disp_X.{tif}           "F"
#  corr_X.{tif}           "F"
#
#
export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin/
. read_params.sh

if [ "${1}" != "" ]
then
   ALGO=$1
else
   ALGO=${block_match_method}
fi


#####################################
# run the stereo algorithm
# clean before running
rm output_${ALGO}.tif output_corr_${ALGO}.tif  output_r_${ALGO}.tif output_r_corr_${ALGO}.tif 
echo "simplebm -t $ALGO -w $windowsize -h $windowsize -r $min_disparity -R $max_disparity -s $min_off_y -S $max_off_y left_imagen.tif right_imagen.tif output_${ALGO}.tif output_corr_${ALGO}.tif  output_r_${ALGO}.tif output_r_corr_${ALGO}.tif "

SUBPIXEL=$subpixel \
/usr/bin/time -p \
simplebm -t $ALGO -w $windowsize -h $windowsize -r $min_disparity -R $max_disparity -s $min_off_y -S $max_off_y left_imagen.tif right_imagen.tif output_${ALGO}.tif output_corr_${ALGO}.tif  output_r_${ALGO}.tif output_r_corr_${ALGO}.tif \
2>&1 | grep user > $ALGO.time.txt

## generate preview disparity 
viewOF.sh output_${ALGO}.tif output_${ALGO}.png output_${ALGO}_map.png

##
## generate preview disparity 
#Ri=$min_disparity
#Ra=$max_disparity
#Si=$min_off_y
#Sa=$max_off_y
#
## OLD VISUALIZATION
##plambda output_${ALGO}.tif "x[0] x[1] 0 join3" | iion -  output1_${ALGO}.tif
##qauto output1_${ALGO}.tif output_${ALGO}.png 
##echo "plambda  output_${ALGO}.png "i: :w / $Ra $Ri - *  $Ri +        j: :h / $Sa $Si - * $Si +    0 join3" | qauto - output_${ALGO}_map.png"
##plambda  output_${ALGO}.png ":i :w / $Ra $Ri - *  $Ri +       :j :h / $Sa $Si - * $Si +    0 join3" | qauto - output_${ALGO}_map.png
#
## NEW VISUALIZATION PALETTE 1
#plambda output_${ALGO}.tif "x[0] $Ri -  $Ra $Ri - / 255 * 128 -      x[1]  $Si -  $Sa $Si - / 255 * 128 -     0 join3" | qeasy -128 127 - output_${ALGO}.png
#echo "plambda  output_${ALGO}.png "i: :w /  255 * 128 -      j: :h /  255 * 128 -  0 join3" | qeasy -128 127 - output_${ALGO}_map.png"
#plambda  output_${ALGO}.png ":i :w / 255 *  128 -    :j :h / 255 * 128 -  0 join3" | qeasy -128 127 - output_${ALGO}_map.png
#
## NEW VISUALIZATION PALETTE 2
##plambda output_${ALGO}.tif "x[0]" | qeasy $Ri $Ra | iion - output_${ALGO}.png
##plambda output_${ALGO}.tif "x[1]" | qeasy $Si $Sa | plambda output_${ALGO}.png - "x y 0 join3" | iion - output_${ALGO}.png
##echo "plambda  output_${ALGO}.png "i: :w /  255 *       j: :h /  255 *   0 join3" | qeasy 0 255 - output_${ALGO}_map.png"
##plambda  output_${ALGO}.png ":i :w / 255 *      :j :h / 255 *   0 join3" | qeasy 0 255 - output_${ALGO}_map.png
#
## TODO : ADD LEGEND
#convert  output_${ALGO}_map.png  -gravity NorthWest -draw "text 0,0 '[$Ri,$Si]'" output_${ALGO}_map.png
#convert  output_${ALGO}_map.png  -gravity SouthWest -draw "text 0,0 '[$Ri,$Sa]'" output_${ALGO}_map.png
#convert  output_${ALGO}_map.png  -gravity NorthEast -draw "text 0,0 '[$Ra,$Si]'" output_${ALGO}_map.png
#convert  output_${ALGO}_map.png  -gravity SouthEast -draw "text 0,0 '[$Ra,$Sa]'" output_${ALGO}_map.png


# generate backflow visualization
backflow output_${ALGO}.tif  right_imagen.tif backflow_${ALGO}.tif
genpreview.sh backflow_${ALGO}.tif backflow_${ALGO}.png &
plambda left_imagen.tif backflow_${ALGO}.tif "x y - fabs" | genpreview.sh - backflow_${ALGO}_diff.png &
#plambda left_imagen.tif backflow_${ALGO}.tif "x y - fabs" | iion - backflow_${ALGO}_diff.tif 
#genpreview.sh backflow_${ALGO}_diff.tif backflow_${ALGO}_diff.png &


#generate preview corr for the 92-quantile
MAX90=`imprintf %q[92] output_corr_${ALGO}.tif`
plambda output_corr_${ALGO}.tif "x[0] isinf 0 x[0] if $MAX90 fmin" > tmp_${ALGO}.tif
genpreview_stretch.sh tmp_${ALGO}.tif output_corr_${ALGO}.png 
rm tmp_${ALGO}.tif

# wait for unfinished processes (specially png visualizations)
wait
