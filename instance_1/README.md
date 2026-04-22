# Video Transcoding API (FastAPI + AWS S3/SQS)

This service accepts an uploaded video, pushes a transcoding job to SQS, waits for a worker result message, downloads the transcoded output from S3, and returns the file to the client.

## How It Works

1. Client uploads a video to `POST /transcode`.
2. API sanitizes the filename and uploads the source file to S3.
3. API sends a job message to input queue `SQS_QUEUE_URL_A`.
4. API polls output queue `SQS_QUEUE_URL_B` for a message with the same `job_id`.
5. API downloads the generated output file from S3 and returns it as the response.

The API waits up to 5 minutes for the result before returning a timeout.

## Project Structure

- `main.py`: FastAPI app and end-to-end transcode request flow.
- `sanitize.py`: Filename sanitization helper for safe storage and processing.
- `boto3_utils/settings.py`: AWS/session/env configuration.
- `boto3_utils/utils.py`: S3 and SQS helper functions.
- `requirements.txt`: Python dependencies.
- `Dockerfile`: Container image definition.

## Prerequisites

- Python 3.10+ (Docker path uses Python 3.12 image)
- AWS access to:
	- one S3 bucket
	- two SQS queues (input and output)
- A worker service that:
	- reads from `SQS_QUEUE_URL_A`
	- transcodes the file
	- uploads output to the same S3 bucket
	- posts completion to `SQS_QUEUE_URL_B`

## Environment Variables

Create a `.env` file in the project root with:

```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=...
S3_BUCKET_NAME=...
SQS_QUEUE_URL_A=...
SQS_QUEUE_URL_B=...
```

Notes:

- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` must be set together, or both omitted to use default AWS credential resolution.
- `AWS_REGION` should be set to the region where your resources exist.

## Local Development

1. Create and activate a virtual environment:
	
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

4. Health check:

```bash
curl http://localhost:8000/
```

Expected response:

```json
{"Status":"OK"}
```

## Docker

Build:

```bash
docker build -t transcoding-api .
```

Run:

```bash
docker run --rm -p 8000:8000 --env-file .env transcoding-api
```

## API

### `GET /`

Returns service status.

### `POST /transcode`

Accepts multipart form data:

- `file`: video file (`.mp4`, `.avi`, `.mkv`)
- `requested_profile`: JSON string containing:
	- `resolution` (string)
	- `video_codec` (string)
	- `audio_codec` (string)
	- `ffmpeg_preset` (string)
	- `crf` (integer)
	- `video_bitrate` (string)

Example:

```bash
curl -X POST "http://localhost:8000/transcode" \
	-F 'file=@sample.mp4' \
	-F 'requested_profile={"resolution":"1920x1080","video_codec":"libx264","audio_codec":"aac","ffmpeg_preset":"medium","crf":23,"video_bitrate":"3000k"}'
```

On success, returns the transcoded file as a downloadable response.

## SQS Message Contract

### Input Queue (`SQS_QUEUE_URL_A`)

The API publishes JSON like:

```json
{
	"job_id": "uuid-string",
	"bucket": "your-s3-bucket",
	"key": "sanitized-input-filename.mp4",
	"requested_profile": {
		"resolution": "1920x1080",
		"video_codec": "libx264",
		"audio_codec": "aac",
		"ffmpeg_preset": "medium",
		"crf": 23,
		"video_bitrate": "3000k"
	}
}
```

### Output Queue (`SQS_QUEUE_URL_B`)

Your worker should publish JSON containing the same `job_id` and either:

- `output_file`, or
- `key`

Example:

```json
{
	"job_id": "same-uuid-as-input",
	"output_file": "output-video.mp4"
}
```

## Error Behavior

- `400`: invalid `requested_profile` JSON or unsupported file extension.
- `500`: worker result message missing `output_file` and `key`.
- `504`: no matching worker result received within 5 minutes.

## Notes

- Temporary output files are cleaned up automatically after response is sent.
- Ensure IAM permissions allow required S3 and SQS operations.
