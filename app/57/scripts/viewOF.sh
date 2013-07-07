#!/bin/bash

# usage:
# /path/to/.sh flow out colorwheel_out

set -e

testex() {
	if which $1 > /dev/null ; then
		echo > /dev/null
	else
		echo "ERROR: executable file $1 not available" >&2
		exit 1
	fi
}

usgexit() {
	echo -e "usage:\n\t `basename $0` [...]"
#	rm -rf $TPD
	exit 1
}

echo VSTUFF ARGC: $#
echo VSTUFF ARGV: $*

# check input
if [[ $# < 2 ]]; then
	usgexit
fi

IN=$1
OUT=$2
CWOUT=$3

FLOWMAX=`plambda $IN "x[0] x[1] hypot 0.95 *" | imprintf %a -`
viewflow $FLOWMAX $IN $OUT
#viewflow -1 $COLORWHEEL | downsa v 2 | qeasy 0 255 - cw.${S}.png

if [ "$CWOUT" != "" ]; then
   plambda $IN ":x :y join "| viewflow 1 - $CWOUT
   convert $CWOUT  -gravity NorthWest -draw "text 0,0 'Max vector lenght: $FLOWMAX'" $CWOUT
fi

