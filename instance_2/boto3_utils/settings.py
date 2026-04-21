import os
import boto3
from dotenv import load_dotenv

load_dotenv()

# Load AWS credentials from environment variables
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION")

# Comment if you have yet to create the SQS queues and S3 bucket
s3_bucket_name = os.getenv("S3_BUCKET_NAME")
sqs_queue_url_a = os.getenv("SQS_QUEUE_URL_A")
sqs_queue_url_b = os.getenv("SQS_QUEUE_URL_B")



if (aws_access_key_id and not aws_secret_access_key) or (aws_secret_access_key and not aws_access_key_id):
    raise ValueError(
        "Incomplete AWS credentials: set both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or neither to use default credentials."
    )

session_kwargs = {}
if aws_access_key_id and aws_secret_access_key:
    session_kwargs["aws_access_key_id"] = aws_access_key_id
    session_kwargs["aws_secret_access_key"] = aws_secret_access_key
if aws_region:
    session_kwargs["region_name"] = aws_region

session = boto3.Session(**session_kwargs)

# Uncomment if you have yet to create the SQS queues and S3 bucket

# Create S3 bucket
# s3_client.create_bucket(Bucket=[BUCKET_NAME], CreateBucketConfiguration={'LocationConstraint': aws_region})

# Create SQS queues
# sqs_client.create_queue(QueueName='[QUEUE_NAME_A]')
# sqs_client.create_queue(QueueName='[QUEUE_NAME_B]')

# Uncomment if you after creating
# s3_bucket_name = [BUCKET_NAME]
# sqs_queue_url_a = sqs_client.get_queue_url(QueueName='[QUEUE_NAME_A]')['QueueUrl']
# sqs_queue_url_b = sqs_client.get_queue_url(QueueName='[QUEUE_NAME_B]')['QueueUrl']