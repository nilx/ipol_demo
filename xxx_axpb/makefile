# Copyright 2010 Nicolas Limare <nicolas.limare@cmla.ens-cachan.fr>
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty provided
# the copyright notice and this notice are preserved.  This file is
# offered as-is, without any warranty.

default : update

TARBALL	= axpb.tar.gz
TARBALL_URL	= http://www.ipol.im/meta/dev/axpb.tar.gz
BIN	= bin/axpb

.PHONY	: update getsrc bin distclean

# check the source, update the binary if needed
update	: getsrc bin

# get and expand the source code
getsrc	:
	wget -N $(TARBALL_URL)

# compile the binaries from the ./src folder into the ./bin folder
bin	: $(BIN)
$(BIN)	: $(TARBALL)
	rm -rf tmp; mkdir tmp       # make an empty tmp dir
	tar xvzf axpb.tar.gz -C tmp # extract the source in the tmp dir
	make -C tmp/axpb/           # build the binary
	rm -rf bin; mkdir bin       # make an empty bin dir
	mv tmp/axpb/axpb $@         # save the binary
	rm -rf tmp                  # cleanup 

# delete the compilation by-products from the ./src folder
distclean	:
	rm -rf bin
	rm -f $(TARBALL)
