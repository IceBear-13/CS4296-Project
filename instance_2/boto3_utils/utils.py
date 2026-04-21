from boto3_utils.settings import session, s3_bucket_name, sqs_queue_url_a, sqs_queue_url_b
import os
from fastapi import UploadFile

s3_client = session.client("s3")
sqs_client = session.client("sqs")

def send_message_to_queue(queue_url, message_body):
    response = sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=message_body
    )
    return response

def receive_messages_from_queue(queue_url, max_messages=10, wait_time=20):
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=wait_time
    )
    return response.get("Messages", [])

def delete_message_from_queue(queue_url, receipt_handle):
    response = sqs_client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )
    return response

def upload_file_to_s3(file: UploadFile, object_name=None):
    if object_name is None:
        object_name = os.path.basename(file.filename)
    response = s3_client.upload_fileobj(file.file, s3_bucket_name, object_name)
    return response

def download_file_from_s3(object_name, file_path):
    response = s3_client.download_file(s3_bucket_name, object_name, file_path)
    return response
