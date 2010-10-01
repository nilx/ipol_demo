# Copyright 2010 Nicolas Limare <nicolas.limare@cmla.ens-cachan.fr>
#                Agustin Salgado <asalgado@dis.ulpgc.es>
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty provided
# the copyright notice and this notice are preserved.  This file is
# offered as-is, without any warranty.

default : update

CCACHE  = $(shell which ccache)
CXX	= $(CCACHE) c++

# Source
SRC	= MissStereo
SRC_TGZ	= $(SRC).tar.gz
SRC_URL	= https://edit.ipol.im/edit/algo/m_quasi_euclidean_epipolar_rectification/$(SRC_TGZ)
SCRIPT	= Rectify.sh
BIN	= homography orsa rectify sift size

.PHONY	: update distclean bin

update	:
	-wget --no-check-certificate -N $(SRC_URL)
	$(MAKE) bin

# compile the binaries from the ./src folder into the ./bin folder
bin	: $(SRC_TGZ) makefile bin
	rm -rf src; mkdir src
	tar -xvf $< -C src
	mkdir src/$(SRC)/build; cd src/$(SRC)/build; \
		CC="ccache cc" CXX="ccache c++" \
		cmake \
		-D CMAKE_BUILD_TYPE:string=Release ../src
	$(MAKE) -C src/$(SRC)/build/ -j4
	rm -rf bin; mkdir bin
	cp $(addprefix src/$(SRC)/build/bin/, $(BIN)) bin
	cp -L $(addprefix src/$(SRC)/scripts/, $(SCRIPT)) bin
	rm -rf src

# delete the compilation by-products from the ./src folder
distclean	:
	rm -rf bin src
