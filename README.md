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

## Environment Requirements

### Hardware Requirements

- **RAM**: Minimum 8GB, recommended 16GB or more for optimal performance
- **GPU**: NVIDIA GPU with CUDA support (recommended for AI inference acceleration)
  - Minimum: GTX 1060 or equivalent
  - Recommended: RTX 3060 or higher
- **Storage**: Minimum 10GB free disk space
- **Network**: Stable internet connection (required for WebRTC streaming and model downloads)

### Software Requirements

- **Operating System**: Linux (Ubuntu 18.04+), macOS (10.15+), or Windows 10+
- **CUDA**: Version 11.0+ (if using GPU acceleration)
- **WebRTC-compatible browser**: Chrome 88+, Firefox 85+, Safari 14+, or Edge 88+

### Performance Notes

- GPU acceleration significantly improves avatar rendering performance
- CPU-only mode is supported but may result in lower frame rates
- Real-time video processing requires consistent CPU/GPU performance

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

### 4. Model Downloads

The LiveTalking backend requires several AI models to function. These models are not included in the repository and must be downloaded separately. Run the following commands from the `backend` directory:

```bash
cd backend
mkdir -p models

# Download MuseTalk models (main avatar generation model)
mkdir -p models/musetalkV15
# Download from: https://github.com/TMElyralab/MuseTalk
# Required files: unet.pth, musetalk.json

# Download Stable Diffusion VAE
mkdir -p models/sd-vae
# Download from: https://huggingface.co/stabilityai/sd-vae-ft-mse

# Download Whisper model (for audio processing)
mkdir -p models/whisper
# Choose one of the following Whisper models:
# Tiny (fastest, ~39MB): wget https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt
# Small (balanced, ~244MB): wget https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt
# Medium (accurate, ~776MB): wget https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt

# Download VQ-VAE model
# Download vqvae.pth to models/ directory
```

**Automated Download Script (Recommended):**

Create a download script for convenience:

```bash
#!/bin/bash
cd backend/models

# Download MuseTalk models
echo "Downloading MuseTalk models..."
# Visit https://github.com/TMElyralab/MuseTalk and download manually to musetalkV15/

# Download SD-VAE
echo "Downloading Stable Diffusion VAE..."
wget -O sd-vae/config.json https://huggingface.co/stabilityai/sd-vae-ft-mse/raw/main/config.json
wget -O sd-vae/diffusion_pytorch_model.bin https://huggingface.co/stabilityai/sd-vae-ft-mse/resolve/main/diffusion_pytorch_model.bin

# Download Whisper (choose size)
echo "Downloading Whisper model (small)..."
wget -P whisper/ https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt

# Download VQ-VAE
echo "Downloading VQ-VAE model..."
# Download from appropriate source to vqvae.pth

echo "Model download complete!"
```

**Model Sources:**
- **MuseTalk models**: [Official MuseTalk repository](https://github.com/TMElyralab/MuseTalk) - Download from releases or model zoo
- **Whisper models**: [OpenAI Whisper](https://github.com/openai/whisper) - Direct download links above
- **Stable Diffusion VAE**: [Hugging Face](https://huggingface.co/stabilityai/sd-vae-ft-mse)

**Note**: Some models may require you to agree to terms of service. The total download size is approximately 1-2GB depending on model choices. Whisper models are downloaded automatically on first use if not present.

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
