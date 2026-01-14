"""
FastAPI main application for LiveTalking MUSETALK backend
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1 import router as api_router
from app.core.logger import setup_logging
from app.services.session_manager import SessionManager
from app.services.webrtc_manager import WebRTCManager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global managers - will be initialized in lifespan
session_manager: SessionManager = None
webrtc_manager: WebRTCManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global session_manager, webrtc_manager
    
    # Startup
    logger.info("Starting LiveTalking MUSETALK backend...")
    logger.info(f"Max sessions: {settings.MAX_SESSIONS}")
    logger.info(f"Model: {settings.MODEL}")
    logger.info(f"Avatar ID: {settings.AVATAR_ID}")
    
    # Initialize managers
    session_manager = SessionManager()
    webrtc_manager = WebRTCManager()
    
    # Initialize model and avatar if needed
    # This will be done lazily per session via run.py
    
    yield
    
    # Shutdown
    logger.info("Shutting down LiveTalking MUSETALK backend...")
    if webrtc_manager:
        await webrtc_manager.cleanup_all()
    if session_manager:
        session_manager.cleanup_all()


# Create FastAPI app
app = FastAPI(
    title="LiveTalking MUSETALK API",
    description="FastAPI backend for LiveTalking MUSETALK WebRTC service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "livetalking-musetalk"}


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"code": -1, "msg": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

