import threading
import time 
import boto3
import os
import json
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor
from botocore.exceptions import ClientError
from settings import session, sqs_queue_url_a, sqs_queue_url_b
from sanitize import sanitize_movie_filename
import psutil

s3_client = session.client('s3')
sqs_client = session.client('sqs')
TMP_DIR = os.getenv("TRANSCODE_TMP_DIR", "/tmp")
MIN_FREE_SPACE_BYTES = 500 * 1024 * 1024
SQS_VISIBILITY_TIMEOUT = int(os.getenv("SQS_VISIBILITY_TIMEOUT", "3600"))
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))


def has_enough_tmp_space(bucket_name: str, object_key: str) -> tuple[bool, str]:
    object_size = s3_client.head_object(Bucket=bucket_name, Key=object_key)["ContentLength"]
    free_bytes = shutil.disk_usage(TMP_DIR).free
    required_bytes = max(object_size * 2, MIN_FREE_SPACE_BYTES)

    if free_bytes < required_bytes:
        return False, (
            f"Not enough /tmp space for {object_key}: "
            f"need at least {required_bytes / (1024 * 1024):.2f} MB, "
            f"have {free_bytes / (1024 * 1024):.2f} MB"
        )

    return True, ""

def download_video_from_s3(
    s3_client: boto3.client, 
    bucket_name: str, 
    object_key: str, 
    download_path: str
):
    s3_client.download_file(bucket_name, object_key, download_path)

def upload_video_to_s3(
    s3_client: boto3.client, 
    bucket_name: str, 
    object_key: str, 
    file_path: str
):
    s3_client.upload_file(file_path, bucket_name, object_key)

def transcode_video(
    input_path: str, 
    output_path: str,
    video_codec: str, 
    audio_codec: str, 
    ffmpeg_preset: str, 
    scale: str, 
    crf: int, 
    video_bitrate: str | None
) -> tuple[bool, dict]:
    metrics = {
        "peak_cpu_usage_percent": 0.0,
        "average_cpu_usage_percent": 0.0,
        "memory_usage_mb": 0.0,
    }
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-i", input_path,
            "-c:v", video_codec,
            "-c:a", audio_codec,
            "-preset", ffmpeg_preset,
            "-vf", f"scale={scale}",
            "-crf", str(crf),
        ]

        if video_bitrate:
            cmd.extend(["-b:v", video_bitrate])
        cmd.append(output_path)

        ffmpeg_process = None
        cpu_samples = []
        peak_memory_bytes = 0
        last_progress_log = time.monotonic()

        print(f"Starting transcode for {input_path}")
        process = subprocess.Popen(cmd)
        try:
            ffmpeg_process = psutil.Process(process.pid)
            # Prime cpu_percent so subsequent samples represent actual usage.
            ffmpeg_process.cpu_percent(interval=None)
        except (psutil.Error, ProcessLookupError):
            ffmpeg_process = None

        while process.poll() is None:
            time.sleep(0.2)
            if not ffmpeg_process:
                continue
            try:
                cpu_usage = ffmpeg_process.cpu_percent(interval=None)
                memory_bytes = ffmpeg_process.memory_info().rss
                cpu_samples.append(cpu_usage)
                peak_memory_bytes = max(peak_memory_bytes, memory_bytes)
                if time.monotonic() - last_progress_log >= 30:
                    print(
                        f"Transcoding {input_path}: cpu={cpu_usage:.2f}% "
                        f"rss={memory_bytes / (1024 * 1024):.2f} MB"
                    )
                    last_progress_log = time.monotonic()
            except (psutil.Error, ProcessLookupError):
                ffmpeg_process = None

        if process.wait() != 0:
            print(f"Error occurred while transcoding video: {input_path}")
            return False, metrics

        if cpu_samples:
            metrics["peak_cpu_usage_percent"] = round(max(cpu_samples), 2)
            metrics["average_cpu_usage_percent"] = round(sum(cpu_samples) / len(cpu_samples), 2)
        metrics["memory_usage_mb"] = round(peak_memory_bytes / (1024 * 1024), 2)
        print(f"Finished transcode for {input_path}")
        return True, metrics
    except Exception as exc:
        print(f"Error occurred while transcoding video: {input_path}: {exc}")
        return False, metrics

def parse_video_message(message: dict) -> dict:
    try:
        video_info = json.loads(message.get('Body', '{}'))
        requested_profile = video_info.get("requested_profile") or {}
        if not isinstance(requested_profile, dict):
            print("Invalid message: requested_profile must be an object")
            return {}

        job_id = video_info.get("job_id")
        bucket = video_info.get("bucket")
        key = video_info.get("key")

        if not job_id or not bucket or not key:
            print("Invalid message: missing one or more required fields (job_id, bucket, key)")
            return {}

        resolution = requested_profile.get("resolution")
        video_codec = requested_profile.get("video_codec")
        audio_codec = requested_profile.get("audio_codec")
        ffmpeg_preset = requested_profile.get("ffmpeg_preset", "medium")
        crf = requested_profile.get("crf", 23)
        video_bitrate = requested_profile.get("video_bitrate")

        if not resolution or not video_codec or not audio_codec:
            print("Invalid message: requested_profile must include resolution, video_codec, and audio_codec")
            return {}

        return {
            "job_id": job_id,
            "bucket": bucket,
            "key": key,
            "resolution": resolution,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "ffmpeg_preset": ffmpeg_preset,
            "crf": crf,
            "video_bitrate": video_bitrate
        }
    except json.JSONDecodeError:
        print("Error decoding JSON message")
        return {}
    

def process_video_message(message: dict):
    video_info = parse_video_message(message)
    if not video_info:
        return False

    try:
        job_id = video_info["job_id"]
        bucket = video_info["bucket"]
        key = video_info["key"]
        resolution = video_info["resolution"]
        video_codec = video_info["video_codec"]
        audio_codec = video_info["audio_codec"]
        ffmpeg_preset = video_info["ffmpeg_preset"]
        crf = video_info["crf"]
        video_bitrate = video_info.get("video_bitrate")

        sanitized_filename = sanitize_movie_filename(key.split('/')[-1])
        input_path = f"{TMP_DIR}/{sanitized_filename}"
        output_path = f"{TMP_DIR}/transcoded-{sanitized_filename}"

        has_space, space_message = has_enough_tmp_space(bucket, key)
        if not has_space:
            print(space_message)
            return False

        print(f"Downloading {key} to {input_path}")
        download_video_from_s3(s3_client, bucket, key, input_path)

        try:
            transcode_ok, transcode_metrics = transcode_video(
                input_path,
                output_path,
                video_codec,
                audio_codec,
                ffmpeg_preset,
                resolution,
                crf,
                video_bitrate,
            )
            if not transcode_ok:
                sqs_client.send_message(
                    QueueUrl=sqs_queue_url_b,
                    MessageBody=json.dumps({
                        "job_id": job_id,
                        "bucket": bucket,
                        "key": key,
                        "status": "error",
                    })
                )
                
                return False

            output_key = f"transcoded/{sanitized_filename}"
            print(f"Uploading {output_path} to s3://{bucket}/{output_key}")
            upload_video_to_s3(s3_client, bucket, output_key, output_path)
            sqs_client.send_message(
                QueueUrl=sqs_queue_url_b,
                MessageBody=json.dumps({
                    "job_id": job_id,
                    "bucket": bucket,
                    "key": output_key,
                    "status": "completed",
                    "output_file": output_key,
                    "peak_cpu_usage_percent": transcode_metrics["peak_cpu_usage_percent"],
                    "average_cpu_usage_percent": transcode_metrics["average_cpu_usage_percent"],
                    "memory_usage_mb": transcode_metrics["memory_usage_mb"],
                })
            )

            # Acknowledge only after successful processing to avoid message loss.
            sqs_client.delete_message(
                QueueUrl=sqs_queue_url_a,
                ReceiptHandle=message['ReceiptHandle']
            )
            return True
        finally:
            for path in (input_path, output_path):
                if os.path.exists(path):
                    os.remove(path)
    except Exception as e:
        print(f"Error processing message: {e}")
        return False


def main():
    print("Waiting for messages in SQS Queue A...")

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS) as executor:
        while True:
            try:
                response = sqs_client.receive_message(
                    QueueUrl=sqs_queue_url_a,
                    MaxNumberOfMessages=MAX_CONCURRENT_JOBS,
                    WaitTimeSeconds=10,
                    VisibilityTimeout=SQS_VISIBILITY_TIMEOUT,
                )

                messages = response.get('Messages', [])
                if not messages:
                    continue
                
                print(f"Received {len(messages)} message(s) from SQS Queue A")
                for message in messages:
                    executor.submit(process_video_message, message)
            except ClientError as e:
                print(f"Error receiving messages from SQS: {e}")
                time.sleep(5)
            except Exception as e:
                print(f"Unexpected error: {e}")
                time.sleep(5)

        

if __name__ == "__main__":
    main()