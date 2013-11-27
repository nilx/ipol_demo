"""
The core algo runner 
"""

def run_algo(self, stdout=None, timeout=False):
    """
    The core algo runner
    could also be called by a batch processor
    this one needs no parameter
    """

    high_threshold_canny = self.cfg['param']['high_threshold_canny'] 
    initial_distortion_parameter = self.cfg['param']['initial_distortion_parameter'] 
    final_distortion_parameter = self.cfg['param']['final_distortion_parameter'] 
    distance_point_line_max_hough = self.cfg['param']['distance_point_line_max_hough'] 
    angle_point_orientation_max_difference = self.cfg['param']['angle_point_orientation_max_difference'] 

    # Run the code
    self.wait_proc(self.run_proc(['lens_distortion_correction_division_model_1p',
        'input_0.png', 'output_canny.png', 'output_hough.png', 'output_corrected_image.png',
        str(high_threshold_canny), str(initial_distortion_parameter), 
        str(final_distortion_parameter), str(distance_point_line_max_hough), 
        str(angle_point_orientation_max_difference), 'primitives.txt'],
        stdout=stdout, stderr=stdout), timeout)
