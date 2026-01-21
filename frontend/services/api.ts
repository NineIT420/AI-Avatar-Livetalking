import { config } from '@/utils/config';
import type { OfferResponse, RecordRequest, HumanAudioResponse } from '@/types';

// WebSocket connection management
let audioWebSocket: WebSocket | null = null;
let isWebSocketConnected = false;

/**
 * Connects to the audio WebSocket
 */
export async function connectAudioWebSocket(sessionId: number): Promise<void> {
  if (audioWebSocket && isWebSocketConnected) {
    return; // Already connected
  }

  return new Promise((resolve, reject) => {
    const wsUrl = `${config.api.baseUrl.replace(/^http/, 'ws')}/ws/audio?sessionid=${sessionId}`;
    audioWebSocket = new WebSocket(wsUrl);

    audioWebSocket.onopen = () => {
      isWebSocketConnected = true;
      console.log('Audio WebSocket connected');
      resolve();
    };

    audioWebSocket.onclose = () => {
      isWebSocketConnected = false;
      console.log('Audio WebSocket disconnected');
      audioWebSocket = null;
    };

    audioWebSocket.onerror = (error) => {
      isWebSocketConnected = false;
      console.error('Audio WebSocket error:', error);
      reject(new Error('Failed to connect to audio WebSocket'));
    };

    audioWebSocket.onmessage = (event) => {
      // Handle responses if needed
      try {
        const response = JSON.parse(event.data);
        if (response.code !== 0) {
          console.error('WebSocket audio error:', response.msg);
        }
      } catch (e) {
        // Ignore non-JSON messages
      }
    };
  });
}

/**
 * Disconnects the audio WebSocket
 */
export function disconnectAudioWebSocket(): void {
  if (audioWebSocket) {
    audioWebSocket.close();
    audioWebSocket = null;
    isWebSocketConnected = false;
  }
}

/**
 * Checks if the audio WebSocket is connected
 */
export function isAudioWebSocketConnected(): boolean {
  return isWebSocketConnected;
}

/**
 * Sends WebRTC offer to server and gets answer
 */
export async function sendOffer(offer: RTCSessionDescriptionInit, useStun: boolean): Promise<OfferResponse> {
  const response = await fetch(`${config.api.baseUrl}/offer`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      sdp: offer.sdp,
      type: offer.type,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ msg: response.statusText }));
    throw new Error(error.msg || `Failed to send offer: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Starts server-side recording
 */
export async function startRecording(sessionId: number): Promise<void> {
  const response = await fetch(`${config.api.baseUrl}/record`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      type: 'start_record',
      sessionid: sessionId,
    } as RecordRequest),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ msg: response.statusText }));
    throw new Error(error.msg || 'Failed to start server recording');
  }
}

/**
 * Stops server-side recording
 */
export async function stopRecording(sessionId: number): Promise<void> {
  const response = await fetch(`${config.api.baseUrl}/record`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      type: 'end_record',
      sessionid: sessionId,
    } as RecordRequest),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ msg: response.statusText }));
    throw new Error(error.msg || 'Failed to stop server recording');
  }
}

/**
 * Sends recorded audio to server
 */
export async function sendAudio(audioBlob: Blob, sessionId: number): Promise<HumanAudioResponse> {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.wav');
  formData.append('sessionid', sessionId.toString());

  const response = await fetch(`${config.api.baseUrl}/humanaudio`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ msg: response.statusText }));
    throw new Error(error.msg || `Failed to send audio: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Streams audio chunk to server for real-time inference via WebSocket
 */
export async function streamAudioChunk(audioBlob: Blob, sessionId: number, chunkIndex: number): Promise<HumanAudioResponse> {
  if (!audioWebSocket || !isWebSocketConnected) {
    throw new Error('Audio WebSocket not connected');
  }

  // Convert blob to ArrayBuffer for WebSocket transmission
  const arrayBuffer = await audioBlob.arrayBuffer();

  // Send the audio data over WebSocket
  audioWebSocket.send(arrayBuffer);

  // Return a success response since WebSocket doesn't provide synchronous responses
  // The actual response handling is done in the WebSocket onmessage handler
  return { code: 0, msg: 'ok' };
}

