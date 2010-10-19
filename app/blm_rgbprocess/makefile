# Copyright 2010 Nicolas Limare <nicolas.limare@cmla.ens-cachan.fr>
#		 Jose-Luis Lisani <joseluis.lisani@uib.es>
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty provided
# the copyright notice and this notice are preserved.  This file is
# offered as-is, without any warranty.

default : update

BINNAME = rgbprocess
TARBALL	= $(BINNAME).tar.gz
TARBALL_URL	= http://dmi.uib.es/~lisani/$(TARBALL)
BIN	= bin/$(BINNAME)

CCACHE  = $(shell which ccache)
CC	= $(CCACHE) cc
CXX	= $(CCACHE) c++

.PHONY	: update distclean

update	:
	wget -N $(TARBALL_URL)
	$(MAKE) $(BIN)

# compile the binaries from the ./src folder into the ./bin folder
$(BIN)	: $(TARBALL) makefile
	rm -rf src; mkdir src
	tar xvzf $(TARBALL) -C src
	$(MAKE) -C src/$(BINNAME)/ \
		CC="$(CC)" CXX="$(CXX)" -j4
	rm -rf bin; mkdir bin
	mv src/$(BINNAME)/$(BINNAME) $@
	rm -rf src

# delete the compilation by-products from the ./src folder
distclean	:
	rm -rf bin
	rm -f $(TARBALL)
