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

import math
import torch
import numpy as np

import subprocess
import os
import time
import cv2
import glob
import resampy

import queue
from queue import Queue
from threading import Thread, Event
from io import BytesIO
import soundfile as sf

import asyncio
from av import AudioFrame, VideoFrame

import av
from fractions import Fraction

from ttsreal import EdgeTTS,SovitsTTS,XTTS,CosyVoiceTTS,FishTTS,TencentTTS,DoubaoTTS,IndexTTS2,AzureTTS
from logger import logger

from tqdm import tqdm
def read_imgs(img_list):
    frames = []
    logger.info('reading images...') 
    for img_path in tqdm(img_list):
        frame = cv2.imread(img_path)
        frames.append(frame)
    return frames

def play_audio(quit_event,queue):        
    import pyaudio
    p = pyaudio.PyAudio()
    stream = p.open(
        rate=16000,
        channels=1,
        format=8,
        output=True,
        output_device_index=1,
    )
    stream.start_stream()
    # while queue.qsize() <= 0:
    #     time.sleep(0.1)
    while not quit_event.is_set():
        stream.write(queue.get(block=True))
    stream.close()

class BaseReal:
    def __init__(self, opt):
        self.opt = opt
        self.sample_rate = 16000
        self.chunk = self.sample_rate // opt.fps # 320 samples per chunk (20ms * 16000 / 1000)
        self.sessionid = self.opt.sessionid

        if opt.tts == "edgetts":
            self.tts = EdgeTTS(opt,self)
        elif opt.tts == "gpt-sovits":
            self.tts = SovitsTTS(opt,self)
        elif opt.tts == "xtts":
            self.tts = XTTS(opt,self)
        elif opt.tts == "cosyvoice":
            self.tts = CosyVoiceTTS(opt,self)
        elif opt.tts == "fishtts":
            self.tts = FishTTS(opt,self)
        elif opt.tts == "tencent":
            self.tts = TencentTTS(opt,self)
        elif opt.tts == "doubao":
            self.tts = DoubaoTTS(opt,self)
        elif opt.tts == "indextts2":
            self.tts = IndexTTS2(opt,self)
        elif opt.tts == "azuretts":
            self.tts = AzureTTS(opt,self)

        self.speaking = False

        self.recording = False
        self._record_video_pipe = None
        self._record_audio_pipe = None
        self.width = self.height = 0

        self.curr_state=0
        self.custom_img_cycle = {}
        self.custom_audio_cycle = {}
        self.custom_audio_index = {}
        self.custom_index = {}
        self.custom_opt = {}
        self.__loadcustom()
        
        # Initialize video capture for streaming when no voice is input
        self.video_cap = None
        self.video_path = getattr(opt, 'video', '')
        if self.video_path and os.path.exists(self.video_path):
            self.video_cap = cv2.VideoCapture(self.video_path)
            if not self.video_cap.isOpened():
                logger.warning(f"Failed to open video file: {self.video_path}")
                self.video_cap = None
            else:
                logger.info(f"Video file loaded for silence streaming: {self.video_path}")
        elif self.video_path:
            logger.warning(f"Video file not found: {self.video_path}")

    def __del__(self):
        """Cleanup video capture on destruction"""
        if hasattr(self, 'video_cap') and self.video_cap is not None:
            self.video_cap.release()

    def put_msg_txt(self,msg,datainfo:dict={}):
        self.tts.put_msg_txt(msg,datainfo)
    
    def put_audio_frame(self,audio_chunk,datainfo:dict={}): #16khz 20ms pcm
        self.asr.put_audio_frame(audio_chunk,datainfo)

    def put_audio_file(self,filebyte,datainfo:dict={}): 
        input_stream = BytesIO(filebyte)
        stream = self.__create_bytes_stream(input_stream)
        streamlen = stream.shape[0]
        idx=0
        while streamlen >= self.chunk:  #and self.state==State.RUNNING
            self.put_audio_frame(stream[idx:idx+self.chunk],datainfo)
            streamlen -= self.chunk
            idx += self.chunk
    
    def __create_bytes_stream(self,byte_stream):
        #byte_stream=BytesIO(buffer)
        stream, sample_rate = sf.read(byte_stream) # [T*sample_rate,] float64
        logger.info(f'[INFO]put audio stream {sample_rate}: {stream.shape}')
        stream = stream.astype(np.float32)

        if stream.ndim > 1:
            logger.info(f'[WARN] audio has {stream.shape[1]} channels, only use the first.')
            stream = stream[:, 0]
    
        if sample_rate != self.sample_rate and stream.shape[0]>0:
            logger.info(f'[WARN] audio sample rate is {sample_rate}, resampling into {self.sample_rate}.')
            stream = resampy.resample(x=stream, sr_orig=sample_rate, sr_new=self.sample_rate)

        return stream

    def flush_talk(self):
        self.tts.flush_talk()
        self.asr.flush_talk()

    def is_speaking(self)->bool:
        return self.speaking
    
    def __loadcustom(self):
        for item in self.opt.customopt:
            logger.info(item)
            input_img_list = glob.glob(os.path.join(item['imgpath'], '*.[jpJP][pnPN]*[gG]'))
            input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
            self.custom_img_cycle[item['audiotype']] = read_imgs(input_img_list)
            self.custom_audio_cycle[item['audiotype']], sample_rate = sf.read(item['audiopath'], dtype='float32')
            self.custom_audio_index[item['audiotype']] = 0
            self.custom_index[item['audiotype']] = 0
            self.custom_opt[item['audiotype']] = item

    def init_customindex(self):
        self.curr_state=0
        for key in self.custom_audio_index:
            self.custom_audio_index[key]=0
        for key in self.custom_index:
            self.custom_index[key]=0

    def notify(self,eventpoint):
        logger.info("notify:%s",eventpoint)

    def start_recording(self):
        """开始录制视频"""
        if self.recording:
            return

        command = ['ffmpeg',
                    '-y', '-an',
                    '-f', 'rawvideo',
                    '-vcodec','rawvideo',
                    '-pix_fmt', 'bgr24', #像素格式
                    '-s', "{}x{}".format(self.width, self.height),
                    '-r', str(25),
                    '-i', '-',
                    '-pix_fmt', 'yuv420p', 
                    '-vcodec', "h264",
                    #'-f' , 'flv',                  
                    f'temp{self.opt.sessionid}.mp4']
        self._record_video_pipe = subprocess.Popen(command, shell=False, stdin=subprocess.PIPE)

        acommand = ['ffmpeg',
                    '-y', '-vn',
                    '-f', 's16le',
                    #'-acodec','pcm_s16le',
                    '-ac', '1',
                    '-ar', '16000',
                    '-i', '-',
                    '-acodec', 'aac',
                    #'-f' , 'wav',                  
                    f'temp{self.opt.sessionid}.aac']
        self._record_audio_pipe = subprocess.Popen(acommand, shell=False, stdin=subprocess.PIPE)

        self.recording = True
        # self.recordq_video.queue.clear()
        # self.recordq_audio.queue.clear()
        # self.container = av.open(path, mode="w")
    
        # process_thread = Thread(target=self.record_frame, args=())
        # process_thread.start()
    
    def record_video_data(self,image):
        if self.width == 0:
            print("image.shape:",image.shape)
            self.height,self.width,_ = image.shape
        if self.recording:
            self._record_video_pipe.stdin.write(image.tostring())

    def record_audio_data(self,frame):
        if self.recording:
            self._record_audio_pipe.stdin.write(frame.tostring())
    
    # def record_frame(self): 
    #     videostream = self.container.add_stream("libx264", rate=25)
    #     videostream.codec_context.time_base = Fraction(1, 25)
    #     audiostream = self.container.add_stream("aac")
    #     audiostream.codec_context.time_base = Fraction(1, 16000)
    #     init = True
    #     framenum = 0       
    #     while self.recording:
    #         try:
    #             videoframe = self.recordq_video.get(block=True, timeout=1)
    #             videoframe.pts = framenum #int(round(framenum*0.04 / videostream.codec_context.time_base))
    #             videoframe.dts = videoframe.pts
    #             if init:
    #                 videostream.width = videoframe.width
    #                 videostream.height = videoframe.height
    #                 init = False
    #             for packet in videostream.encode(videoframe):
    #                 self.container.mux(packet)
    #             for k in range(2):
    #                 audioframe = self.recordq_audio.get(block=True, timeout=1)
    #                 audioframe.pts = int(round((framenum*2+k)*0.02 / audiostream.codec_context.time_base))
    #                 audioframe.dts = audioframe.pts
    #                 for packet in audiostream.encode(audioframe):
    #                     self.container.mux(packet)
    #             framenum += 1
    #         except queue.Empty:
    #             print('record queue empty,')
    #             continue
    #         except Exception as e:
    #             print(e)
    #             #break
    #     for packet in videostream.encode(None):
    #         self.container.mux(packet)
    #     for packet in audiostream.encode(None):
    #         self.container.mux(packet)
    #     self.container.close()
    #     self.recordq_video.queue.clear()
    #     self.recordq_audio.queue.clear()
    #     print('record thread stop')
		
    def stop_recording(self):
        """停止录制视频"""
        if not self.recording:
            return
        self.recording = False 
        self._record_video_pipe.stdin.close()  #wait() 
        self._record_video_pipe.wait()
        self._record_audio_pipe.stdin.close()
        self._record_audio_pipe.wait()
        cmd_combine_audio = f"ffmpeg -y -i temp{self.opt.sessionid}.aac -i temp{self.opt.sessionid}.mp4 -c:v copy -c:a copy data/record.mp4"
        os.system(cmd_combine_audio) 
        #os.remove(output_path)

    def mirror_index(self,size, index):
        #size = len(self.coord_list_cycle)
        turn = index // size
        res = index % size
        if turn % 2 == 0:
            return res
        else:
            return size - res - 1 
    
    def get_audio_stream(self,audiotype):
        idx = self.custom_audio_index[audiotype]
        stream = self.custom_audio_cycle[audiotype][idx:idx+self.chunk]
        self.custom_audio_index[audiotype] += self.chunk
        if self.custom_audio_index[audiotype]>=self.custom_audio_cycle[audiotype].shape[0]:
            self.curr_state = 1  #当前视频不循环播放，切换到静音状态
        return stream
    
    def set_custom_state(self,audiotype, reinit=True):
        print('set_custom_state:',audiotype)
        if self.custom_audio_index.get(audiotype) is None:
            return
        self.curr_state = audiotype
        if reinit:
            self.custom_audio_index[audiotype] = 0
            self.custom_index[audiotype] = 0

    def process_frames(self,quit_event,loop=None,audio_track=None,video_track=None):
        enable_transition = False  # 设置为False禁用过渡效果，True启用
        
        # Frame age tracking - only drop truly stale frames (very conservative)
        frame_drop_threshold = 2.0  # Only drop frames older than 2 seconds (very stale)
        frame_timestamps = {}  # Track frame ages
        max_timestamp_cache = 100  # Keep only last 100 timestamps
        
        # A/V synchronization monitoring
        sync_check_counter = 0
        sync_check_interval = 50  # Check sync every 50 frames
        last_sync_warning = 0
        
        if enable_transition:
            _last_speaking = False
            _transition_start = time.time()
            _transition_duration = 0.1  # 过渡时间
            _last_silent_frame = None  # 静音帧缓存
            _last_speaking_frame = None  # 说话帧缓存
        
        if self.opt.transport=='virtualcam':
            import pyvirtualcam
            vircam = None

            audio_tmp = queue.Queue(maxsize=3000)
            audio_thread = Thread(target=play_audio, args=(quit_event,audio_tmp,), daemon=True, name="pyaudio_stream")
            audio_thread.start()
        
        while not quit_event.is_set():
            try:
                res_frame,idx,audio_frames = self.res_frame_queue.get(block=True, timeout=1)
                current_time = time.time()
                
                # Frame dropping: Check if frame is too old (Solution 3)
                if idx in frame_timestamps:
                    frame_age = current_time - frame_timestamps[idx]
                    if frame_age > frame_drop_threshold:
                        logger.debug(f"Dropping stale frame {idx}, age: {frame_age:.3f}s")
                        continue  # Skip this frame
                
                frame_timestamps[idx] = current_time
                
                # Clean old timestamps to prevent memory growth
                if len(frame_timestamps) > max_timestamp_cache:
                    oldest_idx = min(frame_timestamps.keys(), key=lambda k: frame_timestamps[k])
                    del frame_timestamps[oldest_idx]
            except queue.Empty:
                continue
            
            if enable_transition:
                # 检测状态变化
                current_speaking = not (audio_frames[0][1]!=0 and audio_frames[1][1]!=0)
                if current_speaking != _last_speaking:
                    logger.info(f"状态切换：{'说话' if _last_speaking else '静音'} → {'说话' if current_speaking else '静音'}")
                    _transition_start = time.time()
                _last_speaking = current_speaking

            if audio_frames[0][1]!=0 and audio_frames[1][1]!=0: #全为静音数据，只需要取fullimg
                self.speaking = False
                audiotype = audio_frames[0][1]
                
                # If video file is provided, stream from video when no voice is input
                if self.video_cap is not None and self.video_cap.isOpened():
                    ret, target_frame = self.video_cap.read()
                    if not ret:
                        # Video ended, restart from beginning
                        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, target_frame = self.video_cap.read()
                        if not ret:
                            logger.warning("Failed to read from video file, falling back to static frames")
                            target_frame = self.frame_list_cycle[idx]
                elif self.custom_index.get(audiotype) is not None: #有自定义视频
                    mirindex = self.mirror_index(len(self.custom_img_cycle[audiotype]),self.custom_index[audiotype])
                    target_frame = self.custom_img_cycle[audiotype][mirindex]
                    self.custom_index[audiotype] += 1
                else:
                    target_frame = self.frame_list_cycle[idx]
                
                if enable_transition:
                    # 说话→静音过渡
                    if time.time() - _transition_start < _transition_duration and _last_speaking_frame is not None:
                        alpha = min(1.0, (time.time() - _transition_start) / _transition_duration)
                        combine_frame = cv2.addWeighted(_last_speaking_frame, 1-alpha, target_frame, alpha, 0)
                    else:
                        combine_frame = target_frame
                    # 缓存静音帧
                    _last_silent_frame = combine_frame.copy()
                else:
                    combine_frame = target_frame
            else:
                self.speaking = True
                # Check if res_frame is None (shouldn't happen during speech, but handle it gracefully)
                if res_frame is None:
                    logger.warning(f"res_frame is None during speech at idx {idx}, using original frame")
                    combine_frame = self.frame_list_cycle[idx]
                else:
                    try:
                        current_frame = self.paste_back_frame(res_frame,idx)
                        if current_frame is None:
                            logger.warning(f"paste_back_frame returned None at idx {idx}, using original frame")
                            combine_frame = self.frame_list_cycle[idx]
                        else:
                            combine_frame = current_frame
                    except Exception as e:
                        logger.warning(f"paste_back_frame error: {e}")
                        combine_frame = self.frame_list_cycle[idx]
                if enable_transition:
                    # 静音→说话过渡
                    if time.time() - _transition_start < _transition_duration and _last_silent_frame is not None:
                        alpha = min(1.0, (time.time() - _transition_start) / _transition_duration)
                        combine_frame = cv2.addWeighted(_last_silent_frame, 1-alpha, combine_frame, alpha, 0)
                    # 缓存说话帧
                    _last_speaking_frame = combine_frame.copy()

            # Watermark removed
            if self.opt.transport=='virtualcam':
                if vircam==None:
                    height, width,_= combine_frame.shape
                    vircam = pyvirtualcam.Camera(width=width, height=height, fps=25, fmt=pyvirtualcam.PixelFormat.BGR,print_fps=True)
                vircam.send(combine_frame)
            else: #webrtc
                image = combine_frame
                new_frame = VideoFrame.from_ndarray(image, format="bgr24")
                
                # Synchronize audio and video queues to maintain A/V sync (Solution 4)
                # Check queue sizes and ensure they stay balanced
                video_queue_size = video_track._queue.qsize()
                audio_queue_size = audio_track._queue.qsize()
                
                # STRICT A/V SYNCHRONIZATION - Maintain 2:1 audio-to-video ratio
                # Re-check queue sizes right before queuing to ensure accurate sync
                video_queue_size = video_track._queue.qsize()
                audio_queue_size = audio_track._queue.qsize()
                
                # Calculate expected ratio: 2 audio frames per video frame
                expected_audio_frames = video_queue_size * 2
                audio_video_diff = audio_queue_size - expected_audio_frames
                
                # Monitor sync drift periodically
                sync_check_counter += 1
                if sync_check_counter >= sync_check_interval:
                    sync_check_counter = 0
                    if abs(audio_video_diff) > 10:  # Significant drift
                        current_time = time.time()
                        if current_time - last_sync_warning > 5.0:  # Warn at most every 5 seconds
                            logger.warning(f"A/V sync drift: audio={audio_queue_size}, video={video_queue_size}, expected_audio={expected_audio_frames}, diff={audio_video_diff}")
                            last_sync_warning = current_time
                
                # If audio is ahead of video (positive diff), wait for video to catch up
                if audio_video_diff > 5:  # Audio is 5+ frames ahead of expected
                    # Wait for video queue to catch up - maintains sync
                    wait_time = 0.01 * min(audio_video_diff // 2, 5)  # Max 50ms wait
                    time.sleep(wait_time)
                    video_queue_size = video_track._queue.qsize()  # Re-check
                    audio_queue_size = audio_track._queue.qsize()  # Re-check
                
                # If video queue is getting full, use backpressure (wait, don't skip)
                if video_queue_size >= 80:  # Queue getting full
                    # Wait longer to let queue drain - this creates backpressure upstream
                    wait_time = 0.04 * min((video_queue_size - 70) / 10, 2.0)  # Up to 80ms wait
                    time.sleep(wait_time)
                    video_queue_size = video_track._queue.qsize()  # Re-check
                
                # Always queue video frame - use blocking put (no timeout to ensure frame is queued)
                # If queue is full, wait for space - this ensures video is never lost
                max_wait_attempts = 10
                wait_attempt = 0
                queued = False
                
                while not queued and wait_attempt < max_wait_attempts:
                    try:
                        # Try to put frame - this will block if queue is full
                        future = asyncio.run_coroutine_threadsafe(video_track._queue.put((new_frame,None)), loop)
                        # Wait for put to complete - use longer timeout to ensure frame is queued
                        future.result(timeout=2.0)  # 2 second timeout - should be enough
                        queued = True
                    except Exception as e:
                        wait_attempt += 1
                        current_size = video_track._queue.qsize()
                        if current_size >= 95:
                            # Queue is still very full - wait a bit and retry
                            logger.debug(f"Video queue full ({current_size}), waiting for space (attempt {wait_attempt}/{max_wait_attempts})")
                            time.sleep(0.1)  # Wait 100ms for queue to drain
                        else:
                            # Queue has space now, retry immediately
                            continue
                
                if not queued:
                    # Last resort: log error but still try one more time with no timeout
                    logger.error(f"Video frame queuing failed after {max_wait_attempts} attempts, queue size: {video_track._queue.qsize()}")
                    try:
                        future = asyncio.run_coroutine_threadsafe(video_track._queue.put((new_frame,None)), loop)
                        future.result(timeout=None)  # Block indefinitely - frame MUST be queued
                    except Exception as e:
                        logger.critical(f"CRITICAL: Failed to queue video frame - video will be lost! Error: {e}")
            self.record_video_data(combine_frame)

            # Process audio frames - ensure ALL frames are queued
            audio_frames_queued = 0
            total_audio_frames = len(audio_frames)
            
            # Log audio frame processing for debugging
            if total_audio_frames == 0:
                logger.warning(f"No audio frames to process at idx {idx}")
            
            for audio_frame_idx, audio_frame in enumerate(audio_frames):
                frame,type,eventpoint = audio_frame
                
                # Skip silence frames (type != 0) - they don't need to be queued
                # But we still need to maintain the 2:1 ratio, so queue silence too
                frame = (frame * 32767).astype(np.int16)

                if self.opt.transport=='virtualcam':
                    audio_tmp.put(frame.tobytes()) #TODO
                else: #webrtc
                    new_frame = AudioFrame(format='s16', layout='mono', samples=frame.shape[0])
                    new_frame.planes[0].update(frame.tobytes())
                    new_frame.sample_rate=16000
                    
                    # STRICT A/V SYNCHRONIZATION - Maintain 2:1 audio-to-video ratio
                    # Re-check queue sizes right before queuing to ensure accurate sync
                    video_queue_size = video_track._queue.qsize()
                    audio_queue_size = audio_track._queue.qsize()
                    
                    # Calculate expected ratio: 2 audio frames per video frame
                    expected_audio_frames = video_queue_size * 2
                    audio_video_diff = audio_queue_size - expected_audio_frames
                    
                    # If audio is behind video (negative diff), we need to catch up
                    # Don't wait - just queue immediately to catch up
                    if audio_video_diff < -10:  # Audio is 10+ frames behind
                        # Audio is behind - queue immediately without any waits
                        logger.debug(f"Audio behind video: expected {expected_audio_frames}, actual {audio_queue_size}, diff: {audio_video_diff} - queuing immediately")
                    
                    # If audio is too far ahead of video, wait briefly to maintain sync
                    elif audio_video_diff > 15:  # Audio is 15+ frames ahead
                        # Wait briefly to let video catch up, but limit wait time
                        wait_time = 0.01 * min((audio_video_diff - 10) // 5, 1)  # Max 10ms wait
                        time.sleep(wait_time)
                        audio_queue_size = audio_track._queue.qsize()  # Re-check
                    
                    # ALWAYS queue audio frame - use blocking put with reasonable timeout
                    # Check queue size first - if not too full, queue immediately
                    current_queue_size = audio_track._queue.qsize()
                    
                    if current_queue_size < 95:  # Queue has space
                        # Queue immediately - should succeed quickly
                        try:
                            future = asyncio.run_coroutine_threadsafe(audio_track._queue.put((new_frame,eventpoint)), loop)
                            future.result(timeout=0.1)  # Short timeout if queue has space
                            audio_frames_queued += 1
                        except Exception as e:
                            # Queue might have filled up, retry with longer timeout
                            logger.debug(f"Audio queue filled during put, retrying: {e}")
                            try:
                                future = asyncio.run_coroutine_threadsafe(audio_track._queue.put((new_frame,eventpoint)), loop)
                                future.result(timeout=2.0)  # Longer timeout
                                audio_frames_queued += 1
                            except Exception as retry_e:
                                logger.warning(f"Audio frame queuing delayed, queue size: {audio_track._queue.qsize()}")
                                # Last resort: block indefinitely
                                try:
                                    future = asyncio.run_coroutine_threadsafe(audio_track._queue.put((new_frame,eventpoint)), loop)
                                    future.result(timeout=None)  # Block indefinitely
                                    audio_frames_queued += 1
                                except Exception as final_e:
                                    logger.critical(f"CRITICAL: Failed to queue audio frame! Error: {final_e}")
                    else:
                        # Queue is very full - wait a bit then queue with longer timeout
                        logger.debug(f"Audio queue very full ({current_queue_size}), waiting before queuing")
                        time.sleep(0.05)  # Brief wait for queue to drain
                        try:
                            future = asyncio.run_coroutine_threadsafe(audio_track._queue.put((new_frame,eventpoint)), loop)
                            future.result(timeout=5.0)  # Longer timeout for full queue
                            audio_frames_queued += 1
                        except Exception as e:
                            logger.warning(f"Audio frame queuing timeout, queue size: {audio_track._queue.qsize()}")
                            # Block indefinitely as last resort
                            try:
                                future = asyncio.run_coroutine_threadsafe(audio_track._queue.put((new_frame,eventpoint)), loop)
                                future.result(timeout=None)
                                audio_frames_queued += 1
                            except Exception as final_e:
                                logger.critical(f"CRITICAL: Failed to queue audio frame! Error: {final_e}")
            
            # Log audio frame queuing status (for debugging)
            if total_audio_frames > 0:
                if audio_frames_queued != total_audio_frames:
                    logger.warning(f"Audio frame queuing incomplete: {audio_frames_queued}/{total_audio_frames} frames queued at idx {idx}")
                elif audio_frames_queued == 0:
                    logger.error(f"CRITICAL: No audio frames were queued! Total frames: {total_audio_frames}, idx: {idx}")
                # Log successful queuing periodically (every 100 frames to avoid spam)
                elif idx % 100 == 0:
                    logger.debug(f"Audio frames queued successfully: {audio_frames_queued}/{total_audio_frames} at idx {idx}, queue size: {audio_track._queue.qsize() if audio_track else 'N/A'}")
                self.record_audio_data(frame)
            if self.opt.transport=='virtualcam':
                vircam.sleep_until_next_frame()
        if self.opt.transport=='virtualcam':
            audio_thread.join()
            vircam.close()
        
        # Clean up video capture
        if self.video_cap is not None:
            self.video_cap.release()
            logger.info('Video capture released')
        
        logger.info('basereal process_frames thread stop') 
    
    # def process_custom(self,audiotype:int,idx:int):
    #     if self.curr_state!=audiotype: #从推理切到口播
    #         if idx in self.switch_pos:  #在卡点位置可以切换
    #             self.curr_state=audiotype
    #             self.custom_index=0
    #     else:
    #         self.custom_index+=1