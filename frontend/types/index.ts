export interface SessionInfo {
  sessionid: number;
}

export interface OfferResponse {
  sdp: string;
  type: RTCSdpType;
  sessionid: number;
}

export type RecordType = 'start_record' | 'end_record';

export interface RecordRequest {
  type: RecordType;
  sessionid: number;
}

export interface HumanAudioResponse {
  code: number;
  msg?: string;
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'failed';

export interface WebRTCConfig {
  peerConnection: RTCPeerConnection | null;
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  latency: number | null;
  sessionId: number | null;
}

export interface AudioConfig {
  sampleRate: number;
  channelCount: number;
  echoCancellation: boolean;
  noiseSuppression: boolean;
}

export interface AudioChunk {
  data: Float32Array;
}

export interface ApiConfig {
  baseUrl: string;
}

export interface WebRTCIceConfig {
  stunServers: string[];
  turnServer: {
    urls: string;
    username: string;
    credential: string;
  };
}

export interface VideoPlayerProps {
  videoRef: React.RefObject<HTMLVideoElement>;
  audioRef: React.RefObject<HTMLAudioElement>;
}

export interface StatusDisplayProps {
  status: ConnectionStatus;
  latency: number | null;
}

export interface ControlsProps {
  isConnected: boolean;
  onStart: () => void;
  onStop: () => void;
  error?: string | Error | null;
  isLoading?: boolean;
}

export interface UseWebRTCReturn extends WebRTCConfig {
  start: (useStun: boolean) => Promise<void>;
  stop: () => void;
  videoRef: React.RefObject<HTMLVideoElement>;
  audioRef: React.RefObject<HTMLAudioElement>;
}

export interface UseRecordingReturn {
  isRecording: boolean;
  startRecord: (sessionId: number) => Promise<void>;
  stopRecord: (sessionId: number) => Promise<void>;
  error: string | null;
}

export interface UseAsyncErrorReturn<T = any> {
  error: Error | null;
  isLoading: boolean;
  execute: (
    asyncFn: () => Promise<T>,
    onSuccess?: (result: T) => void,
    onError?: (error: Error) => void
  ) => Promise<T | null>;
  reset: () => void;
}

