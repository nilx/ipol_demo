#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin/

set -e

usgexit() {
	echo -e "usage:\n\t `basename $0` vscale field.tiff view.png "
	exit 1
}

# check input
if [ $# != "3" ]; then
	usgexit
fi

VSCALE=$1
INFIELD=$2
OUTVIEW=$3

DISP=`mktemp /tmp/vvv.XXXXXX` 
SAMIN=`imprintf %i < $INFIELD`
#plambda $INFIELD "x[0] $SAMIN - x[1] $SAMIN - hypot" > $DISP
plambda $INFIELD "x[0]" > $DISP
DISPRANGE=`imprintf "%q[2] %q[98]" < $DISP`
gblur 1.6 $DISP | plambda - "x(1,0) x - >1 x(0,1) x - >2 <1 <2 + -1 *" | qeasy -$VSCALE $VSCALE | plambda - $DISP "x $SAMIN 2 sqrt * + >2 y $DISPRANGE qe >1 <2 <2 <1 join3" | qauto - $OUTVIEW
rm $DISP
