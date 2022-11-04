#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    vibes.py
#  
#    Copyright 2017 Alessandro Proglio <ale.proglio@gmail.com>
#
#    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
#    documentation files (the "Software"), to deal in the Software without restriction, including without limitation 
#    the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, 
#    and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
#    The above copyright notice and this permission notice shall be included in all copies or substantial 
#    portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED 
#    TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#     OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
#     DEALINGS IN THE SOFTWARE.

import logging
import numpy as np
import pyaudio

class VibesAnalyzer:

    def __init__(self, seconds=0.25, channel=0):
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 2
        self.RATE = 44100
        self.CHUNK = 882
        self.START = 0
        self.N = 512
        self.RECORD_SECONDS = seconds
        self.channel = channel

        self.spec_x = 0
        self.spec_y = 0
        self.data = []

        self.pa = pyaudio.PyAudio()
        self.listDevices()
        self.formatIsSupported()
        self.stream = self.pa.open(format = self.FORMAT,
            channels = self.CHANNELS, 
            rate = self.RATE, 
            input = True,
            output = False,
            input_device_index = 0,
            frames_per_buffer = self.CHUNK)
    
    def readChunks(self):
        """
        https://stackoverflow.com/questions/22636499/convert-multi-channel-pyaudio-into-numpy-array
        Convert a byte stream into a 2D numpy array with 
        shape (chunk_size, channels)
        Samples are interleaved, so for a stereo stream with left channel 
        of [L0, L1, L2, ...] and right channel of [R0, R1, R2, ...], the output 
        is ordered as [L0, R0, L1, R1, ...]
        """
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            chdata = self.stream.read(self.CHUNK)
            ret = np.fromstring(chdata, np.float32)
            chunk_length = len(ret) / channels
            assert chunk_length == int(chunk_length)
            ret = np.reshape(ret, (chunk_length, channels))
            self.data.append(ret[:, self.channel])

    def removeDCoffset():
        self.data -= np.mean(self.data)
        # we can also shift the zero frequency to the middle of the spectrum
        #self.data = np.fft.fftshift(self.data)

    def campiona(self):
        self.data = []
        self.readChunks()
        self.removeDCoffset()
        #self.normalizeInput()
        y = np.fft.fft(self.data)
        self.spec_x = np.fft.fftfreq(self.N, d = 1.0 / self.RATE)
        # trova frequenza maggiore di 1100 Hz o minore di 3500 Hz
        # centro del range in 2300 Hz, span +-1200 Hz
        i, = np.where( abs(self.spec_x - 2300.) <= 1200. )
        self.spec_y = [np.sqrt(c.real ** 2 + c.imag ** 2) for c in y]
        # self.spectralFlux()
        # self.threshold()
        # self.discretePeaks()
        
    def chiudi(self):
        self.pa.close(self.stream)

    def listDevices(self):
        info = self.pa.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (self.pa.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                print("Input Device id ", i, " - ", self.pa.get_device_info_by_host_api_device_index(0, i).get('name'))

    def formatIsSupported(self):
        try:
            self.pa.is_format_supported(self.RATE, 0, 1, self.FORMAT, None, None, None)
        except ValueError:
            logging.warning('the format is not supported', exc_info=True)
