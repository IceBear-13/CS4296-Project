from pydantic import BaseModel


class SubmitJobResponse(BaseModel):
    job_id: str
    s3_input_key: str
    sqs_message_id: str
    status: str
