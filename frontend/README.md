# Frontend - Video Transcoding Uploader

React + TypeScript frontend for submitting video transcoding jobs to the gateway API.

## Features

- Upload a video file with configurable transcoding options
- Includes requested profile options:
  - resolution
  - video_codec
  - audio_codec
  - ffmpeg_preset
  - crf
  - video_bitrate
- Shadcn-style component architecture for clean, reusable UI code
- Vite dev proxy for local FastAPI integration

## Run Locally

1. Install dependencies:

```bash
npm install
```

2. Start development server:

```bash
npm run dev
```

By default, API requests to /jobs/\* are proxied to http://localhost:8000.

## Optional Environment Variable

Create a .env file in this folder if you want a custom API base URL:

```env
VITE_API_BASE_URL=http://localhost:8000
```

If VITE_API_BASE_URL is not set, the app uses relative paths and relies on Vite proxy in development.

## Quality Checks

```bash
npm run lint
npm run build
```
