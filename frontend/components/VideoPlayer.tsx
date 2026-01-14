'use client';

import React, { useState, useEffect } from 'react';

interface VideoPlayerProps {
  videoRef: React.RefObject<HTMLVideoElement>;
  audioRef: React.RefObject<HTMLAudioElement>;
}

export function VideoPlayer({ videoRef, audioRef }: VideoPlayerProps) {
  const [hasVideo, setHasVideo] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const checkVideo = () => {
      setHasVideo(!!video.srcObject);
    };

    // Check periodically (simpler approach)
    const interval = setInterval(checkVideo, 500);
    checkVideo(); // Initial check

    return () => clearInterval(interval);
  }, [videoRef]);

  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-slate-200/50 p-6 sm:p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </div>
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Video Stream</h2>
          <p className="text-sm text-slate-500">Live video feed from server</p>
        </div>
      </div>
      
      <div className="relative inline-block">
        <div className="absolute -inset-1 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl blur opacity-25 group-hover:opacity-40 transition duration-300" />
        <div className="relative bg-slate-900 rounded-xl overflow-hidden shadow-2xl">
          <video
            ref={videoRef}
            className="w-full max-w-[400px] h-auto rounded-xl"
            autoPlay
            playsInline
            muted
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent pointer-events-none" />
          {!hasVideo && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-800/80 rounded-xl backdrop-blur-sm">
              <div className="text-center">
                <svg className="w-16 h-16 text-slate-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <p className="text-slate-300 font-medium">Waiting for video stream...</p>
                <p className="text-slate-500 text-sm mt-1">Start connection to begin streaming</p>
              </div>
            </div>
          )}
        </div>
      </div>
      <audio ref={audioRef} autoPlay />
    </div>
  );
}

