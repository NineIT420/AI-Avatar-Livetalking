import { useState, useRef, useCallback } from 'react';
import { startRecording, stopRecording, streamAudioChunk } from '@/services/api';

interface UseRecordingReturn {
  isRecording: boolean;
  startRecord: (sessionId: number) => Promise<void>;
  stopRecord: (sessionId: number) => Promise<void>;
  error: string | null;
}

export function useRecording(): UseRecordingReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const chunkIndexRef = useRef<number>(0);
  const audioChunksRef = useRef<Float32Array[]>([]); // For fallback batch processing

  const startRecord = useCallback(async (sessionId: number) => {
    try {
      setError(null);

      // Start server-side recording
      await startRecording(sessionId);

      // Start microphone audio recording with Web Audio API
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000, // Match backend expectations
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      });
      mediaStreamRef.current = stream;
      chunkIndexRef.current = 0;
      audioChunksRef.current = [];

      // Create AudioContext
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000
      });

      // Create source and processor
      const source = audioContextRef.current.createMediaStreamSource(stream);
      const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1); // 4096 samples ≈ 256ms at 16kHz

      processor.onaudioprocess = async (event) => {
        const inputBuffer = event.inputBuffer;
        const inputData = inputBuffer.getChannelData(0);

        try {
          // Convert Float32Array to Int16Array (16-bit PCM)
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
          }

          // Create WAV blob from PCM data
          const wavBlob = createWavBlob(pcmData, 16000);

          // Stream audio chunk to server for real-time inference
          const response = await streamAudioChunk(wavBlob, sessionId, chunkIndexRef.current);
          if (response.code === 0) {
            console.log(`Audio chunk ${chunkIndexRef.current} streamed successfully`);
          } else {
            console.error(`Failed to stream audio chunk ${chunkIndexRef.current}:`, response.msg);
          }
          chunkIndexRef.current++;
        } catch (err) {
          console.error('Error processing audio chunk:', err);
        }
      };

      // Connect the nodes
      source.connect(processor);
      processor.connect(audioContextRef.current.destination);

      processorRef.current = processor;
      setIsRecording(true);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start recording';
      setError(errorMessage);
      console.error('Error starting recording:', err);
      setIsRecording(true); // Still set to true so stop button is enabled
    }
  }, []);

  const stopRecord = useCallback(
    async (sessionId: number) => {
      try {
        setError(null);

        // Stop server-side recording
        await stopRecording(sessionId);

        // Disconnect and clean up Web Audio API
        if (processorRef.current) {
          processorRef.current.disconnect();
          processorRef.current = null;
        }

        if (audioContextRef.current) {
          await audioContextRef.current.close();
          audioContextRef.current = null;
        }

        // Stop all audio tracks
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }

        setIsRecording(false);
        console.log('Recording stopped. Total chunks streamed:', chunkIndexRef.current);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to stop recording';
        setError(errorMessage);
        console.error('Error stopping recording:', err);
        setIsRecording(false);
      }
    },
    []
  );

  return {
    isRecording,
    startRecord,
    stopRecord,
    error,
  };
}

/**
 * Creates a WAV blob from PCM data
 */
function createWavBlob(pcmData: Int16Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + pcmData.length * 2);
  const view = new DataView(buffer);

  // WAV header
  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  writeString(0, 'RIFF');
  view.setUint32(4, 36 + pcmData.length * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, pcmData.length * 2, true);

  // PCM data
  const pcmView = new Int16Array(buffer, 44);
  pcmView.set(pcmData);

  return new Blob([buffer], { type: 'audio/wav' });
}

