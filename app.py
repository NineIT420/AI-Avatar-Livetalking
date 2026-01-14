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

from aiohttp import web
import aiohttp
import aiohttp_cors
from aiortc import RTCPeerConnection, RTCSessionDescription,RTCIceServer,RTCConfiguration
from aiortc.rtcrtpsender import RTCRtpSender
from webrtc import HumanPlayer
from basereal import BaseReal
from llm import llm_response

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


app = Flask(__name__)
#sockets = Sockets(app)
nerfreals:Dict[int, BaseReal] = {} #sessionid:BaseReal
opt = None
model = None
avatar = None
        

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
    # elif opt.model == 'ernerf':
    #     from nerfreal import NeRFReal
    #     nerfreal = NeRFReal(opt,model,avatar)
    elif opt.model == 'ultralight':
        from lightreal import LightReal
        nerfreal = LightReal(opt,model,avatar)
    return nerfreal

#@app.route('/offer', methods=['POST'])
async def offer(request):
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
    
    #ice_server = RTCIceServer(urls='stun:stun.l.google.com:19302')
    ice_server = RTCIceServer(urls='stun:stun.miwifi.com:3478')
    pc = RTCPeerConnection(configuration=RTCConfiguration(iceServers=[ice_server]))
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

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type, "sessionid":sessionid}
        ),
    )

async def human(request):
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
        
        if params.get('interrupt'):
            nerfreals[sessionid].flush_talk()

        if params['type']=='echo':
            nerfreals[sessionid].put_msg_txt(params['text'])
        elif params['type']=='chat':
            asyncio.get_event_loop().run_in_executor(None, llm_response, params['text'],nerfreals[sessionid])                         
            #nerfreals[sessionid].put_msg_txt(res)

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except KeyError as e:
        logger.exception(f'KeyError in human handler: {e}')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": f"Session not found: {e}"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )

async def interrupt_talk(request):
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
        
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except KeyError as e:
        logger.exception(f'KeyError in interrupt_talk handler: {e}')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": f"Session not found: {e}"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )

async def humanaudio(request):
    try:
        form= await request.post()
        sessionid = int(form.get('sessionid',0))
        if sessionid not in nerfreals or nerfreals[sessionid] is None:
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"code": -1, "msg": f"Session {sessionid} not found"}
                ),
            )
        
        fileobj = form["file"]
        filename=fileobj.filename
        filebytes=fileobj.file.read()
        nerfreals[sessionid].put_audio_file(filebytes)

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except KeyError as e:
        logger.exception(f'KeyError in humanaudio handler: {e}')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": f"Session not found: {e}"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )

async def set_audiotype(request):
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

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except KeyError as e:
        logger.exception(f'KeyError in set_audiotype handler: {e}')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": f"Session not found: {e}"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )

async def record(request):
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
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except KeyError as e:
        logger.exception(f'KeyError in record handler: {e}')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": f"Session not found: {e}"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )

async def is_speaking(request):
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
        
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "data": nerfreals[sessionid].is_speaking()}
            ),
        )
    except KeyError as e:
        logger.exception(f'KeyError in is_speaking handler: {e}')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": f"Session not found: {e}"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )


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

async def post(url,data):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url,data=data) as response:
                return await response.text()
    except aiohttp.ClientError as e:
        logger.info(f'Error: {e}')

async def run(push_url,sessionid):
    nerfreal = await asyncio.get_event_loop().run_in_executor(None, build_nerfreal,sessionid)
    nerfreals[sessionid] = nerfreal

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    player = HumanPlayer(nerfreals[sessionid])
    audio_sender = pc.addTrack(player.audio)
    video_sender = pc.addTrack(player.video)

    await pc.setLocalDescription(await pc.createOffer())
    answer = await post(push_url,pc.localDescription.sdp)
    await pc.setRemoteDescription(RTCSessionDescription(sdp=answer,type='answer'))
##########################################
# os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
# os.environ['MULTIPROCESSING_METHOD'] = 'forkserver'                                                    
if __name__ == '__main__':
    mp.set_start_method('spawn')
    parser = argparse.ArgumentParser()
    
    # audio FPS
    parser.add_argument('--fps', type=int, default=50, help="audio fps,must be 50")
    # sliding window left-middle-right length (unit: 20ms)
    parser.add_argument('-l', type=int, default=10)
    parser.add_argument('-m', type=int, default=8)
    parser.add_argument('-r', type=int, default=10)

    parser.add_argument('--W', type=int, default=450, help="GUI width")
    parser.add_argument('--H', type=int, default=450, help="GUI height")

    #musetalk opt
    parser.add_argument('--avatar_id', type=str, default='avator_1', help="define which avatar in data/avatars")
    #parser.add_argument('--bbox_shift', type=int, default=5)
    parser.add_argument('--batch_size', type=int, default=16, help="infer batch")
    parser.add_argument('--audio_gain', type=float, default=1.0, help="Audio gain multiplier to amplify mouth movement (1.0=normal, 1.5=wider, 2.0=very wide)")

    parser.add_argument('--customvideo_config', type=str, default='', help="custom action json")

    parser.add_argument('--tts', type=str, default='edgetts', help="tts service type") #xtts gpt-sovits cosyvoice fishtts tencent doubao indextts2 azuretts
    parser.add_argument('--REF_FILE', type=str, default="zh-CN-YunxiaNeural",help="参考文件名或语音模型ID，默认值为 edgetts的语音模型ID zh-CN-YunxiaNeural, 若--tts指定为azuretts, 可以使用Azure语音模型ID, 如zh-CN-XiaoxiaoMultilingualNeural")
    parser.add_argument('--REF_TEXT', type=str, default=None)
    parser.add_argument('--TTS_SERVER', type=str, default='http://127.0.0.1:9880') # http://localhost:9000
    # parser.add_argument('--CHARACTER', type=str, default='test')
    # parser.add_argument('--EMOTION', type=str, default='default')

    parser.add_argument('--model', type=str, default='musetalk') #musetalk wav2lip ultralight

    parser.add_argument('--transport', type=str, default='rtcpush') #webrtc rtcpush virtualcam
    parser.add_argument('--push_url', type=str, default='http://localhost:1985/rtc/v1/whip/?app=live&stream=livestream') #rtmp://localhost/live/livestream

    parser.add_argument('--max_session', type=int, default=1)  #multi session count
    parser.add_argument('--listenport', type=int, default=8010, help="web listen port")
    parser.add_argument('--ssl_cert', type=str, default='', help="SSL certificate file path (for HTTPS)")
    parser.add_argument('--ssl_key', type=str, default='', help="SSL private key file path (for HTTPS)")
    parser.add_argument('--video', type=str, default='', help="Video file path to stream when no voice is input")

    opt = parser.parse_args()
    #app.config.from_object(opt)
    #print(app.config)
    opt.customopt = []
    if opt.customvideo_config!='':
        with open(opt.customvideo_config,'r') as file:
            opt.customopt = json.load(file)

    # if opt.model == 'ernerf':       
    #     from nerfreal import NeRFReal,load_model,load_avatar
    #     model = load_model(opt)
    #     avatar = load_avatar(opt) 
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
    appasync = web.Application(client_max_size=1024**2*100)
    appasync.on_shutdown.append(on_shutdown)
    appasync.router.add_post("/offer", offer)
    appasync.router.add_post("/human", human)
    appasync.router.add_post("/humanaudio", humanaudio)
    appasync.router.add_post("/set_audiotype", set_audiotype)
    appasync.router.add_post("/record", record)
    appasync.router.add_post("/interrupt_talk", interrupt_talk)
    appasync.router.add_post("/is_speaking", is_speaking)
    appasync.router.add_static('/',path='web')

    # Configure default CORS settings.
    cors = aiohttp_cors.setup(appasync, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })
    # Configure CORS on all routes.
    for route in list(appasync.router.routes()):
        cors.add(route)

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
    
    def run_server(runner):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Suppress aioice STUN transaction retry errors
        import logging
        aioice_logger = logging.getLogger('aioice')
        aioice_logger.setLevel(logging.WARNING)
        
        # Set custom exception handler to suppress aioice InvalidStateError
        def exception_handler(loop, context):
            exception = context.get('exception')
            if exception and isinstance(exception, asyncio.InvalidStateError):
                # Check if it's from aioice STUN transaction
                message = str(context.get('message', ''))
                if 'Transaction.__retry' in message or 'aioice' in message.lower():
                    logger.debug(f"Suppressed aioice STUN transaction retry error: {message}")
                    return
            # Call default handler for other exceptions
            loop.default_exception_handler(context)
        
        loop.set_exception_handler(exception_handler)
        
        loop.run_until_complete(runner.setup())
        if use_https and ssl_context:
            site = web.TCPSite(runner, '0.0.0.0', opt.listenport, ssl_context=ssl_context)
        else:
            site = web.TCPSite(runner, '0.0.0.0', opt.listenport)
        loop.run_until_complete(site.start())
        if opt.transport=='rtcpush':
            for k in range(opt.max_session):
                push_url = opt.push_url
                if k!=0:
                    push_url = opt.push_url+str(k)
                loop.run_until_complete(run(push_url,k))
        loop.run_forever()    
    #Thread(target=run_server, args=(web.AppRunner(appasync),)).start()
    run_server(web.AppRunner(appasync))

    #app.on_shutdown.append(on_shutdown)
    #app.router.add_post("/offer", offer)

    # print('start websocket server')
    # server = pywsgi.WSGIServer(('0.0.0.0', 8000), app, handler_class=WebSocketHandler)
    # server.serve_forever()
    
    
