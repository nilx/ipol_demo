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
MATCH	= match
MATCH_TAR	= $(MATCH).tar.gz
MATCH_URL	= https://edit.ipol.im/edit/algo/ltp_stereovision_with_graph_cuts/$(MATCH_TAR)

AUTOK	= autoK
AUTOK_TAR	= $(AUTOK).tar.gz
AUTOK_URL	= https://edit.ipol.im/edit/algo/ltp_stereovision_with_graph_cuts/$(AUTOK_TAR)

.PHONY	: update distclean

update	:
	-wget -N $(MATCH_URL)
	$(MAKE) bin/$(MATCH)
	-wget -N $(AUTOK_URL)
	$(MAKE) bin/$(AUTOK)

bin	:
	mkdir bin

# compile the binaries from the ./src folder into the ./bin folder
# 1) match

bin/$(MATCH)	: $(MATCH_TAR) makefile bin
	rm -rf src; mkdir src
	tar -xvf $< -C src
	$(MAKE) -C src/match-v3.3.src/unix/ CCOMP="$(CXX)"
	mv src/match-v3.3.src/bin/match $@
	rm -rf src

# 2) autoK
bin/$(AUTOK)	: $(AUTOK_TAR) makefile bin
	rm -rf src; mkdir src
	tar -xvf $< -C src
	$(MAKE) -C src/autoK/unix/ CCOMP="$(CXX)"
	mv src/autoK/bin/autoK $@
	rm -rf src

# delete the compilation by-products from the ./src folder
distclean	:
	rm -rf bin
