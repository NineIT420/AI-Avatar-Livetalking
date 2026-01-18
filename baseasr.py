###############################################################################
#  Copyright (C) 2024 LiveTalking@lipku https://github.com/lipku/LiveTalking
#  email: lipku@foxmail.com
# 
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import time
import numpy as np
from scipy import signal
from scipy.fft import rfft, rfftfreq

import queue
from queue import Queue
import torch.multiprocessing as mp

from basereal import BaseReal


class BaseASR:
    def __init__(self, opt, parent:BaseReal = None):
        self.opt = opt
        self.parent = parent

        self.fps = opt.fps # 20 ms per frame
        self.sample_rate = 16000
        self.chunk = self.sample_rate // self.fps # 320 samples per chunk (20ms * 16000 / 1000)
        self.queue = Queue()
        self.output_queue = mp.Queue()

        self.batch_size = opt.batch_size
        self.audio_gain = getattr(opt, 'audio_gain', 1.0)  # Audio gain multiplier for mouth movement amplification

        self.frames = []
        self.stride_left_size = opt.l
        self.stride_right_size = opt.r
        #self.context_size = 10
        self.feat_queue = mp.Queue(8)

        # Voice activity detection state
        self.vad_state = False  # Current VAD state
        self.vad_hysteresis_counter = 0  # Counter for hysteresis
        self.vad_hysteresis_threshold = 3  # Frames to confirm state change

        #self.warm_up()

    def flush_talk(self):
        self.queue.queue.clear()

    def put_audio_frame(self,audio_chunk,datainfo:dict): #16khz 20ms pcm
        self.queue.put((audio_chunk,datainfo))

    def detect_voice_activity(self, frame):
        """
        Advanced Voice Activity Detection to distinguish human speech from breathing and noise.
        Uses multiple spectral and temporal features to identify human speech patterns.
        """
        # Basic RMS energy check
        rms = np.sqrt(np.mean(frame**2))
        if rms < 0.005:  # Very quiet - definitely silence
            return False

        # Compute FFT for spectral analysis
        fft = rfft(frame)
        freqs = rfftfreq(len(frame), 1/self.sample_rate)
        magnitude = np.abs(fft)

        # Focus on speech frequency bands (300-3400 Hz where most speech energy resides)
        speech_band_mask = (freqs >= 300) & (freqs <= 3400)
        speech_band_energy = np.sum(magnitude[speech_band_mask]**2)
        total_energy = np.sum(magnitude**2)

        if total_energy == 0:
            return False

        # Speech band energy ratio (human speech has high energy in 300-3400 Hz band)
        speech_ratio = speech_band_energy / total_energy

        # Spectral centroid (speech tends to have higher centroid than breathing)
        if speech_band_energy > 0:
            spectral_centroid = np.sum(freqs[speech_band_mask] * magnitude[speech_band_mask]**2) / speech_band_energy
        else:
            spectral_centroid = 0

        # Zero-crossing rate (speech has more rapid amplitude changes than breathing)
        zero_crossings = np.sum(np.abs(np.diff(np.sign(frame)))) / len(frame)

        # Formant-like detection: Look for peaks in speech frequency ranges
        # Human speech typically has formants around 500-2000 Hz
        formant_band_mask = (freqs >= 500) & (freqs <= 2000)
        formant_energy = np.sum(magnitude[formant_band_mask]**2)

        # Breathing typically has:
        # - Low speech band ratio (< 0.3)
        # - Low spectral centroid (< 800 Hz)
        # - Low zero-crossing rate (< 0.1)
        # - Low formant energy relative to total

        speech_criteria = [
            speech_ratio > 0.4,  # Sufficient energy in speech bands
            spectral_centroid > 800,  # Higher frequency content than breathing
            zero_crossings > 0.08,  # More amplitude changes than breathing
            formant_energy / total_energy > 0.15  # Formant energy present
        ]

        # Require at least 3 out of 4 criteria for speech detection
        speech_score = sum(speech_criteria)

        return speech_score >= 3

    #return frame:audio pcm; type: 0-normal speak, 1-silence; eventpoint:custom event sync with audio
    def get_audio_frame(self):
        try:
            frame,eventpoint = self.queue.get(block=True,timeout=0.01)
            # Apply audio gain to amplify mouth movement for speech frames
            if self.audio_gain != 1.0:
                frame = frame * self.audio_gain
                # Prevent clipping by normalizing if too loud
                max_val = np.abs(frame).max()
                if max_val > 1.0:
                    frame = frame / max_val

            # Advanced Voice Activity Detection to distinguish human speech from breathing/noise
            is_speech = self.detect_voice_activity(frame)

            # Apply hysteresis to prevent rapid switching between speech/silence states
            if is_speech:
                if not self.vad_state:
                    self.vad_hysteresis_counter += 1
                    if self.vad_hysteresis_counter >= self.vad_hysteresis_threshold:
                        self.vad_state = True
                        self.vad_hysteresis_counter = 0
            else:
                if self.vad_state:
                    self.vad_hysteresis_counter += 1
                    if self.vad_hysteresis_counter >= self.vad_hysteresis_threshold:
                        self.vad_state = False
                        self.vad_hysteresis_counter = 0

            if self.vad_state:
                type = 0  # Human speech detected
            else:
                type = 1  # Silence, breathing, or background noise
            #print(f'[INFO] get frame {frame.shape}')
        except queue.Empty:
            if self.parent and self.parent.curr_state>1: #播放自定义音频
                frame = self.parent.get_audio_stream(self.parent.curr_state)
                type = self.parent.curr_state
                # Apply audio gain to custom audio too
                if self.audio_gain != 1.0:
                    frame = frame * self.audio_gain

                    
                    max_val = np.abs(frame).max()
                    if max_val > 1.0:
                        frame = frame / max_val
            else:
                frame = np.zeros(self.chunk, dtype=np.float32)
                type = 1
            eventpoint = None

        return frame,type,eventpoint 

    #return frame:audio pcm; type: 0-normal speak, 1-silence; eventpoint:custom event sync with audio
    def get_audio_out(self): 
        return self.output_queue.get()
    
    def warm_up(self):
        for _ in range(self.stride_left_size + self.stride_right_size):
            audio_frame,type,eventpoint=self.get_audio_frame()
            self.frames.append(audio_frame)
            self.output_queue.put((audio_frame,type,eventpoint))
        for _ in range(self.stride_left_size):
            self.output_queue.get()

    def run_step(self):
        pass

    def get_next_feat(self,block,timeout):        
        return self.feat_queue.get(block,timeout)