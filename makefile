SRC	:= $(wildcard *.py) $(wildcard */*.py)

default	:
	@cat README.txt

DEMO := $(filter-out ./.git ./base_template, \
		$(shell find ./ -maxdepth 1 -mindepth 1 -type d))

lint	: lint.flag
lint.flag	: $(SRC)
	pylint -e $?
	touch $@
# fore more details, use --disable-msg C0103,W0511

.PHONY	: update
update	:
	for D in $(DEMO); do $(MAKE) -C $$D/ update; done

.PHONY	: test
test	: update
	./demo.py

.PHONY	: clean
clean	:
	$(RM) -r */tmp
	$(RM) */input/*.__*x*__.png
	$(RM) *.flag
