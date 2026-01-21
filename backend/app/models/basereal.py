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

from ..utils.logger import logger

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
    while not quit_event.is_set():
        stream.write(queue.get(block=True))
    stream.close()

class BaseReal:
    def __init__(self, opt):
        self.opt = opt
        self.sample_rate = 16000
        self.chunk = self.sample_rate // opt.fps
        self.sessionid = self.opt.sessionid

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
        
        self.video_cap = None
        self.video_path = os.path.expanduser(getattr(opt, 'video', ''))
        self.video_frame_index = 0
        self.video_total_frames = 0
        if self.video_path and os.path.exists(self.video_path):
            self.video_cap = cv2.VideoCapture(self.video_path)
            if not self.video_cap.isOpened():
                logger.warning(f"Failed to open video file: {self.video_path}")
                self.video_cap = None
            else:
                self.video_total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                logger.info(f"Video file loaded for silence streaming: {self.video_path} (total frames: {self.video_total_frames})")
        elif self.video_path:
            logger.warning(f"Video file not found: {self.video_path}")

    def __del__(self):
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

    def put_audio_chunk(self,filebyte,chunk_index:int,datainfo:dict={}):
        try:
            input_stream = BytesIO(filebyte)
            stream = self.__create_bytes_stream(input_stream)
            streamlen = stream.shape[0]
            idx=0
            while streamlen >= self.chunk:
                self.put_audio_frame(stream[idx:idx+self.chunk],datainfo)
                streamlen -= self.chunk
                idx += self.chunk
        except Exception as e:
            logger.warning(f'Failed to decode streaming audio chunk {chunk_index}: {e}. Skipping chunk.')
    
    def __create_bytes_stream(self,byte_stream):
        stream, sample_rate = sf.read(byte_stream)
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
        if self.recording:
            return

        acommand = ['ffmpeg',
                    '-y', '-vn',
                    '-f', 's16le',
                    '-ac', '1',
                    '-ar', '16000',
                    '-i', '-',
                    '-acodec', 'aac',
                    f'temp{self.opt.sessionid}.aac']
        self._record_audio_pipe = subprocess.Popen(acommand, shell=False, stdin=subprocess.PIPE)

        self.recording = True
    
    def record_video_data(self,image):
        if self.width == 0:
            self.height,self.width,_ = image.shape

        if self.recording:
            if self._record_video_pipe is None:
                command = ['ffmpeg',
                          '-y', '-an',
                          '-f', 'rawvideo',
                          '-vcodec','rawvideo',
                          '-pix_fmt', 'bgr24',
                          '-s', "{}x{}".format(self.width, self.height),
                          '-r', str(25),
                          '-i', '-',
                          '-pix_fmt', 'yuv420p',
                          '-vcodec', "h264",
                          f'temp{self.opt.sessionid}.mp4']
                self._record_video_pipe = subprocess.Popen(command, shell=False, stdin=subprocess.PIPE)

            self._record_video_pipe.stdin.write(image.tobytes())

    def record_audio_data(self,frame):
        if self.recording and self._record_audio_pipe is not None:
            try:
                if not isinstance(frame, np.ndarray):
                    logger.warning(f"Audio frame is not a numpy array: {type(frame)}")
                    return
                if frame.size == 0:
                    logger.warning("Audio frame is empty")
                    return
                if frame.dtype != np.int16:
                    frame = frame.astype(np.int16)
                data = frame.tobytes()
                self._record_audio_pipe.stdin.write(data)
                self._record_audio_pipe.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                logger.warning(f"Error writing audio to pipe: {e}")
                self.recording = False
            except Exception as e:
                logger.warning(f"Unexpected error writing audio: {e}")
                self.recording = False
    
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
        if not self.recording:
            return
        self.recording = False 
        
        try:
            if self._record_video_pipe is not None:
                self._record_video_pipe.stdin.flush()
                self._record_video_pipe.stdin.close()
                self._record_video_pipe.wait()
        except Exception as e:
            logger.warning(f"Error closing video pipe: {e}")
        
        try:
            self._record_audio_pipe.stdin.flush()
            self._record_audio_pipe.stdin.close()
            self._record_audio_pipe.wait()
        except Exception as e:
            logger.warning(f"Error closing audio pipe: {e}")
        
        audio_file = f'temp{self.opt.sessionid}.aac'
        video_file = f'temp{self.opt.sessionid}.mp4'
        output_file = 'data/record.mp4'
        
        if not os.path.exists(audio_file):
            logger.error(f"Audio file not found: {audio_file}")
            return
        if not os.path.exists(video_file):
            logger.error(f"Video file not found: {video_file}")
            return
        
        audio_file_size = os.path.getsize(audio_file) if os.path.exists(audio_file) else 0
        if audio_file_size == 0:
            logger.warning(f"Audio file is empty: {audio_file}. Will generate silent audio track.")
            try:
                probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_file]
                result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
                video_duration = float(result.stdout.strip())
                logger.info(f"Video duration: {video_duration} seconds")
                
                silent_audio_file = f'temp{self.opt.sessionid}_silent.aac'
                silent_cmd = [
                    'ffmpeg', '-y', '-f', 'lavfi',
                    '-i', f'anullsrc=channel_layout=mono:sample_rate=16000',
                    '-t', str(video_duration),
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    silent_audio_file
                ]
                subprocess.run(silent_cmd, capture_output=True, text=True, check=True)
                audio_file = silent_audio_file
                logger.info(f"Generated silent audio track: {audio_file}")
            except Exception as e:
                logger.error(f"Failed to generate silent audio: {e}")
                
        if os.path.getsize(video_file) == 0:
            logger.error(f"Video file is empty: {video_file}")
            return
        
        os.makedirs('data', exist_ok=True)
        
        cmd_combine = [
            'ffmpeg', '-y',
            '-i', video_file,
            '-i', audio_file,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-shortest',
            '-map', '0:v:0',
            '-map', '1:a:0',
            output_file
        ]
        
        try:
            result = subprocess.run(cmd_combine, capture_output=True, text=True, check=True)
            logger.info(f"Recording saved to {output_file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg combine failed: {e.stderr}")
            logger.error(f"Command: {' '.join(cmd_combine)}")
            cmd_combine_fallback = [
                'ffmpeg', '-y',
                '-i', video_file,
                '-i', audio_file,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-shortest',
                output_file
            ]
            try:
                result = subprocess.run(cmd_combine_fallback, capture_output=True, text=True, check=True)
                logger.info(f"Recording saved to {output_file} (using fallback command)")
            except subprocess.CalledProcessError as e2:
                logger.error(f"FFmpeg fallback also failed: {e2.stderr}")
                logger.warning("Attempting to save video without audio")
                cmd_video_only = [
                    'ffmpeg', '-y',
                    '-i', video_file,
                    '-c:v', 'copy',
                    output_file
                ]
                try:
                    result = subprocess.run(cmd_video_only, capture_output=True, text=True, check=True)
                    logger.warning(f"Recording saved to {output_file} (video only, no audio)")
                except subprocess.CalledProcessError as e3:
                    logger.error(f"Failed to save video: {e3.stderr}")
        except Exception as e:
            logger.error(f"Error combining audio/video: {e}")

    def mirror_index(self,size, index):
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
            self.curr_state = 1
        return stream
    
    def set_custom_state(self,audiotype, reinit=True):
        if self.custom_audio_index.get(audiotype) is None:
            return
        self.curr_state = audiotype
        if reinit:
            self.custom_audio_index[audiotype] = 0
            self.custom_index[audiotype] = 0
            
    def process_frames(self,quit_event,loop=None,audio_track=None,video_track=None):
        enable_transition = False
        
        if enable_transition:
            _last_speaking = False
            _transition_start = time.time()
            _transition_duration = 0.1
            _last_silent_frame = None
            _last_speaking_frame = None
        
        if self.opt.transport=='virtualcam':
            import pyvirtualcam
            vircam = None

            audio_tmp = queue.Queue(maxsize=3000)
            audio_thread = Thread(target=play_audio, args=(quit_event,audio_tmp,), daemon=True, name="pyaudio_stream")
            audio_thread.start()
        
        while not quit_event.is_set():
            try:
                res_frame,idx,audio_frames = self.res_frame_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue
            
            if enable_transition:
                current_speaking = not (audio_frames[0][1]!=0 and audio_frames[1][1]!=0)
                if current_speaking != _last_speaking:
                    logger.info(f"状态切换：{'说话' if _last_speaking else '静音'} → {'说话' if current_speaking else '静音'}")
                    _transition_start = time.time()
                _last_speaking = current_speaking

            if audio_frames[0][1]!=0 and audio_frames[1][1]!=0:
                self.speaking = False
                audiotype = audio_frames[0][1]
                
                if self.video_cap is not None and self.video_cap.isOpened():
                    ret, target_frame = self.video_cap.read()
                    if not ret:
                        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, target_frame = self.video_cap.read()
                        if not ret:
                            logger.warning("Failed to read frame from video, falling back to default")
                            if self.custom_index.get(audiotype) is not None:
                                mirindex = self.mirror_index(len(self.custom_img_cycle[audiotype]),self.custom_index[audiotype])
                                target_frame = self.custom_img_cycle[audiotype][mirindex]
                                self.custom_index[audiotype] += 1
                            else:
                                target_frame = self.frame_list_cycle[idx]
                    self.video_frame_index += 1
                elif self.custom_index.get(audiotype) is not None:
                    mirindex = self.mirror_index(len(self.custom_img_cycle[audiotype]),self.custom_index[audiotype])
                    target_frame = self.custom_img_cycle[audiotype][mirindex]
                    self.custom_index[audiotype] += 1
                else:
                    target_frame = self.frame_list_cycle[idx]
                
                if enable_transition:
                    if time.time() - _transition_start < _transition_duration and _last_speaking_frame is not None:
                        alpha = min(1.0, (time.time() - _transition_start) / _transition_duration)
                        combine_frame = cv2.addWeighted(_last_speaking_frame, 1-alpha, target_frame, alpha, 0)
                    else:
                        combine_frame = target_frame
                    _last_silent_frame = combine_frame.copy()
                else:
                    combine_frame = target_frame
            else:
                self.speaking = True
                try:
                    current_frame = self.paste_back_frame(res_frame,idx)
                except Exception as e:
                    logger.warning(f"paste_back_frame error: {e}")
                    continue
                if enable_transition:
                    if time.time() - _transition_start < _transition_duration and _last_silent_frame is not None:
                        alpha = min(1.0, (time.time() - _transition_start) / _transition_duration)
                        combine_frame = cv2.addWeighted(_last_silent_frame, 1-alpha, current_frame, alpha, 0)
                    else:
                        combine_frame = current_frame
                    _last_speaking_frame = combine_frame.copy()
                else:
                    combine_frame = current_frame

            if self.opt.transport=='virtualcam':
                if vircam==None:
                    height, width,_= combine_frame.shape
                    vircam = pyvirtualcam.Camera(width=width, height=height, fps=25, fmt=pyvirtualcam.PixelFormat.BGR,print_fps=True)
                vircam.send(combine_frame)
            else:
                image = combine_frame
                new_frame = VideoFrame.from_ndarray(image, format="bgr24")
                asyncio.run_coroutine_threadsafe(video_track._queue.put((new_frame,None)), loop)
            self.record_video_data(combine_frame)

            for audio_frame in audio_frames:
                frame,type,eventpoint = audio_frame
                frame = (frame * 32767).astype(np.int16)

                if self.opt.transport=='virtualcam':
                    audio_tmp.put(frame.tobytes())
                else:
                    new_frame = AudioFrame(format='s16', layout='mono', samples=frame.shape[0])
                    new_frame.planes[0].update(frame.tobytes())
                    new_frame.sample_rate=16000
                    asyncio.run_coroutine_threadsafe(audio_track._queue.put((new_frame,eventpoint)), loop)
                self.record_audio_data(frame)
            if self.opt.transport=='virtualcam':
                vircam.sleep_until_next_frame()
        if self.opt.transport=='virtualcam':
            audio_thread.join()
            vircam.close()
        logger.info('basereal process_frames thread stop') 
    
        