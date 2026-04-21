import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.config import settings
from app.schemas import SubmitJobResponse

app = FastAPI(title="Transcoding Gateway", version="1.0.0")

s3_client = boto3.client("s3", region_name=settings.aws_region)
sqs_client = boto3.client("sqs", region_name=settings.aws_region)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs/transcode", response_model=SubmitJobResponse)
def submit_transcode_job(
    file: UploadFile = File(...),
    target_resolution: str = Form("480p"),
    target_video_codec: str = Form("libx264"),
    target_audio_codec: str = Form("aac"),
) -> SubmitJobResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file name is required.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    file.file.seek(0, 2)
    total_size = file.file.tell()
    file.file.seek(0)

    if total_size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max allowed: {settings.max_upload_mb} MB",
        )

    job_id = str(uuid.uuid4())
    extension = Path(file.filename).suffix or ".mp4"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    s3_input_key = f"{settings.input_prefix}/{timestamp}_{job_id}{extension}"

    try:
        s3_client.upload_fileobj(
            file.file,
            settings.s3_bucket,
            s3_input_key,
            ExtraArgs={
                "ContentType": file.content_type or "application/octet-stream",
            },
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=502, detail=f"Failed to upload to S3: {exc}") from exc

    message_body = {
        "job_id": job_id,
        "bucket": settings.s3_bucket,
        "input_key": s3_input_key,
        "requested_profile": {
            "resolution": target_resolution,
            "video_codec": target_video_codec,
            "audio_codec": target_audio_codec,
        },
        "submitted_at": datetime.now(UTC).isoformat(),
    }

    try:
        sqs_response = sqs_client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps(message_body),
            MessageAttributes={
                "job_id": {"DataType": "String", "StringValue": job_id},
                "input_key": {"DataType": "String", "StringValue": s3_input_key},
            },
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=502, detail=f"Failed to send SQS message: {exc}") from exc

    return SubmitJobResponse(
        job_id=job_id,
        s3_input_key=s3_input_key,
        sqs_message_id=sqs_response["MessageId"],
        status="queued",
    )
