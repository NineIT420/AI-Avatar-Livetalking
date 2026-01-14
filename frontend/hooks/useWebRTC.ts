import { useState, useRef, useCallback, useEffect } from 'react';
import { sendOffer } from '@/services/api';
import type { OfferResponse } from '@/types';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'failed';

interface UseWebRTCReturn {
  peerConnection: RTCPeerConnection | null;
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  latency: number | null;
  sessionId: number | null;
  start: (useStun: boolean) => Promise<void>;
  stop: () => void;
  videoRef: React.RefObject<HTMLVideoElement>;
  audioRef: React.RefObject<HTMLAudioElement>;
}

export function useWebRTC(): UseWebRTCReturn {
  const [peerConnection, setPeerConnection] = useState<RTCPeerConnection | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [latency, setLatency] = useState<number | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const statsIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Function to measure latency using WebRTC stats
  const measureLatency = useCallback(async (pc: RTCPeerConnection) => {
    try {
      const stats = await pc.getStats();
      let minRtt = Infinity;
      let foundRtt = false;

      // Iterate through all stats reports
      for (const [id, report] of stats.entries()) {
        // Check candidate-pair stats (most reliable for RTT)
        if (report.type === 'candidate-pair') {
          const candidatePair = report as any;
          // Check if the candidate pair is active/succeeded
          if (candidatePair.state === 'succeeded' || candidatePair.state === 'in-progress') {
            // Access RTT properties - they might be in different formats
            let rtt: number | null = null;
            
            // Try different property names (browser-dependent)
            if ('currentRoundTripTime' in candidatePair && candidatePair.currentRoundTripTime) {
              rtt = candidatePair.currentRoundTripTime;
            } else if ('totalRoundTripTime' in candidatePair && candidatePair.totalRoundTripTime) {
              rtt = candidatePair.totalRoundTripTime;
            } else if ('roundTripTime' in candidatePair && candidatePair.roundTripTime) {
              rtt = candidatePair.roundTripTime;
            }
            
            if (rtt !== null && rtt > 0 && rtt < minRtt) {
              minRtt = rtt;
              foundRtt = true;
            }
          }
        }
        
        // Check transport stats
        if (report.type === 'transport') {
          const transport = report as any;
          if ('currentRoundTripTime' in transport && transport.currentRoundTripTime) {
            const rtt = transport.currentRoundTripTime;
            if (rtt > 0 && rtt < minRtt) {
              minRtt = rtt;
              foundRtt = true;
            }
          }
        }
        
        // Check inbound-rtp stats (some browsers report RTT here)
        if (report.type === 'inbound-rtp') {
          const inboundRtp = report as any;
          if ('roundTripTime' in inboundRtp && inboundRtp.roundTripTime) {
            const rtt = inboundRtp.roundTripTime;
            if (rtt > 0 && rtt < minRtt) {
              minRtt = rtt;
              foundRtt = true;
            }
          }
        }
      }

      // If we found a valid RTT, update latency
      if (foundRtt && minRtt !== Infinity && minRtt > 0) {
        // RTT from stats is in seconds, convert to milliseconds
        const latencyMs = Math.round(minRtt * 1000);
        setLatency(latencyMs);
      }
      // Note: RTT may not be available immediately or in all browsers
      // It typically becomes available after media starts flowing
    } catch (error) {
      console.error('Error measuring latency:', error);
    }
  }, []);

  const start = useCallback(async (useStun: boolean) => {
    setConnectionStatus('connecting');
    setLatency(null);

    const config: RTCConfiguration = {
      sdpSemantics: 'unified-plan',
    };

    if (useStun) {
      config.iceServers = [{ urls: ['stun:stun.l.google.com:19302'] }];
    }

    const pc = new RTCPeerConnection(config);

    // Track connection state changes
    pc.addEventListener('connectionstatechange', () => {
      const state = pc.connectionState;
      if (state === 'connected') {
        setConnectionStatus('connected');
        setIsConnected(true);
      } else if (state === 'connecting' || state === 'checking') {
        setConnectionStatus('connecting');
      } else if (state === 'disconnected' || state === 'closed') {
        setConnectionStatus('disconnected');
        setIsConnected(false);
      } else if (state === 'failed') {
        setConnectionStatus('failed');
        setIsConnected(false);
      }
    });

    // Track ICE connection state
    pc.addEventListener('iceconnectionstatechange', () => {
      const iceState = pc.iceConnectionState;
      if (iceState === 'connected' || iceState === 'completed') {
        setConnectionStatus('connected');
        setIsConnected(true);
      } else if (iceState === 'checking' || iceState === 'connecting') {
        setConnectionStatus('connecting');
      } else if (iceState === 'disconnected' || iceState === 'closed' || iceState === 'failed') {
        setConnectionStatus(iceState === 'failed' ? 'failed' : 'disconnected');
        setIsConnected(false);
      }
    });

    // Handle incoming tracks
    pc.addEventListener('track', (evt) => {
      if (evt.track.kind === 'video' && videoRef.current) {
        videoRef.current.srcObject = evt.streams[0];
      } else if (evt.track.kind === 'audio' && audioRef.current) {
        audioRef.current.srcObject = evt.streams[0];
      }
    });

    // Add transceivers
    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });

    // Create and send offer
    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // Wait for ICE gathering to complete
      await new Promise<void>((resolve) => {
        if (pc.iceGatheringState === 'complete') {
          resolve();
        } else {
          const checkState = () => {
            if (pc.iceGatheringState === 'complete') {
              pc.removeEventListener('icegatheringstatechange', checkState);
              resolve();
            }
          };
          pc.addEventListener('icegatheringstatechange', checkState);
        }
      });

      const answer: OfferResponse = await sendOffer(pc.localDescription!, useStun);
      setSessionId(answer.sessionid);
      await pc.setRemoteDescription(answer);

      setPeerConnection(pc);

      // Start measuring latency periodically
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
      }
      
      // Wait a bit for connection to fully establish before measuring
      const startMeasuring = () => {
        statsIntervalRef.current = setInterval(() => {
          if (pc.connectionState === 'connected' && pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
            measureLatency(pc);
          }
        }, 1000); // Measure every second
      };
      
      // Start measuring after connection is established
      const checkConnection = () => {
        if (pc.connectionState === 'connected' && (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed')) {
          startMeasuring();
          // Initial measurement after a short delay
          setTimeout(() => measureLatency(pc), 500);
        } else {
          // Check again in 500ms
          setTimeout(checkConnection, 500);
        }
      };
      
      // Start checking after a short delay
      setTimeout(checkConnection, 1000);
    } catch (error) {
      console.error('Error starting WebRTC:', error);
      setConnectionStatus('failed');
      pc.close();
      throw error;
    }
  }, [measureLatency]);

  const stop = useCallback(() => {
    if (statsIntervalRef.current) {
      clearInterval(statsIntervalRef.current);
      statsIntervalRef.current = null;
    }
    if (peerConnection) {
      setTimeout(() => {
        peerConnection.close();
        setPeerConnection(null);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        setLatency(null);
        setSessionId(null);
      }, 500);
    }
  }, [peerConnection]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
      }
      if (peerConnection) {
        peerConnection.close();
      }
    };
  }, [peerConnection]);

  // Handle page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (peerConnection) {
        setTimeout(() => {
          peerConnection.close();
        }, 500);
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('unload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('unload', handleBeforeUnload);
    };
  }, [peerConnection]);

  return {
    peerConnection,
    isConnected,
    connectionStatus,
    latency,
    sessionId,
    start,
    stop,
    videoRef,
    audioRef,
  };
}

