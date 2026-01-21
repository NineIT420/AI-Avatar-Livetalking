interface AppConfig {
  api: {
    baseUrl: string;
  };
  webrtc: {
    stunServers: string[];
    turnServer: {
      urls: string;
      username: string;
      credential: string;
    };
  };
  audio: {
    sampleRate: number;
    channelCount: number;
    echoCancellation: boolean;
    noiseSuppression: boolean;
  };
}

function getEnvVar(key: string, defaultValue?: string): string {
  const value = process.env[key] || defaultValue;
  if (!value) {
    throw new Error(`Environment variable ${key} is required but not set`);
  }
  return value;
}

export const config: AppConfig = {
  api: {
    baseUrl: getEnvVar('NEXT_PUBLIC_API_BASE_URL', 'https://52.3.240.147:8010'),
  },
  webrtc: {
    stunServers: [
      'stun:stun.l.google.com:19302',
      'stun:stun1.l.google.com:19302',
      'stun:stun2.l.google.com:19302',
      'stun:stun3.l.google.com:19302',
      'stun:stun4.l.google.com:19302',
    ],
    turnServer: {
      urls: getEnvVar('NEXT_PUBLIC_TURN_SERVER_URL', 'turn:turn.anyfirewall.com:443?transport=tcp'),
      username: getEnvVar('NEXT_PUBLIC_TURN_USERNAME', 'webrtc'),
      credential: getEnvVar('NEXT_PUBLIC_TURN_CREDENTIAL', 'webrtc'),
    },
  },
  audio: {
    sampleRate: parseInt(getEnvVar('NEXT_PUBLIC_AUDIO_SAMPLE_RATE', '16000')),
    channelCount: parseInt(getEnvVar('NEXT_PUBLIC_AUDIO_CHANNEL_COUNT', '1')),
    echoCancellation: getEnvVar('NEXT_PUBLIC_AUDIO_ECHO_CANCELLATION', 'true') === 'true',
    noiseSuppression: getEnvVar('NEXT_PUBLIC_AUDIO_NOISE_SUPPRESSION', 'true') === 'true',
  },
};
