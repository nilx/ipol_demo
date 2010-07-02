SRC	:= controller.py $(wildcard */*.py)

lint	: lint.flag
lint.flag	: $(SRC)
	pylint -e $^
	touch $@

.PHONY	: test
test	:
	./controller.py

.PHONY	: clean
clean	:
	$(RM) -r */data/tmp/*
	$(RM) */data/input/*.*x*.png
	$(RM) lint.flag
