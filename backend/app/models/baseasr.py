import time
import numpy as np
from scipy import signal
from scipy.fft import rfft, rfftfreq

import queue
from queue import Queue
import torch.multiprocessing as mp

from .basereal import BaseReal


class BaseASR:
    def __init__(self, opt, parent:BaseReal = None):
        self.opt = opt
        self.parent = parent

        self.fps = opt.fps
        self.sample_rate = 16000
        self.chunk = self.sample_rate // self.fps
        self.queue = Queue()
        self.output_queue = mp.Queue()

        self.batch_size = opt.batch_size
        self.audio_gain = getattr(opt, 'audio_gain', 1.0)

        self.frames = []
        self.stride_left_size = opt.l
        self.stride_right_size = opt.r
        self.feat_queue = mp.Queue(8)

        self.vad_state = False
        self.vad_hysteresis_counter = 0
        self.vad_hysteresis_threshold = 1

    def flush_talk(self):
        self.queue.queue.clear()

    def put_audio_frame(self,audio_chunk,datainfo:dict):
        self.queue.put((audio_chunk,datainfo))

    def detect_voice_activity(self, frame):
        rms = np.sqrt(np.mean(frame**2))
        if rms < 0.005:
            return False

        fft = rfft(frame)
        freqs = rfftfreq(len(frame), 1/self.sample_rate)
        magnitude = np.abs(fft)

        speech_band_mask = (freqs >= 300) & (freqs <= 3400)
        speech_band_energy = np.sum(magnitude[speech_band_mask]**2)
        total_energy = np.sum(magnitude**2)

        if total_energy == 0:
            return False

        speech_ratio = speech_band_energy / total_energy

        if speech_band_energy > 0:
            spectral_centroid = np.sum(freqs[speech_band_mask] * magnitude[speech_band_mask]**2) / speech_band_energy
        else:
            spectral_centroid = 0

        zero_crossings = np.sum(np.abs(np.diff(np.sign(frame)))) / len(frame)

        formant_band_mask = (freqs >= 500) & (freqs <= 2000)
        formant_energy = np.sum(magnitude[formant_band_mask]**2)

        speech_criteria = [
            speech_ratio > 0.3,
            spectral_centroid > 600,
            zero_crossings > 0.05,
            formant_energy / total_energy > 0.10
        ]

        speech_score = sum(speech_criteria)

        return speech_score >= 2

    def get_audio_frame(self):
        try:
            frame,eventpoint = self.queue.get(block=True,timeout=0.01)
            if self.audio_gain != 1.0:
                frame = frame * self.audio_gain
                max_val = np.abs(frame).max()
                if max_val > 1.0:
                    frame = frame / max_val

            is_speech = self.detect_voice_activity(frame)

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
                type = 0
            else:
                type = 1
        except queue.Empty:
            if self.parent and self.parent.curr_state>1:
                frame = self.parent.get_audio_stream(self.parent.curr_state)
                type = self.parent.curr_state
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