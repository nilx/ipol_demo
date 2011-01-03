# copyright (C) 2009 
# Nicolas Limare, CMLA, ENS Cachan <nicolas.limare@cmla.ens-cachan.fr>
#
# licensed under GPLv3, see http://www.gnu.org/licenses/gpl-3.0.html
#
"""
Simple color balance
"""

ID = 'simplest_color_balance'
NAME = 'simplest color balance'
INPUT_NB = 1

import os
from utils import tmp_folder, tmp_url
from utils import process_mw, get_samples_list
from utils import url_start, url_step, url_demo
from magick import convert_image, resize_image, get_image_info
from templates import http_header_redir, http_header_content
from templates import html_page, html_header, html_body
from templates import html_form_upload, html_form_samples, html_running_image
import time

HTML_HEADER = html_header(title="%s demo" % NAME)
HTML_TITLE = "IPOL demo - %s" % NAME

def input_cb():
    """
    custom input message
    """
    page = """
<div class="crosslinks">
<ul>
<li><a href="http://www.ipol.im/pub/algo/lmps_simplest_color_balance/">algorithm</a></li>
<li><a class="active" href="/megawave/demo/simplest_color_balance/">demonstration</a></li>
<li><a href="/megawave/demo/simplest_color_balance/archive/">archive</a></li>
<!-- <li><a href="">forum</a></li> -->
</ul>
</div>
<h1>%s</h1>
""" % NAME
    page += html_form_upload(input_nb=INPUT_NB, url=url_start(module_id=ID),
                             info="""\
This program performs a color balance transformation on an
image. Each color channel is scaled by an affine transformation such
that the minimum and maximum pixel values reach the extrema of the
color space.
</p><p>
Please select an image.<br />
This normalization will ignore 3% of the pixels in the upper and lower
parts of the histogram; you can run it again later with another
saturation level.""")
    samples = get_samples_list(module_id=ID, input_nb=INPUT_NB, 
                               thumbnails=True)
    if samples:
        page += html_form_samples(samples=samples, module_id=ID,
                                  url=url_start(module_id=ID),
                                  info="""\
You can also try these proposed images.""")
    print http_header_content()
    print
    print html_page(header=HTML_HEADER, title=HTML_TITLE,
                    body=html_body(content=page))
    return

def pre_cb(key):
    """
    convert the image, prepare for cb
    """ 
    page = "<h1>%s</h1>" % NAME
    page += html_running_image()
    folder = tmp_folder(key)
    # convert input
    assert convert_image(from_file='input_0', to_file='input.tiff',
                         cwd=folder, format='TIFF', 
                         options=['-type', 'truecolor',
                                  '-depth', '8'])
    page += """\
<p>The color balance transformation is running, please wait for a few seconds,
your browser will be redirected to the result.</p>
"""
    assert True == convert_image(from_file='input.tiff',
                                 to_file='input.jpeg',
                                 cwd=tmp_folder(key), format='JPEG',
                                 options=['-quality', '100',
                                          '-interlace', 'Line'])
    print http_header_redir(url=url_step(module_id=ID, key=key, step=1))
    print http_header_content()
    print
    print html_page(header=HTML_HEADER, title=HTML_TITLE,
                    body=html_body(content=page))
    return

def run_cb(key):
    """
    cb
    """
    # run cb
    page = "<h1>%s</h1>" % NAME
    folder = tmp_folder(key)
    try:
        import cgi
        query = cgi.parse_qs(cgi.os.environ['QUERY_STRING'])
        p_param = int(query['_p'][0])
    except Exception:
        p_param = 3
    if (0 > p_param) or (100 < p_param):
        p_param = 3
    start_time = time.time()
    cb = process_mw(module_id=ID, program='run.sh', 
                    options="%i" % p_param, cwd=folder)
    cb.wait()
    total_time = time.time() - start_time
    assert 0 == cb.returncode
    assert True == convert_image(from_file="output_%i.tiff" % p_param,
                                 to_file="output_%i.jpeg" % p_param,
                                 cwd=tmp_folder(key), format='JPEG',
                                 options=['-quality', '100',
                                          '-interlace', 'Line'])
    page += """
<p>You can try again <a href="%s">with another image</a> or with the
same images and a different threshold value.</p>
""" % url_demo(module_id=ID)

    page += """
<form action="" method="GET">
<input type="submit" value="restart" />
with the threshold percentage 
<select name="_p">
  <option value="0">0</option>
  <option value="1">1</option>
  <option value="2">2</option>
  <option value="3" selected>3</option>
  <option value="4">4</option>
  <option value="5">5</option>
  <option value="10">10</option>
  <option value="20">20</option>
</select> %
</form>"""

    page += """\
<p>Computation took %.2fs.</p>
""" %  total_time
    page += """\
<div style="float:left; margin:5px"><h2>Original image</h2>
<img src="%s"/></div>
""" % os.path.join(tmp_url(key), 'input.jpeg')
    page += """\
<div style="float:left; margin:5px"><h2>Color-balanced image,
%i%% saturation</h2>
<img src="%s"/></div>
""" % (p_param, os.path.join(tmp_url(key), "output_%i.jpeg" % p_param))

    print http_header_content()
    print
    print html_page(header=HTML_HEADER, title=HTML_TITLE,
                    body=html_body(content=page))

    try:
        # thumbnails
        convert_image(from_file='input.jpeg',
                      to_file='_input.jpeg',
                      cwd=tmp_folder(key), format='JPEG',
                      options=['-resize', '128x128!'])
        convert_image(from_file="output_%i.jpeg" % p_param,
                      to_file="_output_%i.jpeg" % p_param,
                      cwd=tmp_folder(key), format='JPEG',
                      options=['-resize', '128x128!'])
    except Exception:
        # pass silently
        return
    return


INFO = {
    'id'       : ID,
    'name'     : NAME,
    'input_nb' : INPUT_NB,
    'input'    : input_cb,
    'command'  : [pre_cb, run_cb],
    }
