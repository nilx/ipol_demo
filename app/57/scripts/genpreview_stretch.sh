#!/bin/bash
# usage:
# genpreview_stretch.sh in out [minval] [maxval]

export PATH=$PATH:/usr/bin/:/usr/local/bin/

# check input
if [ "$4" != "" ]; then
#   (min(max(x,m),M) - m ) / (M-m) * 255
   plambda $1 "x[0] $3 fmax $4 fmin $3 - $4 $3 - / 255 *" -o $2 
   addscale.py $2 $2 $3 $4
else
   qauto  $1 $2 > $2.tmp.txt   2>&1 
   min=`cat $2.tmp.txt | cut -f 4 -d' '`
   max=`cat $2.tmp.txt | cut -f 5 -d' '`
   rm $2.tmp.txt
   echo $min $max
   plambda $1 "x[0] $min fmax $max fmin $min - $max $min - / 255 *" -o $2 
   addscale.py $2 $2 $min $max
fi


