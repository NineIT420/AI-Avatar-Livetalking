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


def create_app():
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

    def run_server():
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
