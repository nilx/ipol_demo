SRC	:= controller.py $(wildcard */*.py)

default	:
	@cat README.txt

lint	: lint.flag
lint.flag	: $(SRC)
	pylint -e $?
	touch $@
# fore more details, use --disable-msg C0103,W0511

.PHONY	: test
test	:
	./controller.py

.PHONY	: clean
clean	:
	$(RM) -r */data/tmp/*
	$(RM) */data/input/*.*x*.png
	$(RM) lint.flag
