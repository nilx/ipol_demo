#!/bin/bash

# out = a * in + b
# axpb.sh in out a b

plambda $1 "x[0] $3 * $4 +" | iion - $2 

