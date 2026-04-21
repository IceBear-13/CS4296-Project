from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    aws_region: str = Field(..., alias="AWS_REGION")
    s3_bucket: str = Field(..., alias="S3_BUCKET")
    sqs_queue_url: str = Field(..., alias="SQS_QUEUE_URL")
    input_prefix: str = Field(default="input", alias="INPUT_PREFIX")
    max_upload_mb: int = Field(default=1024, alias="MAX_UPLOAD_MB")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
