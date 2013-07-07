#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/
. read_params.sh

plambda left_imagen.tif  "x[0]  x[1]  x[2] + + 3 /" | iion - left_imagen.tif  &
plambda right_imagen.tif "x[0]  x[1]  x[2] + + 3 /" | iion - right_imagen.tif & 

wait
