"""
IPOL demo support library
"""

from .misc import prod, init_app, app_expose
from .image import image, thumbnail
from .base_app import base_app

# compat
from .config import file_dict as index_dict
