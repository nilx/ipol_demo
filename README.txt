% IPOL demo web service

# Requirements

This code requires python plus some modules, included in the following
Debian/Ubuntu packages: python, python-cherrypy3, python-mako, python-imaging.

# Usage

To test this service locally,
* copy `controller.conf.example` to `controller.conf`
* run the `controller.py` script (must be executable)
* visit http://127.0.0.1:8080 with a graphical web browser

# Shortcuts

A makefile provides a few convenient shortcuts:

* make test
  run the service locally
* make clean
  delete locally generated temporary files and thumbnails
* make lint
  checks the source code quality (it requires the pylint program)
