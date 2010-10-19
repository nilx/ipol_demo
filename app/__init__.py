"""
IPOL demo app collection
"""

import os

def get_demo_dict():
    """
    build a demo dictionary, implemented as a function to avoid
    module recursivity
    @return (id:app) dict
    """
    demo_dict = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for demo_id in os.listdir(base_dir):
        if not os.path.isdir(os.path.join(base_dir, demo_id)):
            continue
        # function version of `from demo_id import app as demo.app`
        # TODO: import as demo_app
        demo = __import__(demo_id, globals(), locals(), ['app'], -1)        
        demo_dict[demo_id] = demo.app
    return demo_dict

