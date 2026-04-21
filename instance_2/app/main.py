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