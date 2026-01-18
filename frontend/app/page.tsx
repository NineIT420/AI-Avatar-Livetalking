'use client';

import React, { useEffect } from 'react';
import { useWebRTC } from '@/hooks/useWebRTC';
import { useRecording } from '@/hooks/useRecording';
import { VideoPlayer } from '@/components/VideoPlayer';
import { Controls } from '@/components/Controls';
import { StatusDisplay } from '@/components/StatusDisplay';

export default function Home() {
  const { peerConnection, isConnected, connectionStatus, latency, sessionId, start, stop, videoRef, audioRef } = useWebRTC();
  const { isRecording, startRecord, stopRecord, error: recordingError } = useRecording();

  // Automatically start/stop recording when sessionId changes
  useEffect(() => {
    const manageRecording = async () => {
      if (sessionId !== null && !isRecording) {
        // Start recording when sessionId becomes available
        try {
          await startRecord(sessionId);
        } catch (error) {
          console.error('Failed to start recording:', error);
        }
      } else if (sessionId === null && isRecording) {
        // Stop recording when sessionId becomes null
        try {
          await stopRecord(sessionId!);
        } catch (error) {
          console.error('Failed to stop recording:', error);
        }
      }
    };

    manageRecording();
  }, [sessionId, isRecording, startRecord, stopRecord]);

  const handleStart = async () => {
    try {
      await start(true); // STUN server enabled
      // Recording will start automatically when sessionId becomes available
    } catch (error) {
      console.error('Failed to start WebRTC:', error);
      alert('Failed to start connection. Please check your browser permissions and try again.');
    }
  };

  const handleStop = () => {
    stop();
    // Recording will stop automatically when connection stops
  };


  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* Header */}
        <div className="mb-8 sm:mb-12">
          <h1 className="text-4xl sm:text-5xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent mb-2">
            NVIDIA A2F Demo
          </h1>
          <p className="text-slate-600 text-lg">Real-time video streaming with WebRTC technology</p>
        </div>

        <div className="space-y-6 sm:space-y-8">
          {/* Status Card */}
          <StatusDisplay status={connectionStatus} latency={latency} />
          
          {/* Controls Card */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-slate-200/50 p-6 sm:p-8">
            <h2 className="text-xl font-semibold text-slate-800 mb-6">Connection Controls</h2>
            <Controls
              isConnected={isConnected}
              onStart={handleStart}
              onStop={handleStop}
              error={recordingError}
            />
          </div>

          {/* Video Player Card */}
          <VideoPlayer videoRef={videoRef} audioRef={audioRef} />
        </div>
      </div>
    </main>
  );
}

