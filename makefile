SRC	:= $(wildcard *.py) $(wildcard */*.py)

default	:
	@cat README.txt

DEMO := $(filter-out ./.git ./lib, \
		$(shell find ./ -maxdepth 1 -mindepth 1 -type d))

.PHONY	: checklint srcdoc update test clean
check	: $(SRC)
	pylint -e $^

lint	: $(SRC)
	pylint $^

srcdoc	: $(SRC)
	$(RM) -r srcdoc
	epydoc -o srcdoc $^

update	:
	for D in $(DEMO); do $(MAKE) -C $$D/ update; done

test	: update
	./demo.py

clean	:
	$(RM) -r */tmp
	$(RM) */input/*.__*x*__.png
	$(RM) -r srcdoc
