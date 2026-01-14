export interface SessionInfo {
  sessionid: number;
}

export interface OfferResponse {
  sdp: string;
  type: string;
  sessionid: number;
}

export interface RecordRequest {
  type: 'start_record' | 'end_record';
  sessionid: number;
}

export interface HumanAudioResponse {
  code: number;
  msg?: string;
}

export interface MediaRecorderState {
  isRecording: boolean;
  mediaRecorder: MediaRecorder | null;
  audioChunks: Blob[];
  audioStream: MediaStream | null;
  mimeType: string;
}

