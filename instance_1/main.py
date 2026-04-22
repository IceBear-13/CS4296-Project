from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from botocore.exceptions import ClientError
from boto3_utils.utils import (
    delete_message_from_queue,
    send_message_to_queue,
    receive_messages_from_queue,
    upload_file_to_s3,
    download_file_from_s3,
)
from boto3_utils.settings import sqs_queue_url_a, sqs_queue_url_b, s3_bucket_name
import json
import mimetypes
import os
import time
import uuid
from pydantic import BaseModel
from sanitize import sanitize_movie_filename
from fastapi.middleware.cors import CORSMiddleware

class RequestedProfile(BaseModel):
    resolution: str = "854:480"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    ffmpeg_preset: str = "medium"
    crf: int = 23
    video_bitrate: str = "1000k"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["localhost", "http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Status": "OK"}

def craft_message_body(job_id: str, bucket: str, key: str, requested_profile: RequestedProfile) -> str:
    return json.dumps({
        "job_id": job_id,
        "bucket": bucket,
        "key": key,
        "requested_profile": requested_profile.model_dump()
    })

def process_video(job_id: str, file: UploadFile, requested_profile: RequestedProfile) -> str:
    sanitized_filename = sanitize_movie_filename(file.filename)
    upload_file_to_s3(file, sanitized_filename)
    send_message_to_queue(
        sqs_queue_url_a,
        craft_message_body(job_id, s3_bucket_name, sanitized_filename, requested_profile),
    )

    output_path = f"output_{sanitized_filename}"
    deadline = time.time() + 300  # 5 minute timeout

    while time.time() < deadline:
        messages = receive_messages_from_queue(sqs_queue_url_b)
        for message in messages:
            try:
                message_body = json.loads(message["Body"])
            except (TypeError, json.JSONDecodeError):
                continue

            if message_body.get("job_id") != job_id:
                continue

            output_file = message_body.get("output_file") or message_body.get("key")
            if not output_file:
                raise HTTPException(status_code=500, detail="Transcoding result missing output_file/key.")

            print(f"Peak memory usage: {message_body.get('memory_usage_mb')}, peak CPU usage: {message_body.get('peak_cpu_usage_percent')}, average CPU usage: {message_body.get('average_cpu_usage_percent')}")
            output_bucket = message_body.get("bucket") or s3_bucket_name
            try:
                download_file_from_s3(output_file, output_path, output_bucket)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "Unknown")
                if code in {"404", "NoSuchKey", "NotFound"}:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Transcoded file not found in S3. bucket={output_bucket}, key={output_file}",
                    )
                raise
            delete_message_from_queue(sqs_queue_url_b, message["ReceiptHandle"])
            return output_path

    raise HTTPException(status_code=504, detail="Timed out waiting for transcoded video.")
    

@app.post("/transcode")
def transcode_video(
    file: UploadFile = File(...),
    requested_profile: str = Form(...),
):
    try:
        requested_profile_obj = RequestedProfile.model_validate_json(requested_profile)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid requested_profile. Provide JSON with fields: "
                "resolution, video_codec, audio_codec, ffmpeg_preset, crf, video_bitrate."
            ),
        )

    if not file.filename.endswith(('.mp4', '.avi', '.mkv')):
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a video file.")
    
    job_id = str(uuid.uuid4())
    output_path = process_video(job_id, file, requested_profile_obj)
    media_type = mimetypes.guess_type(output_path)[0] or "application/octet-stream"
    return FileResponse(
        path=output_path,
        media_type=media_type,
        filename=os.path.basename(output_path),
        background=BackgroundTask(lambda: os.path.exists(output_path) and os.remove(output_path)),
    )

@app.get("/transcoded/{file_name}")
def get_transcoded_video(file_name: str):
    sanitized_name = sanitize_movie_filename(file_name)
    output_path = f"output_{sanitized_name}"
    object_key = f"transcoded/{sanitized_name}"
    try:
        download_file_from_s3(object_key, output_path)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        if code in {"404", "NoSuchKey", "NotFound"}:
            raise HTTPException(status_code=404, detail="Transcoded video not found.")
        raise
    media_type = mimetypes.guess_type(output_path)[0] or "application/octet-stream"
    return FileResponse(
        path=output_path,
        media_type=media_type,
        filename=sanitized_name,
        background=BackgroundTask(lambda: os.path.exists(output_path) and os.remove(output_path)),
    )