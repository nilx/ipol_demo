# Copyright 2010 Nicolas Limare <nicolas.limare@cmla.ens-cachan.fr>
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty provided
# the copyright notice and this notice are preserved.  This file is
# offered as-is, without any warranty.

default : update

# 
DEMONAME=stereo-leger-tan-pumir
AUTOK=autoK
MATCH=match

# Root demo
TARBALL	= $(DEMONAME).tar.gz
TARBALL_URL= http://www.ipol.im/pub/algo/gjmr_line_segment_detector/$(TARBALL)
BIN	= bin/$(DEMONAME)
SRC_PATH= src/$(DEMONAME)

# First subprogram
TARBALL1= $(SRC_PATH)/$(AUTOK).tar.gz    
BIN1	= bin/$(AUTOK)
PATH1	= $(SRC_PATH)/$(AUTOK)

# Second subprogram
TARBALL2= $(SRC_PATH)/$(MATCH).tar.gz
BIN2	= bin/$(MATCH)
PATH2	= $(SRC_PATH)/$(MATCH)-v3.3.src


CCACHE  = $(shell which ccache)
CC	= $(CCACHE) cc
CXX	= $(CCACHE) c++

.PHONY	: update distclean

update	:
	#wget -N $(TARBALL_URL)
	$(MAKE) $(BIN)
	$(MAKE) $(BIN1)
	$(MAKE) $(BIN2)

# compile the binaries from the ./src folder into the ./bin folder
$(BIN)	: $(TARBALL) makefile
	rm -rf src; mkdir src

    # Decompress the DEMO tar.gz file
	tar xzf $< -C src

	rm -rf bin; mkdir bin


# compile the binaries from the ./src folder into the ./bin folder
# 1) installation the first programm (autoK)
$(BIN1)	: $(TARBALL1) makefile

	tar -xvf  $< -C $(SRC_PATH)
	$(MAKE) -C $(PATH1)/unix/ OMP=1 \
		CC="$(CC)" CXX="$(CXX)" -j4

	mv $(PATH1)/bin/$(AUTOK)  $@


# compile the binaries from the ./src folder into the ./bin folder
# 2) installation the second programm (match)
$(BIN2)	: $(TARBALL2) makefile

	tar -xvf $< -C $(SRC_PATH)
	$(MAKE) -C $(PATH2)/unix/ OMP=1 \
		CC="$(CC)" CXX="$(CXX)" -j4

	mv $(PATH2)/bin/$(MATCH)  $@


	rm -rf src

# delete the compilation by-products from the ./src folder
distclean	:
	rm -rf bin
	rm -f $(TARBALL)
