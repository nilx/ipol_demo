/*
 * Copyright (c) 2011, Antoni Buades <toni.buades@uib.es>
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above
 *    copyright notice, this list of conditions and the following
 *    disclaimer in the documentation and/or other materials provided
 *    with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
 * THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
 * USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 *
 * The views and conclusions contained in the software and
 * documentation are those of the authors and should not be
 * interpreted as representing official policies, either expressed
 * or implied, of the copyright holder.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cmath>


#include "io_png.h"



/**
 * @brief Function to compute RMSE and PSNR between two images
 *
 * @param image1, image2 input images
 */


int main(int argc, char **argv)
{
	
	
	if (argc < 3)
	{
		printf("usage: img_mse_ipol image1 image2\n");
		exit(-1);
	}

	
	
	
	// read input1
	size_t nx,ny,nc;
	float *d_v = NULL;
	d_v = read_png_f32(argv[1], &nx, &ny, &nc);
	if (!d_v)
	{
		printf("error :: %s not found  or not a correct png image \n", argv[1]);
		exit(-1);
	}
	
	if (nc == 2) { nc = 1; }  // we do not use the alpha channel
	if (nc > 3) { nc = 3; }  // we do not use the alpha channel
	
	
	
	// read input2
	size_t nx2,ny2,nc2;
	float *d_v2 = NULL;
	d_v2 = read_png_f32(argv[2], &nx2, &ny2, &nc2);
	if (!d_v2)
	{
		printf("error :: %s not found  or not a correct png image \n", argv[2]);
		exit(-1);
	}
	
	
	if (nc2 == 2) { nc2 = 1; }  // we do not use the alpha channel
	if (nc2 > 3) { nc2 = 3; }  // we do not use the alpha channel
	
	
	
	// test if same size
	if (nc != nc2 || nx != nx2 || ny != ny2)
	{
		printf("error :: input images of different size or number of channels \n");
		exit(-1);
	}
	
	
	
	
	// variables
	int d_w = (int) nx; 
	int d_h = (int) ny; 
	int d_c = (int) nc; 
	
	int d_wh = d_w * d_h;
	
	
	
	// compute error and image difference
	float fDist = 0.0f;
	float fPSNR = 0.0f;
	
	
	for (int ii=0; ii < d_c ;  ii++)
	{
		
		for (int jj=0; jj < d_wh; jj++)
		{
		
			float dif = d_v[ ii * d_wh + jj] - d_v2[ii * d_wh + jj];
			fDist += dif * dif;
			
		}
		
	}
	
	
	fDist /= (float) (d_c * d_wh);
	fDist /= sqrtf(fDist);
	
	fPSNR = 10.0f * log10f(255.0f * 255.0f / (fDist * fDist));
	
	printf("RMSE: %2.2f\n", fDist);
	printf("PSNR: %2.2f\n", fPSNR);

	
}
