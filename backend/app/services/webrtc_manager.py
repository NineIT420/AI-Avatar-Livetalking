"""
WebRTC connection management service
"""
import asyncio
import logging
from typing import Dict, Set
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration
from aiortc.rtcrtpsender import RTCRtpSender

from app.core.config import settings
from webrtc import HumanPlayer

logger = logging.getLogger(__name__)


class WebRTCManager:
    """Manages WebRTC peer connections"""
    
    def __init__(self):
        self.peer_connections: Dict[int, RTCPeerConnection] = {}  # sessionid -> pc
        self.pcs: Set[RTCPeerConnection] = set()
    
    async def create_peer_connection(
        self, 
        sessionid: int, 
        nerfreal
    ) -> RTCPeerConnection:
        """Create a new WebRTC peer connection"""
        # Create ICE server
        ice_server = RTCIceServer(urls=settings.STUN_SERVER)
        pc = RTCPeerConnection(
            configuration=RTCConfiguration(iceServers=[ice_server])
        )
        
        self.pcs.add(pc)
        self.peer_connections[sessionid] = pc
        
        # Setup connection state change handler
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Connection state for session {sessionid}: {pc.connectionState}")
            try:
                if pc.connectionState == "failed":
                    try:
                        await asyncio.wait_for(pc.close(), timeout=2.0)
                    except asyncio.TimeoutError:
                        logger.debug(f"Timeout closing peer connection for session {sessionid}")
                    except Exception as e:
                        logger.debug(f"Error closing peer connection for session {sessionid}: {e}")
                    finally:
                        self.pcs.discard(pc)
                        if sessionid in self.peer_connections:
                            del self.peer_connections[sessionid]
                        session_manager.delete_session(sessionid)
                elif pc.connectionState == "closed":
                    self.pcs.discard(pc)
                    if sessionid in self.peer_connections:
                        del self.peer_connections[sessionid]
                    session_manager.delete_session(sessionid)
            except KeyError as e:
                logger.debug(f"Session {sessionid} already cleaned up: {e}")
            except Exception as e:
                logger.warning(f"Error in connection state change handler for session {sessionid}: {e}")
        
        # Create player and add tracks
        player = HumanPlayer(nerfreal)
        audio_sender = pc.addTrack(player.audio)
        video_sender = pc.addTrack(player.video)
        
        # Configure codec preferences
        capabilities = RTCRtpSender.getCapabilities("video")
        preferences = list(filter(lambda x: x.name == "H264", capabilities.codecs))
        preferences += list(filter(lambda x: x.name == "VP8", capabilities.codecs))
        preferences += list(filter(lambda x: x.name == "rtx", capabilities.codecs))
        transceiver = pc.getTransceivers()[1]
        transceiver.setCodecPreferences(preferences)
        
        # Start render thread
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        player.start_render(loop)
        
        return pc
    
    async def handle_offer(
        self, 
        offer: RTCSessionDescription, 
        sessionid: int,
        session_manager
    ) -> RTCSessionDescription:
        """Handle WebRTC offer and return answer"""
        # Get or create session
        nerfreal = session_manager.get_session(sessionid)
        if nerfreal is None:
            nerfreal = await session_manager.create_session_async(sessionid)
        
        # Create peer connection
        pc = await self.create_peer_connection(sessionid, nerfreal)
        
        # Set remote description
        await pc.setRemoteDescription(offer)
        
        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        return pc.localDescription
    
    async def cleanup_all(self):
        """Cleanup all peer connections"""
        logger.info(f"Cleaning up {len(self.pcs)} peer connections")
        coros = []
        for pc in self.pcs:
            try:
                coros.append(asyncio.wait_for(pc.close(), timeout=2.0))
            except Exception as e:
                logger.debug(f"Error preparing to close peer connection: {e}")
        
        if coros:
            results = await asyncio.gather(*coros, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception) and not isinstance(result, asyncio.TimeoutError):
                    logger.debug(f"Error closing peer connection: {result}")
        
        self.pcs.clear()
        self.peer_connections.clear()

