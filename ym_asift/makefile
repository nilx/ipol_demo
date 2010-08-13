# Copyright 2010 Nicolas Limare <nicolas.limare@cmla.ens-cachan.fr>
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty provided
# the copyright notice and this notice are preserved.  This file is
# offered as-is, without any warranty.

default : update

TARBALL	= ASIFT_png.tar.gz
TARBALL_URL	= http://www.ipol.im/pub/algo/my_affine_sift/$(TARBALL)
BIN	= bin/asift

CCACHE  = $(shell which ccache)
CC	= $(CCACHE) cc
CXX	= $(CCACHE) c++

.PHONY	: update distclean

update	:
	wget -N $(TARBALL_URL)
	$(MAKE) $(BIN)

# compile the binaries from the ./src folder into the ./bin folder
$(BIN)	: $(TARBALL) makefile
	rm -rf tmp; mkdir tmp
	tar xzf $< -C tmp
	$(MAKE) -C tmp/ASIFT_png/ OMP=1 \
		COPT="-O3 -ftree-vectorize" \
		CC="$(CC)" CXX="$(CXX)" -j4
	rm -rf bin; mkdir bin
	mv tmp/ASIFT_png/demo_ASIFT $@
	rm -rf tmp

# delete the compilation by-products from the ./src folder
distclean	:
	rm -rf bin
	rm -f $(TARBALL)
