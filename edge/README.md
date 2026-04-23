# Video Transcoding Service

A FastAPI-based service for transcoding videos using FFmpeg. This service allows users to upload a video and specify transcoding parameters such as resolution, codecs, and bitrate.

## Features
- **Video Transcoding**: Convert videos to different formats and resolutions.
- **Customizable Profiles**: Specify video/audio codecs, FFmpeg presets, CRF, and bitrate.
- **Resource Monitoring**: Tracks CPU and memory utilization during the transcoding process.
- **Dockerized**: Ready to deploy via Docker.

## Prerequisites
- Python 3.12+
- FFmpeg installed on the system

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd edge
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Start the server using uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Reference

### Transcode Video
`POST /transcode`

Uploads a video file and transcodes it based on the provided profile.

**Request Body (Multipart/form-data):**
- `file`: The video file to transcode.
- `request`: A JSON string containing the transcoding profile.

**Example Profile JSON:**
```json
{
  "resolution": "854:480",
  "video_codec": "libx264",
  "audio_codec": "aac",
  "ffmpeg_preset": "medium",
  "crf": 23,
  "video_bitrate": "1000k"
}
```

**Response:**
- `200 OK`: Returns the transcoded video file.
- `422 Unprocessable Entity`: Validation error in the request profile.
- `500 Internal Server Error`: Transcoding failed.

### Get Transcoded Video
`GET /trasncode/{filename}`

Retrieves a previously transcoded video from the temporary storage.

**Parameters:**
- `filename`: The original filename of the video.

## Docker Deployment

Build the image:
```bash
docker build -t video-transcoder .
```

Run the container:
```bash
docker run -p 8000:8000 video-transcoder
```
