import threading
import time 
import boto3
# import os
import json
import subprocess
from botocore.exceptions import ClientError
from settings import session, sqs_queue_url_a, sqs_queue_url_b
from sanitize import sanitize_movie_filename

s3_client = session.client('s3')
sqs_client = session.client('sqs')

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
) -> bool:
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
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"Error occurred while transcoding video: {input_path}")
        return False

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
        input_path = f"/tmp/{sanitized_filename}"
        output_path = f"/tmp/transcoded-{sanitized_filename}"
        download_video_from_s3(s3_client, bucket, key, input_path)

        transcode_ok = transcode_video(
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
            return False

        output_key = f"transcoded/{sanitized_filename}"
        upload_video_to_s3(s3_client, bucket, output_key, output_path)
        sqs_client.send_message(
            QueueUrl=sqs_queue_url_b,
            MessageBody=json.dumps({
                "jobId": job_id,
                "bucket": bucket,
                "key": output_key,
            })
        )

        # Acknowledge only after successful processing to avoid message loss.
        sqs_client.delete_message(
            QueueUrl=sqs_queue_url_a,
            ReceiptHandle=message['ReceiptHandle']
        )
        return True
    except Exception as e:
        print(f"Error processing message: {e}")
        return False


def main():
    threads = []
    while True:
        print("Waiting for messages in SQS Queue A...")
        try:
            response = sqs_client.receive_message(
                QueueUrl=sqs_queue_url_a,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )

            messages = response.get('Messages', [])
            if not messages:
                continue
            
            else:
                for message in messages:
                    thread = threading.Thread(target=process_video_message, args=(message,))
                    thread.start()
                    threads.append(thread)
        except ClientError as e:
            print(f"Error receiving messages from SQS: {e}")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)

        

if __name__ == "__main__":
    main()