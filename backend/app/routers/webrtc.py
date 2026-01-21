import asyncio
import random
from typing import Dict

from fastapi import APIRouter, Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration
from aiortc.rtcrtpsender import RTCRtpSender

from config.settings import settings
from ..utils.logger import logger
from ..webrtc import HumanPlayer
from ..core.session_manager import session_manager

router = APIRouter()
pcs = set()


async def on_shutdown():
    coros = []
    for pc in pcs:
        try:
            coros.append(asyncio.wait_for(pc.close(), timeout=2.0))
        except Exception as e:
            logger.debug(f"Error preparing to close peer connection: {e}")

    if coros:
        results = await asyncio.gather(*coros, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception) and not isinstance(result, asyncio.TimeoutError):
                logger.debug(f"Error closing peer connection: {result}")
    pcs.clear()


def randN(N: int) -> int:
    min_val = pow(10, N - 1)
    max_val = pow(10, N)
    return random.randint(min_val, max_val - 1)


@router.post("/offer")
async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    sessionid = randN(6)
    session_manager.create_session(sessionid)
    logger.info('sessionid=%d, session num=%d', sessionid, len(session_manager.nerfreals))

    nerfreal = await asyncio.get_event_loop().run_in_executor(
        None, session_manager.build_nerfreal, sessionid
    )
    session_manager.nerfreals[sessionid] = nerfreal

    ice_servers = [
        RTCIceServer(urls=[
            'stun:stun.l.google.com:19302',
            'stun:stun1.l.google.com:19302',
            'stun:stun2.l.google.com:19302',
            'stun:stun3.l.google.com:19302',
            'stun:stun4.l.google.com:19302'
        ]),
        RTCIceServer(
            urls='turn:turn.anyfirewall.com:443?transport=tcp',
            username='webrtc',
            credential='webrtc'
        )
    ]
    pc = RTCPeerConnection(configuration=RTCConfiguration(iceServers=ice_servers))
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state is %s" % pc.connectionState)
        try:
            if pc.connectionState == "failed":
                try:
                    await asyncio.wait_for(pc.close(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.debug("Timeout closing peer connection in failed state")
                except Exception as e:
                    logger.debug(f"Error closing peer connection in failed state: {e}")
                finally:
                    pcs.discard(pc)
                    session_manager.cleanup_session(sessionid)
            elif pc.connectionState == "closed":
                pcs.discard(pc)
                session_manager.cleanup_session(sessionid)
        except KeyError:
            logger.debug(f"Session {sessionid} already cleaned up")
        except Exception as e:
            logger.warning(f"Error in connection state change handler: {e}")

    player = HumanPlayer(session_manager.nerfreals[sessionid])
    audio_sender = pc.addTrack(player.audio)
    video_sender = pc.addTrack(player.video)
    capabilities = RTCRtpSender.getCapabilities("video")
    preferences = list(filter(lambda x: x.name == "H264", capabilities.codecs))
    preferences += list(filter(lambda x: x.name == "VP8", capabilities.codecs))
    preferences += list(filter(lambda x: x.name == "rtx", capabilities.codecs))
    transceiver = pc.getTransceivers()[1]
    transceiver.setCodecPreferences(preferences)

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    player.start_render(loop)

    return JSONResponse(
        content={"sdp": pc.localDescription.sdp, "type": pc.localDescription.type, "sessionid": sessionid}
    )
