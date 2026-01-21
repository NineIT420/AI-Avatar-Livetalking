# LiveTalking

A real-time AI avatar communication platform with WebRTC support.

## Overview

LiveTalking is an AI-powered avatar system that enables real-time video communication with animated avatars. The system consists of a Next.js frontend for the user interface and a FastAPI backend handling AI model inference and WebRTC streaming.

## Prerequisites

Before setting up the project, ensure you have the following installed:

- **Node.js** (v16 or higher)
- **Python** (v3.8 or higher)
- **Conda** (Miniconda or Anaconda)
- **OpenSSL** (for HTTPS certificates)
- **Git**

## Project Structure

```
LiveTalking/
├── frontend/          # Next.js React application
│   ├── app/          # Next.js app directory
│   ├── components/   # React components
│   ├── public/       # Static assets
│   └── server.js     # Custom HTTPS server
├── backend/          # FastAPI Python backend
│   ├── app/         # FastAPI application
│   ├── models/      # AI models and configurations
│   ├── musetalk/    # MuseTalk avatar model
│   └── config/      # Configuration settings
└── README.md
```

## Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd LiveTalking
```

### 2. Backend Setup

#### Create Conda Environment

```bash
# Source your bash profile (if needed)
source ~/.bashrc

# Create and activate conda environment
conda create -n nerfstream python=3.10 -y
conda activate nerfstream
```

#### Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### Environment Variables (Optional)

Create a `.env` file in the backend directory to customize settings:

```bash
# Example .env file
LIVETALKING_FPS=25
LIVETALKING_AVATAR_ID=avator
LIVETALKING_BATCH_SIZE=8
LIVETALKING_LISTENPORT=8010
LIVETALKING_MODEL=musetalk
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Start the Backend

```bash
# From the project root
source ~/.bashrc
conda activate nerfstream
cd backend
uvicorn main:app --host 0.0.0.0 --port 8010
```

The backend will start on `http://0.0.0.0:8010` (or the port specified in your environment variables).

### Start the Frontend

```bash
# From the project root
cd frontend
npm run dev
```

The frontend will start on `https://localhost:3000` with a self-signed SSL certificate.

> **Note:** Your browser may show a security warning for the self-signed certificate. You can safely accept it for development.

## API Endpoints

The backend provides the following main endpoints:

- `GET /` - Health check
- `POST /session/create` - Create a new session
- `WebSocket /webrtc/{session_id}` - WebRTC signaling for real-time communication

## Configuration

### Backend Configuration

Key configuration options (can be set via environment variables):

- `LIVETALKING_FPS`: Frames per second (default: 25)
- `LIVETALKING_AVATAR_ID`: Avatar identifier (default: "avator")
- `LIVETALKING_BATCH_SIZE`: Inference batch size (default: 8)
- `LIVETALKING_LISTENPORT`: Server port (default: 8000)
- `LIVETALKING_MODEL`: AI model to use (default: "musetalk")
- `LIVETALKING_SSL_CERT`: Path to SSL certificate (optional)
- `LIVETALKING_SSL_KEY`: Path to SSL private key (optional)

### Frontend Configuration

The frontend automatically connects to the backend. To change the backend URL, modify the API endpoints in the frontend code.

## Troubleshooting

### Common Issues

1. **Conda environment not found**
   ```bash
   conda env list
   conda create -n nerfstream python=3.10 -y
   ```

2. **Port already in use**
   - Change the port in your `.env` file or command line arguments
   - Check what's using the port: `lsof -i :8010`

3. **SSL Certificate errors**
   - The frontend generates self-signed certificates automatically
   - For production, provide proper SSL certificates via environment variables

4. **CUDA/GPU issues**
   - Ensure you have CUDA installed if using GPU acceleration
   - The system will fall back to CPU if GPU is not available

### Performance Optimization

- Adjust `LIVETALKING_BATCH_SIZE` based on your GPU memory
- Use `LIVETALKING_FPS` to balance quality vs. performance
- Consider using multiple workers in production: `--workers 4`

## Development

### Adding New Features

1. **Frontend**: Add components in `frontend/components/`
2. **Backend**: Add routers in `backend/app/routers/`
3. **Models**: Place new AI models in `backend/models/`
