# LiveTalking Frontend

A modern Next.js frontend for the LiveTalking WebRTC application.

## Features

- Real-time video/audio streaming via WebRTC
- Microphone recording with automatic WAV conversion
- Server-side recording integration
- Modern React hooks architecture
- TypeScript for type safety
- Tailwind CSS for styling

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
npm install
# or
yarn install
```

### Configuration

Create a `.env.local` file in the frontend directory with the following environment variables:

```env
# API Configuration
NEXT_PUBLIC_API_BASE_URL=https://52.3.240.147:8010

# WebRTC Configuration
NEXT_PUBLIC_TURN_SERVER_URL=turn:turn.anyfirewall.com:443?transport=tcp
NEXT_PUBLIC_TURN_USERNAME=webrtc
NEXT_PUBLIC_TURN_CREDENTIAL=webrtc

# Audio Configuration
NEXT_PUBLIC_AUDIO_SAMPLE_RATE=16000
NEXT_PUBLIC_AUDIO_CHANNEL_COUNT=1
NEXT_PUBLIC_AUDIO_ECHO_CANCELLATION=true
NEXT_PUBLIC_AUDIO_NOISE_SUPPRESSION=true
```

See `.env.local.example` for a complete example.

### Development

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── app/              # Next.js app directory
│   ├── page.tsx      # Main page component
│   ├── layout.tsx    # Root layout
│   └── globals.css   # Global styles
├── components/       # React components
│   ├── VideoPlayer.tsx
│   └── Controls.tsx
├── hooks/            # Custom React hooks
│   ├── useWebRTC.ts
│   └── useRecording.ts
├── services/         # API service layer
│   └── api.ts
├── types/            # TypeScript types
│   └── index.ts
└── utils/            # Utility functions
    └── config.ts
```

## Architecture

### Hooks

- **useWebRTC**: Manages WebRTC peer connection, video/audio streaming
- **useRecording**: Handles microphone recording and audio conversion

### Components

- **VideoPlayer**: Displays video and audio streams
- **Controls**: UI controls for connection and recording

### Services

- **api.ts**: API client for backend communication

### Utils

- **config.ts**: Centralized configuration management with environment variables

## API Endpoints

The frontend communicates with the backend at the following endpoints:

- `POST /offer` - WebRTC offer/answer negotiation
- `POST /record` - Start/stop server-side recording
- `POST /humanaudio` - Send recorded audio to server

## Browser Compatibility

- Chrome/Edge (recommended)
- Firefox
- Safari (may have limited WebRTC support)

## License

Same as the main LiveTalking project.

