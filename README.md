# CS4296 Project

Video transcoding system with three parts:

- A React + TypeScript frontend for uploading a video and choosing output options
- A local FastAPI edge service that transcodes on the host with FFmpeg
- An AWS-backed pipeline made up of an API gateway and a worker that communicate through S3 and SQS

## Repository Layout

- [frontend](frontend) - Vite app for the user interface
- [edge](edge) - local FastAPI + FFmpeg service
- [instance_1](instance_1) - AWS-backed FastAPI API gateway
- [instance_2](instance_2) - AWS-backed worker that polls SQS and runs FFmpeg

## Prerequisites

- Python 3.11+ for the FastAPI services
- Node.js 18+ and npm for the frontend
- FFmpeg for transcoding
- AWS credentials and resources for the distributed pipeline

The AWS-backed services expect these environment variables:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `SQS_QUEUE_URL_A`
- `SQS_QUEUE_URL_B`

## Running Locally

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend app starts with Vite and is intended to talk to the transcoding API configured in the client.

### Local Edge Service

```bash
cd edge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### AWS API Gateway

```bash
cd instance_1
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### AWS Worker

```bash
cd instance_2
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m transcodeVideo
```

## Docker

Each service folder includes a Dockerfile. Build and run the service you need from that directory.

## How It Fits Together

1. The frontend uploads a video and submits transcoding options.
2. The edge service can transcode the file directly for local use.
3. The AWS gateway uploads the source file to S3 and enqueues a job on SQS.
4. The worker reads the job, downloads the source file, transcodes it with FFmpeg, uploads the result, and signals completion back to the gateway.

## Notes

- The AWS path requires S3 and two SQS queues to be created ahead of time.
- The worker and edge service both depend on FFmpeg being installed in the runtime environment.
