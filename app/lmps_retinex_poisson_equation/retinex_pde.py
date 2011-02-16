# copyright (C) 2009 
# Nicolas Limare, CMLA, ENS Cachan <nicolas.limare@cmla.ens-cachan.fr>
#
# licensed under GPLv3, see http://www.gnu.org/licenses/gpl-3.0.html
#
"""
PDE implementation of Retinex.
"""

ID = 'retinex_pde'
NAME = 'Retinex PDE'
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



PRIMES_2       = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
PRIMES_2_3     = [1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 27, 32, 
                  36, 48, 54, 64, 72, 81, 96, 108, 
                  128, 144, 162, 192, 216, 243, 256, 
                  288, 324, 384, 432, 486, 512, 
                  576, 648, 729, 768, 864, 972, 1024]
PRIMES_2_3_5   = [1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 
                  18, 20, 24, 25, 27, 30, 32, 
                  36, 40, 45, 48, 50, 54, 60, 64, 
                  72, 75, 80, 81, 90, 96, 100, 108, 120, 125, 128, 
                  135, 144, 150, 160, 162, 180, 192, 
                  200, 216, 225, 240, 243, 250, 256, 
                  270, 288, 300, 320, 324, 360, 375, 384, 
                  400, 405, 432, 450, 480, 486, 500, 512, 
                  540, 576, 600, 625, 640, 648, 675, 720, 729, 750, 768, 
                  800, 810, 864, 900, 960, 972, 1000, 1024]
PRIMES_2_3_5_7 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 16, 
                  18, 20, 21, 24, 25, 27, 28, 30, 32, 
                  35, 36, 40, 42, 45, 48, 49, 50, 54, 56, 60, 63, 64, 
                  70, 72, 75, 80, 81, 84, 90, 96, 
                  98, 100, 105, 108, 112, 120, 125, 126, 128, 
                  135, 140, 144, 147, 150, 160, 162, 168, 175, 180, 189, 192, 
                  196, 200, 210, 216, 224, 225, 240, 243, 245, 250, 252, 256, 
                  270, 280, 288, 294, 300, 315, 320, 
                  324, 336, 343, 350, 360, 375, 378, 384, 
                  392, 400, 405, 420, 432, 441, 448, 
                  450, 480, 486, 490, 500, 504, 512, 
                  525, 540, 560, 567, 576, 588, 600, 625, 630, 640, 
                  648, 672, 675, 686, 700, 720, 729, 735, 750, 756, 768, 
                  784, 800, 810, 840, 864, 875, 882, 896, 
                  900, 945, 960, 972, 980, 1000, 1008, 1024]

def closest_prime(primes=None, number=1):
    """
    fine the closest prime in the primes list
    """
    if None == primes:
        return None
    if number in primes:
        return number   
    elif number >= primes[-1]:
        return primes[-1]
    elif number <= primes[0]:
        return primes[0]
    else:
        i = 0
        while number > primes[i]:
            i += 1
        if (primes[i] - number) > (number - primes[i-1]):
            return primes[i]
        else:
            return primes[i-1]

def input_retinex():
    """
    custom input message
    """
    page = """
<div class="crosslinks">
<ul>
<li><a href="http://www.ipol.im/pub/algo/lmps_retinex_poisson_equation/">algorithm</a></li>
<li><a class="active" href="/megawave/demo/retinex_pde/">demonstration</a></li>
<li><a href="/megawave/demo/retinex_pde/archive/">archive</a></li>
<!-- <li><a href="">forum</a></li> -->
</ul>
</div>
<h1>%s</h1>
""" % NAME
    page += html_form_upload(input_nb=INPUT_NB, url=url_start(module_id=ID),
                             info="""\
This program transforms an image according to the PDE implementation
of the Retinex theory.
</p><p>
Please select an image.  It may be slightly resized
for an efficient FFT.<br />
Very large images will be downsized.<br />
Retinex PDE will run with the threshold value t=4; you can run it
again later with another value.""")
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

def pre_retinex(key):
    """
    convert the image, prepare for retinex_pde
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
<p>The Retinex PDE algorithm is running, please wait for a few seconds,
your browser will be redirected to the result.</p>
"""
    # resize
    size = get_image_info(os.path.join(folder, 'input.tiff'))['size']
    primes = PRIMES_2_3_5_7
    if (size[0] <= primes[-1]) and (size[1] <= primes[-1]):
        newsize = (closest_prime(primes, size[0]),
                   closest_prime(primes, size[1]))
    else:
        scale = float(primes[-1]) / max(size)
        newsize = (closest_prime(primes, size[0] * scale),
                   closest_prime(primes, size[1] * scale))
    assert resize_image(filename='input.tiff', cwd=folder,
                        size="%ix%i!" % newsize)
    if size != newsize:
        page += """\
<p style="font-size:80%%">The image has been resized to %i x %i for a better
computation time.</p>""" % newsize

    page += """\
<p style="font-size:80%%">Safari 3.x users, follow <a href="%s">this
link</a> if your browser seems stuck.</p>
"""  % url_step(module_id=ID, key=key, step=1)
    assert True == convert_image(from_file='input.tiff',
                                 to_file='input.jpeg',
                                 cwd=tmp_folder(key), format='JPEG',
                                 options=['-quality', '100',
                                          '-interlace', 'Line'])
    page += """\
<img src="%s"/></div>
""" % os.path.join(tmp_url(key), 'input.jpeg')

    print http_header_redir(url=url_step(module_id=ID, key=key, step=1))
    print http_header_content()
    print
    print html_page(header=HTML_HEADER, title=HTML_TITLE,
                    body=html_body(content=page))
    return

def run_retinex(key):
    """
    process Retinex
    """
    # run retinex_pde
    page = "<h1>%s</h1>" % NAME
    folder = tmp_folder(key)
    try:
        import cgi
        query = cgi.parse_qs(cgi.os.environ['QUERY_STRING'])
        t_param = int(query['_t'][0])
    except Exception:
        t_param = 4
    if (0 > t_param) or (255 < t_param):
        t_param = 4
    start_time = time.time()
    retinex = process_mw(module_id=ID, program='retinex_pde.sh', 
                         options="%i" % t_param, cwd=folder)
    retinex.wait()
    total_time = time.time() - start_time
    assert 0 == retinex.returncode
    assert True == convert_image(from_file='balanced.tiff',
                                 to_file='balanced.jpeg',
                                 cwd=tmp_folder(key), format='JPEG',
                                 options=['-quality', '100',
                                          '-interlace', 'Line'])
    assert True == convert_image(from_file="retinex.tiff",
                                 to_file="retinex_%i.jpeg" % t_param,
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
with the threshold parameter t = 
<select name="_t">
  <option value="0">0</option>
  <option value="2">2</option>
  <option value="4" selected>4</option>
  <option value="6">6</option>
  <option value="8">8</option>
  <option value="10">10</option>
  <option value="15">15</option>
</select>
</form>"""

    page += """\
<p>Computation for the Retinex PDE took %.2fs.</p>
""" %  total_time
    page += """\
<div style="float:left; margin:5px"><h2>Retinex-corrected image,
threshold t=%i</h2>
<img src="%s"/></div>
""" % (t_param, os.path.join(tmp_url(key), "retinex_%i.jpeg" % t_param))
    page += """\
<div style="float:left; margin:5px"><h2>Color balanced image</h2>
<img src="%s"/></div>
""" % os.path.join(tmp_url(key), 'balanced.jpeg')
    page += """\
<div style="float:left; margin:5px"><h2>Original image</h2>
<img src="%s"/></div>
""" % os.path.join(tmp_url(key), 'input.jpeg')

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
        convert_image(from_file='balanced.jpeg',
                      to_file='_balanced.jpeg',
                      cwd=tmp_folder(key), format='JPEG',
                      options=['-resize', '128x128!'])
        convert_image(from_file="retinex_%i.jpeg" % t_param,
                      to_file="_retinex_%i.jpeg" % t_param,
                      cwd=tmp_folder(key), format='JPEG',
                      options=['-resize', '128x128!'])
        # original image
        convert_image(from_file='input_0',
                      to_file='original.jpeg',
                      cwd=tmp_folder(key), format='JPEG',
                      options=['-quality', '100',
                               '-interlace', 'Line'])
        os.unlink(os.path.join(tmp_folder(key), 'input_0'))
        convert_image(from_file='original.jpeg',
                      to_file='_original.jpeg',
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
    'input'    : input_retinex,
    'command'  : [pre_retinex, run_retinex],
    }
