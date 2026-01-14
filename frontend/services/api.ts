import type { OfferResponse, RecordRequest, HumanAudioResponse } from '@/types';


const API_BASE_URL = 'https://52.3.240.147:8010';
const API_V1_BASE = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;

/**
 * Sends WebRTC offer to server and gets answer
 */
export async function sendOffer(offer: RTCSessionDescriptionInit, useStun: boolean): Promise<OfferResponse> {
  const response = await fetch(`${API_V1_BASE}/offer`, {
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
  const response = await fetch(`${API_V1_BASE}/record`, {
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
  const response = await fetch(`${API_V1_BASE}/record`, {
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

  const response = await fetch(`${API_V1_BASE}/humanaudio`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ msg: response.statusText }));
    throw new Error(error.msg || `Failed to send audio: ${response.statusText}`);
  }

  return response.json();
}

