import { useState, useRef, useCallback } from 'react';
import { startRecording, stopRecording, sendAudio } from '@/services/api';
import { convertToWav, getSupportedMimeType } from '@/utils/audioConverter';

interface UseRecordingReturn {
  isRecording: boolean;
  startRecord: (sessionId: number) => Promise<void>;
  stopRecord: (sessionId: number) => Promise<void>;
  error: string | null;
}

export function useRecording(): UseRecordingReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const mimeTypeRef = useRef<string>('audio/webm');

  const startRecord = useCallback(async (sessionId: number) => {
    try {
      setError(null);

      // Start server-side recording
      await startRecording(sessionId);

      // Start microphone audio recording
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;
      audioChunksRef.current = [];

      // Detect supported audio format
      mimeTypeRef.current = getSupportedMimeType();

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: mimeTypeRef.current,
      });

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      // Request data every 100ms to ensure timely collection
      mediaRecorder.start(100);
      mediaRecorderRef.current = mediaRecorder;
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

        // Stop microphone audio recording
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop();

          // Set stop handler to send audio when recording stops
          mediaRecorderRef.current.onstop = async () => {
            // Combine audio chunks into Blob
            const audioBlob = new Blob(audioChunksRef.current, {
              type: mimeTypeRef.current,
            });

            try {
              // Convert to WAV format
              const wavBlob = await convertToWav(audioBlob);

              // Send audio to server
              if (wavBlob.size > 0) {
                const response = await sendAudio(wavBlob, sessionId);
                if (response.code === 0) {
                  console.log('Audio sent successfully to /humanaudio');
                } else {
                  console.error('Failed to send audio:', response.msg);
                  setError(response.msg || 'Failed to send audio');
                }
              }
            } catch (err) {
              console.error('Error converting/sending audio:', err);
              setError('Error processing audio');
            } finally {
              // Clear audio chunks
              audioChunksRef.current = [];
            }
          };
        }

        // Stop all audio tracks
        if (audioStreamRef.current) {
          audioStreamRef.current.getTracks().forEach((track) => track.stop());
          audioStreamRef.current = null;
        }

        setIsRecording(false);
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

