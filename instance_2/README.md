# Video Transcode Worker (Instance A)

This service listens to an input SQS queue, downloads videos from S3, transcodes them with FFmpeg, uploads the output back to S3, and sends a completion message to an output SQS queue.

## What It Does

1. Polls `SQS_QUEUE_URL_A` for jobs.
2. Expects each job to include video location and transcoding profile.
3. Downloads the source object from S3 to `/tmp`.
4. Runs FFmpeg with the requested profile.
5. Uploads output to `transcoded/<sanitized_filename>` in S3.
6. Sends result metadata to `SQS_QUEUE_URL_B`.
7. Deletes the source queue message only after successful processing.

## Project Files

- `transcodeVideo.py`: main worker loop and processing logic.
- `settings.py`: AWS/session/env configuration.
- `sanitize.py`: filename sanitization for safe local temp paths.
- `requirements.txt`: Python dependencies.
- `Dockerfile`: container build and runtime definition.

## Prerequisites

- Python 3.12+
- FFmpeg installed and available in `PATH`
- AWS credentials with permissions for:
	- S3 `GetObject` and `PutObject`
	- SQS `ReceiveMessage`, `DeleteMessage`, `SendMessage`

## Environment Variables

Create a `.env` file in this directory.

Required for AWS resources:

- `SQS_QUEUE_URL_A`: input queue URL
- `SQS_QUEUE_URL_B`: output queue URL
- `S3_BUCKET_NAME`: bucket name (used by your environment/config)

AWS credentials options:

- Option 1: set both
	- `AWS_ACCESS_KEY_ID`
	- `AWS_SECRET_ACCESS_KEY`
- Option 2: set neither and use default AWS credential chain (instance role, profile, etc.)

Optional:

- `AWS_REGION`

Example `.env`:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-southeast-1
S3_BUCKET_NAME=your-bucket
SQS_QUEUE_URL_A=https://sqs.<region>.amazonaws.com/<account>/<queue-a>
SQS_QUEUE_URL_B=https://sqs.<region>.amazonaws.com/<account>/<queue-b>
```

## Message Format (Queue A)

Expected SQS message body JSON:

```json
{
	"job_id": "job-123",
	"bucket": "your-bucket",
	"key": "uploads/input.mp4",
	"requested_profile": {
		"resolution": "1280:720",
		"video_codec": "libx264",
		"audio_codec": "aac",
		"ffmpeg_preset": "medium",
		"crf": 23,
		"video_bitrate": "2000k"
	}
}
```

Required fields:

- Top level: `job_id`, `bucket`, `key`
- `requested_profile`: `resolution`, `video_codec`, `audio_codec`

Defaults:

- `ffmpeg_preset`: `medium`
- `crf`: `23`
- `video_bitrate`: optional

## Run Locally

1. Create and activate virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start worker:

```bash
python -m transcodeVideo
```

## Run with Docker

Build image:

```bash
sudo docker buildx build -t instance_a:latest .
```

Run container (loads `.env`):

```bash
sudo docker run --rm --env-file .env instance_a:latest
```

## Output Message (Queue B)

On success, the worker sends:

```json
{
	"job_id": "job-123",
	"bucket": "your-bucket",
	"key": "transcoded/input.mp4",
	"output_file": "transcoded/input.mp4"
}
```

## Troubleshooting

- `Incomplete AWS credentials`:
	Set both `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`, or set neither.

- Docker build fails at pip install on Ubuntu 24 base image:
	The Dockerfile uses an internal virtual environment (`/opt/venv`) to avoid externally-managed pip restrictions.

- FFmpeg errors during transcode:
	Verify input object exists, codecs are valid, and `resolution` format is valid (for example `1280:720`).

