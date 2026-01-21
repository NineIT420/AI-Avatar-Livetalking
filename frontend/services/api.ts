import { config } from '@/utils/config';
import type { OfferResponse, RecordRequest, HumanAudioResponse } from '@/types';

let audioWebSocket: WebSocket | null = null;
let isWebSocketConnected = false;

export async function connectAudioWebSocket(sessionId: number): Promise<void> {
  if (audioWebSocket && isWebSocketConnected) {
    return;
  }

  return new Promise((resolve, reject) => {
    const wsUrl = `${config.api.baseUrl.replace(/^http/, 'ws')}/ws/audio?sessionid=${sessionId}`;
    audioWebSocket = new WebSocket(wsUrl);

    audioWebSocket.onopen = () => {
      isWebSocketConnected = true;
      resolve();
    };

    audioWebSocket.onclose = () => {
      isWebSocketConnected = false;
      audioWebSocket = null;
    };

    audioWebSocket.onerror = (error) => {
      isWebSocketConnected = false;
      reject(new Error('Failed to connect to audio WebSocket'));
    };

    audioWebSocket.onmessage = (event) => {
      
    };
  });
}

export function disconnectAudioWebSocket(): void {
  if (audioWebSocket) {
    audioWebSocket.close();
    audioWebSocket = null;
    isWebSocketConnected = false;
  }
}

export function isAudioWebSocketConnected(): boolean {
  return isWebSocketConnected;
}

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

export async function streamAudioChunk(audioBlob: Blob, sessionId: number, chunkIndex: number): Promise<HumanAudioResponse> {
  if (!audioWebSocket || !isWebSocketConnected) {
    throw new Error('Audio WebSocket not connected');
  }

  const arrayBuffer = await audioBlob.arrayBuffer();

  audioWebSocket.send(arrayBuffer);

  return { code: 0, msg: 'ok' };
}

