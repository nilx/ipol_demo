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

#include "mt19937ar.h"

/**
 * @brief Function to add a white Gaussian noise to a float image 
 * 
 * @param u input float image
 * @param v output float image
 * @param std standard deviation of the white Gaussian noise
 * @param randinit integer value used to compute the seed of the random generator
 * @param size image size
 * 
 * @remark The function uses the Mersenne Twister pseudo-random number mt19937ar 
 * @see mt19937ar.c
 */

void fiAddNoise(float *u, float *v, float std, long int randinit, int size)   
{
	
	mt_init_genrand((unsigned long int) time (NULL) + (unsigned long int) getpid()  + (unsigned long int) randinit);

	for (int i=0; i< size; i++) 
	{
		
		double a=mt_genrand_res53();
		double b=mt_genrand_res53();
		double z = (double)(std)*sqrt(-2.0*log(a))*cos(2.0*M_PI*b);
		
		v[i] =  u[i] + (float) z;
		
	}		
	
}

