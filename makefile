SRC	:= demo.py $(wildcard */*.py)

default	:
	@cat README.txt

DEMO := $(filter-out ./.git ./base_demo ./template_demo, \
		$(shell find ./ -maxdepth 1 -mindepth 1 -type d))
bin	:
	for DEMO in $(DEMO); do \
		$(MAKE) -C $$DEMO bin; \
		$(MAKE) -C $$DEMO clean; \
	done

lint	: lint.flag
lint.flag	: $(SRC)
	pylint -e $?
	touch $@
# fore more details, use --disable-msg C0103,W0511

.PHONY	: update
update	:
	for D in $(DEMO); do $(MAKE) -C $$D/; done

.PHONY	: test
test	: update
	./demo.py

.PHONY	: clean
clean	:
	$(RM) -r */data/tmp/*
	$(RM) */data/input/*.*x*.png
	$(RM) lint.flag
