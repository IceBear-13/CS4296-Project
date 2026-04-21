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

@app.post("/jobs/transcode", response_model=SubmitJobResponse)
def submit_transcode_job(
    file: UploadFile = File(...),
    target_resolution: str = Form("480p"),
    target_video_codec: str = Form("libx264"),
    target_audio_codec: str = Form("aac"),
) -> SubmitJobResponse: