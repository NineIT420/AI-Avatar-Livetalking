# LiveTalking MUSETALK FastAPI Backend

A structured FastAPI backend for the LiveTalking MUSETALK WebRTC service.

## Features

- FastAPI with async/await support
- Structured architecture (routers, services, schemas)
- WebRTC peer connection management
- Session management
- Recording functionality
- Audio upload handling
- Type safety with Pydantic models
- CORS support
- Comprehensive error handling

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py      # Router aggregation
│   │       ├── webrtc.py        # WebRTC endpoints
│   │       ├── recording.py     # Recording endpoints
│   │       └── audio.py         # Audio upload endpoints
│   ├── core/
│   │   ├── config.py            # Application settings
│   │   └── logger.py            # Logging configuration
│   ├── schemas/
│   │   ├── webrtc.py            # WebRTC request/response models
│   │   └── recording.py         # Recording models
│   ├── services/
│   │   ├── session_manager.py   # Session lifecycle management
│   │   └── webrtc_manager.py   # WebRTC connection management
│   └── main.py                  # FastAPI application
├── requirements.txt
├── run.py                       # Startup script
└── README.md
```

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Configuration

Create a `.env` file or set environment variables:

```env
HOST=0.0.0.0
PORT=8000
DEBUG=False
MAX_SESSIONS=1
MODEL=musetalk
AVATAR_ID=avator_1
BATCH_SIZE=16
FPS=50
STUN_SERVER=stun:stun.miwifi.com:3478
```

## Running the Server

### Basic usage:

```bash
python run.py
```

### With custom options:

```bash
python run.py --model musetalk --avatar_id avator_1 --batch_size 16 --fps 50
```

### With SSL:

```bash
python run.py --ssl_cert /path/to/cert.pem --ssl_key /path/to/key.pem
```

## API Endpoints

### WebRTC

- `POST /api/v1/webrtc/offer` - Handle WebRTC offer/answer negotiation

### Recording

- `POST /api/v1/recording/start-stop` - Start or stop recording
- `POST /api/v1/recording/is-speaking` - Check if session is speaking

### Audio

- `POST /api/v1/audio/upload` - Upload audio file for processing

### Health

- `GET /health` - Health check endpoint

## API Documentation

FastAPI automatically generates interactive API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Integration with Frontend

The backend is designed to work with the Next.js frontend. Update the frontend's API base URL to point to this backend:

```typescript
// frontend/services/api.ts
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

## Migration from aiohttp

This FastAPI backend replaces the aiohttp-based endpoints in `app.py` while maintaining compatibility with the existing MUSETALK functionality.

## License

Same as the main LiveTalking project.

