SRC	= controller.py \
	$(addprefix base_demo/, lib.py empty_app.py base_app.py __init__.py) \
	$(addprefix simple_demo/, app.py __init__.py)

lint	: lint.flag
lint.flag	: $(SRC)
	pylint -e $^
	touch $@