import asyncio
import ssl
import os
import torch.multiprocessing as mp
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from app.routers.webrtc import router as webrtc_router, on_shutdown
from app.routers.session import router as session_router
from app.services.model_service import load_model, load_avatar, warm_up
from app.utils.logger import logger


def create_app():
    # Create FastAPI app
    app = FastAPI(title="LiveTalking API", client_max_size=1024**2*100)
    app.add_event_handler("shutdown", on_shutdown)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(webrtc_router)
    app.include_router(session_router)

    logger.info(f"Configuration: {settings.to_dict()}")

    load_model()
    load_avatar()
    warm_up(settings.batch_size)

    return app


app = create_app()


if __name__ == '__main__':
    mp.set_start_method('spawn')

    ssl_context = None
    use_https = False
    if settings.ssl_cert and settings.ssl_key:
        if os.path.exists(settings.ssl_cert) and os.path.exists(settings.ssl_key):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(settings.ssl_cert, settings.ssl_key)
            use_https = True
            logger.info('SSL certificates loaded. Starting HTTPS server.')
        else:
            logger.warning('SSL certificate or key file not found. Falling back to HTTP.')
            if not os.path.exists(settings.ssl_cert):
                logger.warning(f'Certificate file not found: {settings.ssl_cert}')
            if not os.path.exists(settings.ssl_key):
                logger.warning(f'Key file not found: {settings.ssl_key}')

    protocol = 'https' if use_https else 'http'
    pagename = 'webrtcapi.html'
    if settings.transport == 'rtmp':
        pagename = 'echoapi.html'
    elif settings.transport == 'rtcpush':
        pagename = 'rtcpushapi.html'

    logger.info(f'start {protocol} server; {protocol}://<serverip>:'+str(settings.listenport)+'/'+pagename)
    logger.info(f'如果使用webrtc，推荐访问webrtc集成前端: {protocol}://<serverip>:'+str(settings.listenport)+'/dashboard.html')
    if use_https:
        logger.info('HTTPS enabled - microphone access will work from remote connections.')
    else:
        logger.info('HTTP mode - microphone access only works from localhost. Use --ssl_cert and --ssl_key for HTTPS.')

    def run_server():
        import logging
        aioice_logger = logging.getLogger('aioice')
        aioice_logger.setLevel(logging.WARNING)

        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=settings.listenport,
            ssl_certfile=settings.ssl_cert if use_https else None,
            ssl_keyfile=settings.ssl_key if use_https else None,
            reload=False,
            log_level="info"
        )

    run_server()
