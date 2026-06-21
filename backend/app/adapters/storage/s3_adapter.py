import uuid

import boto3
from botocore.client import Config

from app.adapters.storage.port import ObjectStoragePort
from app.core.config import get_settings

settings = get_settings()


class S3ObjectStorageAdapter:
    def __init__(self) -> None:
        self.bucket = settings.object_storage_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.object_storage_endpoint,
            aws_access_key_id=settings.object_storage_access_key,
            aws_secret_access_key=settings.object_storage_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def create_upload_url(self, *, key: str, content_type: str, expires_seconds: int = 900) -> str:
        url = self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_seconds,
        )
        return str(url)

    def create_download_url(self, *, key: str, expires_seconds: int = 900) -> str:
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
        return str(url)


def build_document_storage_key(*, organization_id: str, patient_id: str, filename: str) -> str:
    safe_name = filename.replace("/", "_")
    return f"org/{organization_id}/patients/{patient_id}/documents/{uuid.uuid4()}-{safe_name}"


def build_recording_storage_key(*, organization_id: str, session_id: str, filename: str) -> str:
    safe_name = filename.replace("/", "_")
    return f"org/{organization_id}/sessions/{session_id}/recordings/{uuid.uuid4()}-{safe_name}"


def get_object_storage_adapter() -> ObjectStoragePort:
    return S3ObjectStorageAdapter()
