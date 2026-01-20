###############################################################################
#  Copyright (C) 2024 LiveTalking@lipku https://github.com/lipku/LiveTalking
#  email: lipku@foxmail.com
# 
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

# server.py
from flask import Flask, render_template,send_from_directory,request, jsonify
from flask_sockets import Sockets
import base64
import json
#import gevent
#from gevent import pywsgi
#from geventwebsocket.handler import WebSocketHandler
import re
import numpy as np
from threading import Thread,Event
#import multiprocessing
import torch.multiprocessing as mp

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from aiortc import RTCPeerConnection, RTCSessionDescription,RTCIceServer,RTCConfiguration
from aiortc.rtcrtpsender import RTCRtpSender
from webrtc import HumanPlayer
from basereal import BaseReal

import argparse
import random
import shutil
import asyncio
import torch
from typing import Dict
from logger import logger
import gc
import ssl
import os
import warnings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


app = Flask(__name__)
#sockets = Sockets(app)
nerfreals:Dict[int, BaseReal] = {} #sessionid:BaseReal
opt = argparse.Namespace()  # Initialize opt as a namespace object
model = None
avatar = None

# FastAPI app instance
fastapi_app = None
_initialized = False  # Global flag to ensure initialization happens only once

async def on_shutdown(app):
    # close peer connections with timeout to avoid hanging
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

async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # if len(nerfreals) >= opt.max_session:
    #     logger.info('reach max session')
    #     return web.Response(
    #         content_type="application/json",
    #         text=json.dumps(
    #             {"code": -1, "msg": "reach max session"}
    #         ),
    #     )
    sessionid = randN(6) #len(nerfreals)
    nerfreals[sessionid] = None
    logger.info('sessionid=%d, session num=%d',sessionid,len(nerfreals))
    nerfreal = await asyncio.get_event_loop().run_in_executor(None, build_nerfreal,sessionid)
    nerfreals[sessionid] = nerfreal

    # Use multiple STUN servers and TURN for better connectivity
    ice_servers = [
        RTCIceServer(urls=[
            'stun:stun.l.google.com:19302',
            'stun:stun1.l.google.com:19302',
            'stun:stun2.l.google.com:19302',
            'stun:stun3.l.google.com:19302',
            'stun:stun4.l.google.com:19302'
        ]),
        # Add TURN server for NAT traversal (replace with your own TURN server)
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
                # Close connection with timeout to avoid hanging
                try:
                    await asyncio.wait_for(pc.close(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.debug(f"Timeout closing peer connection in failed state")
                except Exception as e:
                    logger.debug(f"Error closing peer connection in failed state: {e}")
                finally:
                    pcs.discard(pc)
                    if sessionid in nerfreals:
                        del nerfreals[sessionid]
            elif pc.connectionState == "closed":
                pcs.discard(pc)
                if sessionid in nerfreals:
                    del nerfreals[sessionid]
                # gc.collect()
        except KeyError as e:
            # Session already deleted, ignore
            logger.debug(f"Session {sessionid} already cleaned up: {e}")
        except Exception as e:
            logger.warning(f"Error in connection state change handler: {e}")

    player = HumanPlayer(nerfreals[sessionid])
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

    # Start render thread immediately after connection is established
    # This ensures lip-syncing starts even if client doesn't immediately consume tracks
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    player.start_render(loop)

    #return jsonify({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

    return JSONResponse(
        content={"sdp": pc.localDescription.sdp, "type": pc.localDescription.type, "sessionid":sessionid}
    )

async def human(request: Request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid',0)
        if sessionid not in nerfreals or nerfreals[sessionid] is None:
            return JSONResponse(
                status_code=200,
                content={"code": -1, "msg": f"Session {sessionid} not found"}
            )

        if params.get('interrupt'):
            nerfreals[sessionid].flush_talk()

        if params['type']=='echo':
            nerfreals[sessionid].put_msg_txt(params['text'])
        elif params['type']=='chat':
            asyncio.get_event_loop().run_in_executor(None, llm_response, params['text'],nerfreals[sessionid])
            #nerfreals[sessionid].put_msg_txt(res)

        return JSONResponse(
            content={"code": 0, "msg":"ok"}
        )
    except KeyError as e:
        logger.exception(f'KeyError in human handler: {e}')
        return JSONResponse(
            status_code=200,
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        logger.exception('exception:')
        return JSONResponse(
            status_code=200,
            content={"code": -1, "msg": str(e)}
        )

async def interrupt_talk(request: Request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid',0)
        if sessionid not in nerfreals or nerfreals[sessionid] is None:
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"code": -1, "msg": f"Session {sessionid} not found"}
                ),
            )

        nerfreals[sessionid].flush_talk()

        return JSONResponse(
            content={"code": 0, "msg":"ok"}
        )
    except KeyError as e:
        logger.exception(f'KeyError in interrupt_talk handler: {e}')
        return JSONResponse(
            status_code=200,
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        logger.exception('exception:')
        return JSONResponse(
            status_code=200,
            content={"code": -1, "msg": str(e)}
        )

async def humanaudio(request: Request):
    try:
        form = await request.form()
        sessionid = int(form.get('sessionid', '0'))
        if sessionid not in nerfreals or nerfreals[sessionid] is None:
            return JSONResponse(
                status_code=200,
                content={"code": -1, "msg": f"Session {sessionid} not found"}
            )

        fileobj = form["file"]
        filename = fileobj.filename
        filebytes = await fileobj.read()
        nerfreals[sessionid].put_audio_file(filebytes)

        return JSONResponse(
            content={"code": 0, "msg":"ok"}
        )
    except KeyError as e:
        logger.exception(f'KeyError in humanaudio handler: {e}')
        return JSONResponse(
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        logger.exception('exception:')
        return JSONResponse(
            content={"code": -1, "msg": str(e)}
        )

async def set_audiotype(request: Request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid',0)
        if sessionid not in nerfreals or nerfreals[sessionid] is None:
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"code": -1, "msg": f"Session {sessionid} not found"}
                ),
            )

        nerfreals[sessionid].set_custom_state(params['audiotype'],params['reinit'])

        return JSONResponse(
            content={"code": 0, "msg":"ok"}
        )
    except KeyError as e:
        logger.exception(f'KeyError in set_audiotype handler: {e}')
        return JSONResponse(
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        logger.exception('exception:')
        return JSONResponse(
            content={"code": -1, "msg": str(e)}
        )

async def record(request: Request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid',0)
        if sessionid not in nerfreals or nerfreals[sessionid] is None:
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"code": -1, "msg": f"Session {sessionid} not found"}
                ),
            )

        if params['type']=='start_record':
            # nerfreals[sessionid].put_msg_txt(params['text'])
            nerfreals[sessionid].start_recording()
        elif params['type']=='end_record':
            nerfreals[sessionid].stop_recording()
        return JSONResponse(
            content={"code": 0, "msg":"ok"}
        )
    except KeyError as e:
        logger.exception(f'KeyError in record handler: {e}')
        return JSONResponse(
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        logger.exception('exception:')
        return JSONResponse(
            content={"code": -1, "msg": str(e)}
        )

async def is_speaking(request: Request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid',0)
        if sessionid not in nerfreals or nerfreals[sessionid] is None:
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"code": -1, "msg": f"Session {sessionid} not found"}
                ),
            )

        return JSONResponse(
            content={"code": 0, "data": nerfreals[sessionid].is_speaking()}
        )
    except KeyError as e:
        logger.exception(f'KeyError in is_speaking handler: {e}')
        return JSONResponse(
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        logger.exception('exception:')
        return JSONResponse(
            content={"code": -1, "msg": str(e)}
        )

def create_app():
    global fastapi_app, _initialized, opt, model, avatar

    if fastapi_app is None:
        fastapi_app = FastAPI(title="LiveTalking API", client_max_size=1024**2*100)
        fastapi_app.add_event_handler("shutdown", on_shutdown)

        # Configure CORS
        fastapi_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add routes
        fastapi_app.post("/offer")(offer)
        fastapi_app.post("/human")(human)
        fastapi_app.post("/humanaudio")(humanaudio)
        fastapi_app.post("/set_audiotype")(set_audiotype)
        fastapi_app.post("/record")(record)
        fastapi_app.post("/interrupt_talk")(interrupt_talk)
        fastapi_app.post("/is_speaking")(is_speaking)

    # Initialize models and configuration if not already done
    if not _initialized:
        # Load environment variables
        opt.fps = int(os.getenv('LIVETALKING_FPS'))
        opt.l = int(os.getenv('LIVETALKING_L'))
        opt.m = int(os.getenv('LIVETALKING_M'))
        opt.r = int(os.getenv('LIVETALKING_R'))
        opt.W = int(os.getenv('LIVETALKING_W'))
        opt.H = int(os.getenv('LIVETALKING_H'))
        opt.avatar_id = os.getenv('LIVETALKING_AVATAR_ID')
        opt.batch_size = int(os.getenv('LIVETALKING_BATCH_SIZE'))
        opt.audio_gain = float(os.getenv('LIVETALKING_AUDIO_GAIN'))
        opt.customvideo_config = os.getenv('LIVETALKING_CUSTOMVIDEO_CONFIG')
        opt.tts = os.getenv('LIVETALKING_TTS')
        opt.REF_FILE = os.getenv('LIVETALKING_REF_FILE')
        opt.REF_TEXT = os.getenv('LIVETALKING_REF_TEXT')
        opt.TTS_SERVER = os.getenv('LIVETALKING_TTS_SERVER')
        opt.model = os.getenv('LIVETALKING_MODEL')
        opt.transport = os.getenv('LIVETALKING_TRANSPORT')
        opt.push_url = os.getenv('LIVETALKING_PUSH_URL')
        opt.max_session = int(os.getenv('LIVETALKING_MAX_SESSION'))
        opt.listenport = int(os.getenv('LIVETALKING_LISTENPORT'))
        opt.ssl_cert = os.getenv('LIVETALKING_SSL_CERT')
        opt.ssl_key = os.getenv('LIVETALKING_SSL_KEY')
        opt.video = os.getenv('LIVETALKING_VIDEO')
        opt.customopt = []
        if opt.customvideo_config!='':
            with open(opt.customvideo_config,'r') as file:
                opt.customopt = json.load(file)

        # Display opt value
        logger.info(f"opt = {vars(opt)}")

        # Load models based on model type
        if opt.model == 'musetalk':
            from musereal import MuseReal,load_model,load_avatar,warm_up
            logger.info(opt)
            model = load_model()
            avatar = load_avatar(opt.avatar_id)
            warm_up(opt.batch_size,model)
        elif opt.model == 'wav2lip':
            from lipreal import LipReal,load_model,load_avatar,warm_up
            logger.info(opt)
            model = load_model("./models/wav2lip.pth")
            avatar = load_avatar(opt.avatar_id)
            warm_up(opt.batch_size,model,256)
        elif opt.model == 'ultralight':
            from lightreal import LightReal,load_model,load_avatar,warm_up
            logger.info(opt)
            model = load_model(opt)
            avatar = load_avatar(opt.avatar_id)
            warm_up(opt.batch_size,avatar,160)

        _initialized = True

    return fastapi_app

# Expose the FastAPI app factory for uvicorn/gunicorn
application = create_app
        

#####webrtc###############################
pcs = set()

def randN(N)->int:
    '''生成长度为 N的随机数 '''
    min = pow(10, N - 1)
    max = pow(10, N)
    return random.randint(min, max - 1)

def build_nerfreal(sessionid:int)->BaseReal:
    opt.sessionid=sessionid
    if opt.model == 'wav2lip':
        from lipreal import LipReal
        nerfreal = LipReal(opt,model,avatar)
    elif opt.model == 'musetalk':
        from musereal import MuseReal
        nerfreal = MuseReal(opt,model,avatar)
    elif opt.model == 'ultralight':
        from lightreal import LightReal
        nerfreal = LightReal(opt,model,avatar)
    return nerfreal

# os.environ['MULTIPROCESSING_METHOD'] = 'forkserver'
if __name__ == '__main__':
    mp.set_start_method('spawn')

    # Create the app (this will also initialize models and configuration)
    app_instance = create_app()

    # if opt.transport=='rtmp':
    #     thread_quit = Event()
    #     nerfreals[0] = build_nerfreal(0)
    #     rendthrd = Thread(target=nerfreals[0].render,args=(thread_quit,))
    #     rendthrd.start()
    if opt.transport=='virtualcam':
        thread_quit = Event()
        nerfreals[0] = build_nerfreal(0)
        rendthrd = Thread(target=nerfreals[0].render,args=(thread_quit,))
        rendthrd.start()

    #############################################################################

    pagename='webrtcapi.html'
    if opt.transport=='rtmp':
        pagename='echoapi.html'
    elif opt.transport=='rtcpush':
        pagename='rtcpushapi.html'
    
    # Setup SSL context if certificates are provided
    ssl_context = None
    use_https = False
    if opt.ssl_cert and opt.ssl_key:
        if os.path.exists(opt.ssl_cert) and os.path.exists(opt.ssl_key):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(opt.ssl_cert, opt.ssl_key)
            use_https = True
            logger.info('SSL certificates loaded. Starting HTTPS server.')
        else:
            logger.warning('SSL certificate or key file not found. Falling back to HTTP.')
            if not os.path.exists(opt.ssl_cert):
                logger.warning(f'Certificate file not found: {opt.ssl_cert}')
            if not os.path.exists(opt.ssl_key):
                logger.warning(f'Key file not found: {opt.ssl_key}')
    
    protocol = 'https' if use_https else 'http'
    logger.info(f'start {protocol} server; {protocol}://<serverip>:'+str(opt.listenport)+'/'+pagename)
    logger.info(f'如果使用webrtc，推荐访问webrtc集成前端: {protocol}://<serverip>:'+str(opt.listenport)+'/dashboard.html')
    if use_https:
        logger.info('HTTPS enabled - microphone access will work from remote connections.')
    else:
        logger.info('HTTP mode - microphone access only works from localhost. Use --ssl_cert and --ssl_key for HTTPS.')
    
    def run_server():
        # Suppress aioice STUN transaction retry errors
        import logging
        aioice_logger = logging.getLogger('aioice')
        aioice_logger.setLevel(logging.WARNING)

        # Run with uvicorn
        uvicorn.run(
            "app:application",
            host="0.0.0.0",
            port=opt.listenport,
            ssl_certfile=opt.ssl_cert if use_https else None,
            ssl_keyfile=opt.ssl_key if use_https else None,
            reload=False,
            log_level="info"
        )

    run_server()

    #app.on_shutdown.append(on_shutdown)
    #app.router.add_post("/offer", offer)

    # print('start websocket server')
    # server = pywsgi.WSGIServer(('0.0.0.0', 8000), app, handler_class=WebSocketHandler)
    # server.serve_forever()
    
    
