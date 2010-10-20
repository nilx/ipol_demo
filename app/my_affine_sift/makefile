# Copyright 2010 Nicolas Limare <nicolas.limare@cmla.ens-cachan.fr>
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty provided
# the copyright notice and this notice are preserved.  This file is
# offered as-is, without any warranty.

default : update

ASIFT_TGZ	= ASIFT_png.tar.gz
ASIFT_TGZ_URL	= http://www.ipol.im/pub/algo/my_affine_sift/$(ASIFT_TGZ)
SIFT_TGZ	= SIFT_png.tar.gz
SIFT_TGZ_URL	= http://www.ipol.im/pub/algo/my_affine_sift/$(SIFT_TGZ)

CCACHE  = $(shell which ccache)
CC	= $(CCACHE) cc
CXX	= $(CCACHE) c++

.PHONY	: update distclean

update	:
	wget -N $(ASIFT_TGZ_URL)
	wget -N $(SIFT_TGZ_URL)
	rm -rf bin; mkdir bin
	$(MAKE) bin/asift bin/sift

# compile the binaries from the ./src folder into the ./bin folder
bin/asift	: $(ASIFT_TGZ)
	rm -rf src; mkdir src
	tar xzf $< -C src
	$(MAKE) -C src/ASIFT_png/ OMP=1 \
		CC="$(CC)" CXX="$(CXX)" -j4
	mv src/ASIFT_png/demo_ASIFT $@
	rm -rf src
bin/sift	: $(SIFT_TGZ)
	rm -rf src; mkdir src
	tar xzf $< -C src
	$(MAKE) -C src/SIFT_png/ OMP=1 \
		CC="$(CC)" CXX="$(CXX)" -j4
	mv src/SIFT_png/demo_SIFT $@
	rm -rf src

# delete the compilation by-products from the ./src folder
distclean	:
	rm -rf bin
	rm -f $(ASIFT_TGZ) $(SIFT_TGZ)
