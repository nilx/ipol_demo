# Copyright 2010 Nicolas Limare <nicolas.limare@cmla.ens-cachan.fr>
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty provided
# the copyright notice and this notice are preserved.  This file is
# offered as-is, without any warranty.

default : bin

TARBALL	= axpb.tar.gz
TARBALL_URL	= http://www.ipol.im/meta/dev/$(TARBALL)
BIN	= bin/axpb

CCACHE  = $(shell which ccache)
CC	= $(CCACHE) cc
CXX	= $(CCACHE) c++

.PHONY	: bin distclean

# get the source code
$(TARBALL)	:
	wget -N $(TARBALL_URL)

# compile the binaries from the ./src folder into the ./bin folder
bin	: $(BIN)
$(BIN)	: $(TARBALL) makefile
	rm -rf tmp; mkdir tmp
	tar xvzf axpb.tar.gz -C tmp
	$(MAKE) -C tmp/axpb/ \
		CC="$(CC)" CXX="$(CXX)" -j4
	rm -rf bin; mkdir bin
	mv tmp/axpb/axpb $@
	rm -rf tmp

# delete the compilation by-products from the ./src folder
distclean	:
	rm -rf bin
	rm -f $(TARBALL)
