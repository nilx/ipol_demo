#!/bin/bash

# usage:
# DISPSTAT.sh [SAD|SSD|RAFA...]
# if parameter not specified 
# the THE PARAMETER block_match_method is read from index.cfg 


export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin/
. read_params.sh


if [ "${1}" != "" ]
then
   arg1=$1
else
   arg1=${block_match_method}
fi


# compute the STATISTICS
if [ "${ground_truth}" != "" ]
then

   # compute the areas of the masks: ALL (gtmask), OCC (gtmask \cap not occ), NOOCC (gtmask \cap occ)
   AALL=`plambda ground_truth_mask.png "x[0] 0 > " | imprintf %v -`
   AOCC=`plambda ground_truth_occ.png ground_truth_mask.png   "y[0] 0 = z[0] 0 > * " | imprintf %v -`
   ANOOCC=`plambda ground_truth_occ.png ground_truth_mask.png "y[0] 0 > z[0] 0 > * " | imprintf %v -`


   # compute the density of the disparity map in gtmask
   DENSITY=`plambda output_${arg1}.tif ground_truth_mask.png "x[0] x[0] = y[0] 0 > *" | imprintf %v -`
   DENSITY=`plambda "$DENSITY $AALL  /"`



   # compute the density of correct matches (err<=1) in gtmask
   # also compute the difference excluding the gtmask from the comparison : equivalent to midleburry ALL
   ERR_ALL=`plambda output_${arg1}.tif ground_truth.tif "x[0] y[0] - fabs 1 >" | \
            plambda - ground_truth_mask.png "x[0] y[0] 0 > *" | imprintf %v -`
   ERR_ALL=`plambda "$ERR_ALL $AALL  /"`
   # generates the difference image
   plambda output_${arg1}.tif ground_truth.tif "y[0] x[0] -" | \
       plambda - ground_truth_mask.png "x[0] y[0] 0 > *" | \
       genpreview_stretch.sh - output_${arg1}_all_diff.png -${maxerrdiff} ${maxerrdiff} &

   # compute the density of correct matches (err<=1) in gtmask \cap occ
   # also compute the difference excluding the gtmask and occlusions : equivalent to midleburry NOOCC
   ERR_NOOCC=`plambda output_${arg1}.tif ground_truth.tif "x[0] y[0] - fabs 1 >" | \
            plambda - ground_truth_occ.png ground_truth_mask.png "x[0] y[0] 0 > z[0] 0 > * *" | imprintf %v -`
   ERR_NOOCC=`plambda "$ERR_NOOCC $ANOOCC  /"`
   # generates the difference image
   plambda output_${arg1}.tif ground_truth.tif "y[0] x[0] -" | \
       plambda - ground_truth_occ.png ground_truth_mask.png "x[0] y[0] 0 > z[0] 0 > * *" | \
       genpreview_stretch.sh - output_${arg1}_noocc_diff.png -${maxerrdiff} ${maxerrdiff} &


   # generate transparent error masks all and noocc
   plambda output_${arg1}.tif ground_truth.tif "y[0] x[0] -" | \
       plambda - ground_truth_mask.png "x[0] y[0] 0 > * fabs 1 >" | \
       plambda - "x 255 * 0 0 x 255 * join3 join" | iion - error_all.png &
   plambda output_${arg1}.tif ground_truth.tif "y[0] x[0] -" | \
       plambda - ground_truth_occ.png ground_truth_mask.png "x[0] y[0] 0 > z[0] 0 > * * fabs 1 >" | \
       plambda - "x 255 * 0 0 x 255 * join3 join" | iion - error_noocc.png &


   # compute the density of correct matches (err<=1) in gtmask \cap not occ
   ERR_OCC=`plambda output_${arg1}.tif ground_truth.tif "x[0] y[0] - fabs 1 >" | \
            plambda - ground_truth_occ.png ground_truth_mask.png "x[0] y[0] 0 = z[0] 0 > * *" | imprintf %v -`
   ERR_OCC=`plambda "$ERR_OCC $AOCC  /"`


   echo "$DENSITY $ERR_ALL $ERR_OCC $ERR_NOOCC" > ${arg1}_stat.txt




#// compute statistics
M_NONDENSE=$DENSITY
M=$AALL;
#float ratio_correct_nondense = correct/M_nondense;
#float ratio_correct_dense    = correct/M;
#float RMSE                   = sqrt((float)l2 /M_nondense);
#float L1                     = (float)l1 /M_nondense;



fi

wait
