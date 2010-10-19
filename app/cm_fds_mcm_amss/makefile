# Copyright 2010 Nicolas Limare <nicolas.limare@cmla.ens-cachan.fr>
#		 Jose-Luis Lisani <joseluis.lisani@uib.es>
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty provided
# the copyright notice and this notice are preserved.  This file is
# offered as-is, without any warranty.

default : update

BINNAME1 = mcm
DIRNAME1=fds_mcm
TARBALL1 = fds_mcm.tar.gz
TARBALL1_URL	= http://dmi.uib.es/~lisani/$(TARBALL1)
BIN1	= bin/$(BINNAME1)

BINNAME2 = amss
DIRNAME2=fds_amss
TARBALL2 = fds_amss.tar.gz
TARBALL2_URL	= http://dmi.uib.es/~lisani/$(TARBALL2)
BIN2	= bin/$(BINNAME2)

CCACHE  = $(shell which ccache)
CC	= $(CCACHE) cc
CXX	= $(CCACHE) c++

.PHONY	: update distclean

update	:
	wget -N $(TARBALL1_URL)
	rm -rf bin; mkdir bin
	$(MAKE) $(BIN1)
	wget -N $(TARBALL2_URL)
	$(MAKE) $(BIN2)

# compile the binaries from the ./src folder into the ./bin folder
$(BIN1)	: $(TARBALL1) makefile
	rm -rf src; mkdir src
	tar xvzf $(TARBALL1) -C src
	$(MAKE) -C src/$(DIRNAME1)/$(BINNAME1) \
		CC="$(CC)" CXX="$(CXX)" -j4
	mv src/$(DIRNAME1)/$(BINNAME1)/$(BINNAME1) $@
	rm -rf src

$(BIN2)	: $(TARBALL2) makefile
	rm -rf src; mkdir src
	tar xvzf $(TARBALL2) -C src
	$(MAKE) -C src/$(DIRNAME2)/$(BINNAME2)/ \
		CC="$(CC)" CXX="$(CXX)" -j4
	mv src/$(DIRNAME2)/$(BINNAME2)/$(BINNAME2) $@
	rm -rf src


# delete the compilation by-products from the ./src folder
distclean	:
	rm -rf bin
	rm -f $(TARBALL1)
	rm -f $(TARBALL2)

