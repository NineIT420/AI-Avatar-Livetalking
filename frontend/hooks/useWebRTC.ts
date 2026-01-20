import { useState, useRef, useCallback, useEffect } from 'react';
import { sendOffer } from '@/services/api';
import { config } from '@/utils/config';
import type { OfferResponse, ConnectionStatus, UseWebRTCReturn } from '@/types';

export function useWebRTC(): UseWebRTCReturn {
  const [peerConnection, setPeerConnection] = useState<RTCPeerConnection | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [latency, setLatency] = useState<number | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const statsIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Function to measure latency using WebRTC stats with performance optimizations
  const measureLatency = useCallback(async (pc: RTCPeerConnection) => {
    // Early return if connection is not in a good state
    if (pc.connectionState !== 'connected' || (pc.iceConnectionState !== 'connected' && pc.iceConnectionState !== 'completed')) {
      return;
    }

    try {
      const stats = await pc.getStats();
      let minRtt = Infinity;
      let foundRtt = false;

      // Iterate through all stats reports with early optimization
      for (const [id, report] of stats.entries()) {
        // Only check relevant stat types
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
        // Check transport stats as fallback
        else if (report.type === 'transport' && !foundRtt) {
          const transport = report as any;
          if ('currentRoundTripTime' in transport && transport.currentRoundTripTime) {
            const rtt = transport.currentRoundTripTime;
            if (rtt > 0 && rtt < minRtt) {
              minRtt = rtt;
              foundRtt = true;
            }
          }
        }
        // Check inbound-rtp stats as last resort
        else if (report.type === 'inbound-rtp' && !foundRtt) {
          const inboundRtp = report as any;
          if ('roundTripTime' in inboundRtp && inboundRtp.roundTripTime) {
            const rtt = inboundRtp.roundTripTime;
            if (rtt > 0 && rtt < minRtt) {
              minRtt = rtt;
              foundRtt = true;
            }
          }
        }

        // Early exit if we found RTT and it's reasonable
        if (foundRtt && minRtt !== Infinity && minRtt > 0 && minRtt < 1) {
          break;
        }
      }

      // If we found a valid RTT, update latency
      if (foundRtt && minRtt !== Infinity && minRtt > 0) {
        // RTT from stats is in seconds, convert to milliseconds
        const latencyMs = Math.round(minRtt * 1000);
        // Only update if latency changed significantly (prevent unnecessary re-renders)
        setLatency(prevLatency => {
          if (prevLatency === null || Math.abs(prevLatency - latencyMs) > 5) {
            return latencyMs;
          }
          return prevLatency;
        });
      }
    } catch (error) {
      // Silent error handling for performance - don't log on every measurement failure
      console.warn('Latency measurement failed:', error);
    }
  }, []);

  // Helper function to create WebRTC configuration
  const createRTCConfig = useCallback((useStun: boolean): RTCConfiguration => {
    const rtcConfig: RTCConfiguration = {};

    if (useStun) {
      rtcConfig.iceServers = [
        { urls: config.webrtc.stunServers },
        config.webrtc.turnServer
      ];
    }

    return rtcConfig;
  }, []);

  // Helper function to setup connection state listeners
  const setupConnectionListeners = useCallback((pc: RTCPeerConnection) => {
    const handleConnectionStateChange = () => {
      const state = pc.connectionState;
      updateConnectionState(state);
    };

    const handleIceConnectionStateChange = () => {
      const iceState = pc.iceConnectionState;
      updateIceConnectionState(iceState);
    };

    pc.addEventListener('connectionstatechange', handleConnectionStateChange);
    pc.addEventListener('iceconnectionstatechange', handleIceConnectionStateChange);

    return () => {
      pc.removeEventListener('connectionstatechange', handleConnectionStateChange);
      pc.removeEventListener('iceconnectionstatechange', handleIceConnectionStateChange);
    };
  }, []);

  // Helper function to setup track listeners
  const setupTrackListeners = useCallback((pc: RTCPeerConnection) => {
    pc.addEventListener('track', (evt) => {
      if (evt.track.kind === 'video' && videoRef.current) {
        videoRef.current.srcObject = evt.streams[0];
      } else if (evt.track.kind === 'audio' && audioRef.current) {
        audioRef.current.srcObject = evt.streams[0];
      }
    });
  }, []);

  // Helper function to update connection state
  const updateConnectionState = useCallback((state: RTCPeerConnectionState) => {
    switch (state) {
      case 'connected':
        setConnectionStatus('connected');
        setIsConnected(true);
        break;
      case 'connecting':
        setConnectionStatus('connecting');
        break;
      case 'disconnected':
      case 'closed':
        setConnectionStatus('disconnected');
        setIsConnected(false);
        setSessionId(null);
        break;
      case 'failed':
        setConnectionStatus('failed');
        setIsConnected(false);
        setSessionId(null);
        break;
    }
  }, []);

  // Helper function to update ICE connection state
  const updateIceConnectionState = useCallback((iceState: RTCIceConnectionState) => {
    switch (iceState) {
      case 'connected':
      case 'completed':
        setConnectionStatus('connected');
        setIsConnected(true);
        break;
      case 'checking':
        setConnectionStatus('connecting');
        break;
      case 'disconnected':
      case 'closed':
      case 'failed':
        setConnectionStatus(iceState === 'failed' ? 'failed' : 'disconnected');
        setIsConnected(false);
        if (iceState === 'failed' || iceState === 'disconnected' || iceState === 'closed') {
          setSessionId(null);
        }
        break;
    }
  }, []);

  // Helper function to setup latency measurement
  const setupLatencyMeasurement = useCallback((pc: RTCPeerConnection) => {
    if (statsIntervalRef.current) {
      clearInterval(statsIntervalRef.current);
    }

    let measurementCount = 0;
    const maxMeasurements = 10;

    const startMeasuring = () => {
      statsIntervalRef.current = setInterval(() => {
        if (measurementCount >= maxMeasurements) {
          clearInterval(statsIntervalRef.current!);
          statsIntervalRef.current = setInterval(() => {
            if (isConnectionActive(pc)) {
              measureLatency(pc);
            }
          }, 5000);
          return;
        }

        if (isConnectionActive(pc)) {
          measureLatency(pc);
          measurementCount++;
        }
      }, 2000);
    };

    const checkConnection = () => {
      if (isConnectionActive(pc)) {
        startMeasuring();
        setTimeout(() => measureLatency(pc), 300);
      } else {
        setTimeout(checkConnection, 300);
      }
    };

    setTimeout(checkConnection, 500);
  }, [measureLatency]);

  // Helper function to check if connection is active
  const isConnectionActive = useCallback((pc: RTCPeerConnection): boolean => {
    return pc.connectionState === 'connected' &&
           (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed');
  }, []);

  // Main start function - now much cleaner and focused
  const start = useCallback(async (useStun: boolean) => {
    setConnectionStatus('connecting');
    setLatency(null);

    const rtcConfig = createRTCConfig(useStun);
    const pc = new RTCPeerConnection(rtcConfig);

    // Setup all listeners
    const cleanupListeners = setupConnectionListeners(pc);
    setupTrackListeners(pc);

    // Add transceivers
    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });

    try {
      // Create and exchange offer/answer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const answer: OfferResponse = await sendOffer(pc.localDescription!, useStun);
      setSessionId(answer.sessionid);
      await pc.setRemoteDescription({
        type: answer.type as RTCSdpType,
        sdp: answer.sdp
      });

      setPeerConnection(pc);
      setupLatencyMeasurement(pc);
    } catch (error) {
      console.error('Error starting WebRTC:', error);
      setConnectionStatus('failed');
      pc.close();
      throw error;
    }
  }, [createRTCConfig, setupConnectionListeners, setupTrackListeners, setupLatencyMeasurement]);

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

