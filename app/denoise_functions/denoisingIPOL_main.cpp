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



#include "addnoise_function.h"
#include "libpng_io.h"

//YOUR INCLUDES



/**
 * @file   NAME_OF_YOUR_ALGORITHM.cpp
 * @brief  Main executable file for denoising algorithms
 *
 * It takes an input 'clean' image (that is, without noise), 
 * adds a Gaussian noise with standard deviation sigma,
 * and produces as output the noisy image and a denoised image.
 * The 'denoised image' is the result of applying YOUR_ALGORITHM to the noisy image
 *
 * @param image input ('clean') image
 * @param sigma standard deviation of Gaussian noise added to the input image
 * @param output_noisy output noisy image
 * @param output_denoised output denoised image
 *
 * @author YOUR NAME <yourname@yourinstitution>
 */


// usage: NAME_OF_YOUR_ALGORITHM input sigma output_noisy output_denoised

int main(int argc, char **argv)
{
	
	
	if (argc < 5)
	{
		printf("usage: NAME_OF_YOUR_ALGORITHM image sigma noisy denoised \n");
		exit(-1);
	}
	
	
	// read input
	size_t nx,ny,nc;
	float *d_v = NULL;
	d_v = read_png_f32(argv[1], &nx, &ny, &nc);
	if (!d_v)
	{
		printf("error :: %s not found  or not a correct png image \n", argv[1]);
		exit(-1);
	}

	

	
	// variables
	int d_w = (int) nx; 
	int d_h = (int) ny; 
	int d_c = (int) nc; 
	if (d_c == 2) { d_c = 1; }  // we do not use the alpha channel
	if (d_c > 3) { d_c = 3; }  // we do not use the alpha channel
	
	int d_wh = d_w * d_h;
	int d_whc = d_c * d_w * d_h;
	
	
	
	// test if image is really a color image even if it has more than one channel
	if (d_c > 1)  
	{	
		
		// dc equals 3
		int i=0;
		while (i < d_wh && d_v[i] == d_v[d_wh + i] && d_v[i] == d_v[2 * d_wh + i ])  { i++; }
		
		if (i == d_wh) d_c = 1;
		
	}
	
	
	
	// add noise
	float fSigma = atof(argv[2]);
	float *noisy = new float[d_whc];
	
	for (int i=0; i < d_c; i++)
	{
		fiAddNoise(&d_v[i * d_wh], &noisy[i * d_wh], fSigma, i, d_wh);
	}
	
	
	
	
	
	// denoise
	float **fpI = new float*[d_c];
	float **fpO = new float*[d_c];
	float *denoised = new float[d_whc];
	
	for (int ii=0; ii < d_c; ii++) 
	{
		
		fpI[ii] = &noisy[ii * d_wh];
		fpO[ii] = &denoised[ii * d_wh];
		
	}
	

	//CALL HERE YOUR DENOISING ALGORITHM 

	YOUR_DENOISING_ALGORITHM(fpI, fpO, other_parameters);

	/*
	Example: nlmeans denoising
	// denoise parameters depending on sigma
	int bloc = 8;	// research zone 17x17
	

	int win = 1;						// comparison window 3x3
	if (d_c == 3 && fSigma > 25) win = 2;		// comparison window 5x5
	else if (d_c == 1 && fSigma >= 15 && fSigma <= 27.5 ) win = 2;	// comparison window 5x5
	else if (d_c == 1 && fSigma > 27.5) win = 3;				// comparison window 7x7
	
	float fFiltPar = 0.55;
	
	nlmeans_ipol(win, bloc,	fSigma,	fFiltPar, fpI,	fpO, d_c, d_w, d_h);
	*/


	
	// save noisy and denoised images
	if (write_png_f32(argv[3], noisy, (size_t) d_w, (size_t) d_h, (size_t) d_c) != 0)
	{
		printf("... failed to save png image %s", argv[3]);
	} 

	if (write_png_f32(argv[4], denoised, (size_t) d_w, (size_t) d_h, (size_t) d_c) != 0)
	{
		printf("... failed to save png image %s", argv[4]);
	} 
	
	

	
}



