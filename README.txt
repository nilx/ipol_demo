% IPOL demo web service

# Requirements

This code requires python plus some modules, included in the following
Debian/Ubuntu packages: python, python-cherrypy3, python-mako, python-imaging.

# Usage

To test this service locally,
* copy `demo.conf.example` to `demo.conf`
* run the `demo.py` script (must be executable)
* visit http://127.0.0.1:8080 with a graphical web browser

# Shortcuts

A makefile provides a few convenient shortcuts:

* make test
  run the service locally
* make clean
  delete locally generated temporary files and thumbnails
* make lint
  checks the source code quality (it requires the pylint program)

% Development

To create a new demo,

1. copy an example demo ('xxx_something') to a new folder name; this folder
   name will ne the demo id
2. in this new folder, customize the class attributes and functions in
   `__init__.py`
3. in this new folder, customize the default input files in
   `data/input`, and update the description of these files in
   `data/input/index.cfg`
4. in this new folder, customize the `params.html` and `result.html`
   templates in the `tmpl` folder
5. in this new folder, customize the `makefile` and `src` folder
6. debug, test, debug, release
