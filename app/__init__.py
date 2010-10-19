"""
IPOL demo app collection
"""

import os

base_dir = os.path.dirname(os.path.abspath(__file__))

def get_demo_dict():
    """
    build a demo dictionary

    @return (id:app) demo dict
    """
    demo_dict = {}
    for demo_id in os.listdir(base_dir):
        if not os.path.isdir(os.path.join(base_dir, demo_id)):
            continue
        # function version of `from demo_id import app as _tmp.app`
        _tmp = __import__(demo_id, globals(), locals(), ['app'], -1)        
        demo_app = _tmp.app
        demo_dict[demo_id] = demo_app
    return demo_dict

demo_dict = get_demo_dict()
