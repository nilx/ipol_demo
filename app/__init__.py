"""
IPOL demo app collection
"""
# pylint: disable=C0103

import os

base_dir = os.path.dirname(os.path.abspath(__file__))

# (id:app) demo dict
demo_dict = dict([(demo_id,
                   # function version of `from demo_id import app as _.app`
                   __import__(demo_id, globals(), locals(), ['app'], -1).app)
                  for demo_id in os.listdir(base_dir)
                  if os.path.isdir(os.path.join(base_dir, demo_id))])
                  

