/**
 * Converts an audio blob to WAV format
 */
export function convertToWav(audioBlob: Blob): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContext
        .decodeAudioData(e.target?.result as ArrayBuffer)
        .then((audioBuffer) => {
          const wav = audioBufferToWav(audioBuffer);
          const wavBlob = new Blob([wav], { type: 'audio/wav' });
          resolve(wavBlob);
        })
        .catch(reject);
    };
    reader.onerror = reject;
    reader.readAsArrayBuffer(audioBlob);
  });
}

/**
 * Converts AudioBuffer to WAV format
 */
function audioBufferToWav(buffer: AudioBuffer): ArrayBuffer {
  const length = buffer.length;
  const numberOfChannels = buffer.numberOfChannels;
  const sampleRate = buffer.sampleRate;
  const arrayBuffer = new ArrayBuffer(44 + length * numberOfChannels * 2);
  const view = new DataView(arrayBuffer);
  const channels: Float32Array[] = [];
  let pos = 0;

  const setUint16 = (data: number) => {
    view.setUint16(pos, data, true);
    pos += 2;
  };

  const setUint32 = (data: number) => {
    view.setUint32(pos, data, true);
    pos += 4;
  };

  // RIFF identifier
  setUint32(0x46464952); // "RIFF"
  // File length
  setUint32(36 + length * numberOfChannels * 2);
  // RIFF type
  setUint32(0x45564157); // "WAVE"
  // Format chunk identifier
  setUint32(0x20746d66); // "fmt "
  // Format chunk length
  setUint32(16);
  // Sample format (raw)
  setUint16(1);
  // Channel count
  setUint16(numberOfChannels);
  // Sample rate
  setUint32(sampleRate);
  // Byte rate (sample rate * block align)
  setUint32(sampleRate * numberOfChannels * 2);
  // Block align (channel count * bytes per sample)
  setUint16(numberOfChannels * 2);
  // Bits per sample
  setUint16(16);
  // Data chunk identifier
  setUint32(0x61746164); // "data"
  // Data chunk length
  setUint32(length * numberOfChannels * 2);

  // Get channel data
  for (let i = 0; i < numberOfChannels; i++) {
    channels.push(buffer.getChannelData(i));
  }

  // Interleave and convert to 16-bit PCM
  const samples = new Int16Array(length * numberOfChannels);
  for (let i = 0; i < length; i++) {
    for (let channel = 0; channel < numberOfChannels; channel++) {
      const sample = Math.max(-1, Math.min(1, channels[channel][i]));
      samples[i * numberOfChannels + channel] =
        sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
  }

  // Write samples to the buffer after the header (at offset 44)
  const samplesView = new Int16Array(arrayBuffer, 44);
  samplesView.set(samples);

  return arrayBuffer;
}

/**
 * Detects the best supported audio MIME type
 */
export function getSupportedMimeType(): string {
  if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
    return 'audio/webm;codecs=opus';
  } else if (MediaRecorder.isTypeSupported('audio/webm')) {
    return 'audio/webm';
  } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
    return 'audio/ogg;codecs=opus';
  }
  return 'audio/webm';
}

