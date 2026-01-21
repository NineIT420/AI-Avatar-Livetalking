import asyncio
import json
import logging
import threading
import time
from typing import Tuple, Dict, Optional, Set, Union
from av.frame import Frame
from av.packet import Packet
from av import AudioFrame
import fractions
import numpy as np

AUDIO_PTIME = 0.020
VIDEO_CLOCK_RATE = 90000
VIDEO_PTIME = 0.040
VIDEO_TIME_BASE = fractions.Fraction(1, VIDEO_CLOCK_RATE)
SAMPLE_RATE = 16000
AUDIO_TIME_BASE = fractions.Fraction(1, SAMPLE_RATE)

from aiortc import (
    MediaStreamTrack,
)

logging.basicConfig()
logger = logging.getLogger(__name__)
from app.utils.logger import logger as mylogger


class PlayerStreamTrack(MediaStreamTrack):
    def __init__(self, player, kind):
        super().__init__()
        self.kind = kind
        self._player = player
        self._queue = asyncio.Queue(maxsize=100)
        self.timelist = []
        self.current_frame_count = 0
        if self.kind == 'video':
            self.framecount = 0
            self.lasttime = time.perf_counter()
            self.totaltime = 0
    
    _start: float
    _timestamp: int

    async def next_timestamp(self) -> Tuple[int, fractions.Fraction]:
        if self.readyState != "live":
            raise Exception

        if not hasattr(self, "_start"):
            self._start = self._player.get_shared_start_time()
            self._timestamp = 0
            self.timelist.append(self._start)
            if self.kind == 'video':
                mylogger.info('video start (shared):%f',self._start)
            else:
                mylogger.info('audio start (shared):%f',self._start)

        if self.kind == 'video':
            self._timestamp += int(VIDEO_PTIME * VIDEO_CLOCK_RATE)
            self.current_frame_count += 1
            wait = self._start + self.current_frame_count * VIDEO_PTIME - time.time()
            if wait>0:
                await asyncio.sleep(wait)
            return self._timestamp, VIDEO_TIME_BASE
        else: #audio
            self._timestamp += int(AUDIO_PTIME * SAMPLE_RATE)
            self.current_frame_count += 1
            wait = self._start + self.current_frame_count * AUDIO_PTIME - time.time()
            if wait>0:
                await asyncio.sleep(wait)
            return self._timestamp, AUDIO_TIME_BASE

    async def recv(self) -> Union[Frame, Packet]:
        self._player._start(self)
        frame,eventpoint = await self._queue.get()
        pts, time_base = await self.next_timestamp()
        frame.pts = pts
        frame.time_base = time_base
        if eventpoint and self._player is not None:
            self._player.notify(eventpoint)
        if frame is None:
            self.stop()
            raise Exception
        if self.kind == 'video':
            self.totaltime += (time.perf_counter() - self.lasttime)
            self.framecount += 1
            self.lasttime = time.perf_counter()
            if self.framecount==100:
                mylogger.info(f"------actual avg final fps:{self.framecount/self.totaltime:.4f}")
                self.framecount = 0
                self.totaltime=0
        return frame
    
    def stop(self):
        super().stop()
        while not self._queue.empty():
            item = self._queue.get_nowait()
            del item
        if self._player is not None:
            self._player._stop(self)
            self._player = None

def player_worker_thread(
    quit_event,
    loop,
    container,
    audio_track,
    video_track
):
    try:
        mylogger.info("Starting render thread for lip-syncing")
        container.render(quit_event,loop,audio_track,video_track)
        mylogger.info("Render thread stopped")
    except Exception as e:
        mylogger.exception(f"Error in render thread: {e}")
        raise

class HumanPlayer:

    def __init__(
        self, nerfreal, format=None, options=None, timeout=None, loop=False, decode=True
    ):
        self.__thread: Optional[threading.Thread] = None
        self.__thread_quit: Optional[threading.Event] = None

        self.__started: Set[PlayerStreamTrack] = set()
        self.__audio: Optional[PlayerStreamTrack] = None
        self.__video: Optional[PlayerStreamTrack] = None

        self.__shared_start_time: Optional[float] = None
        self.__start_time_lock = threading.Lock()

        self.__audio = PlayerStreamTrack(self, kind="audio")
        self.__video = PlayerStreamTrack(self, kind="video")

        self.__container = nerfreal
        self.__loop = None
    
    def get_shared_start_time(self) -> float:
        with self.__start_time_lock:
            if self.__shared_start_time is None:
                self.__shared_start_time = time.time()
                mylogger.info('Shared start time initialized: %f', self.__shared_start_time)
            return self.__shared_start_time

    def notify(self,eventpoint):
        if self.__container is not None:
            self.__container.notify(eventpoint)

    @property
    def audio(self) -> MediaStreamTrack:
        return self.__audio

    @property
    def video(self) -> MediaStreamTrack:
        return self.__video

    def start_render(self, loop):
        if self.__thread is None:
            mylogger.info("Starting worker thread for lip-syncing render")
            self.__thread_quit = threading.Event()
            self.__loop = loop
            self.__thread = threading.Thread(
                name="media-player",
                target=player_worker_thread,
                args=(
                    self.__thread_quit,
                    loop,
                    self.__container,
                    self.__audio,
                    self.__video                   
                ),
            )
            self.__thread.start()
            mylogger.info("Worker thread started successfully")

    def _start(self, track: PlayerStreamTrack) -> None:
        self.__started.add(track)
        if self.__thread is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            self.start_render(loop)

    def _stop(self, track: PlayerStreamTrack) -> None:
        self.__started.discard(track)

        if not self.__started and self.__thread is not None:
            self.__log_debug("Stopping worker thread")
            self.__thread_quit.set()
            self.__thread.join()
            self.__thread = None

        if not self.__started and self.__container is not None:
            self.__container = None

    def __log_debug(self, msg: str, *args) -> None:
        mylogger.debug(f"HumanPlayer {msg}", *args)
