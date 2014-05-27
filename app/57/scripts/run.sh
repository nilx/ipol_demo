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
   arg1=$1
else
   arg1=${block_match_method}
fi




#####################################
# run the stereo algorithm

# clean before running
rm output_${arg1}.tif output_corr_${arg1}.tif  output_r_${arg1}.tif output_r_corr_${arg1}.tif 
runSTEREO.sh  $arg1






#####################################
# RUN ALL SELECTED FILTERS on top of the result
Methods=${filter_method}

for Filt in $Methods
do
   run${Filt}.sh $arg1
done





# generate preview disparity 
plambda output_${arg1}.tif "x[0]" -o  output1_${arg1}.tif
genpreview_stretch.sh output1_${arg1}.tif output_${arg1}.png ${min_disparity} ${max_disparity} &
#view_landscape.sh 1 output1_${arg1}.tif output_${arg1}_landscape.png
## TODO ADD A SCALE! 

# generate backflow visualization
plambda output_${arg1}.tif "x[0] 0 join" | backflow - right_imagen.tif backflow_${arg1}.tif
genpreview.sh backflow_${arg1}.tif backflow_${arg1}.png &
plambda left_imagen.tif backflow_${arg1}.tif "x y - fabs" | genpreview.sh - backflow_${arg1}_diff.png &
#plambda left_imagen.tif backflow_${arg1}.tif "x y - fabs" | iion - backflow_${arg1}_diff.tif 
#genpreview.sh backflow_${arg1}_diff.tif backflow_${arg1}_diff.png &


#generate preview corr for the 92-quantile
MAX90=`imprintf %q[92] output_corr_${arg1}.tif`
plambda output_corr_${arg1}.tif "x[0] isinf 0 x[0] if $MAX90 fmin" > tmp_${arg1}.tif
genpreview_stretch.sh tmp_${arg1}.tif output_corr_${arg1}.png 
rm tmp_${arg1}.tif






#####################################
# compute the STATISTICS
if [ "${ground_truth}" != "" ]
then
   DISPSTAT.sh $arg1

   ## DUMP THE STATISTICS TO A BIG FILE
   DISPSTAT=`/usr/bin/head -1  ${arg1}_stat.txt`
   echo "$arg1 $subpixel $windowsize $totalsigma \"$input_id\" $DISPSTAT" >> ../../ALL_DISP_STAT.txt

fi

# wait for unfinished processes (specially png visualizations)
wait
