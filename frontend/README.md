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

Set the API base URL in `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Or update `next.config.js` to use rewrites (already configured for localhost:8000).

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
    └── audioConverter.ts
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

- **audioConverter.ts**: Converts audio blobs to WAV format

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

