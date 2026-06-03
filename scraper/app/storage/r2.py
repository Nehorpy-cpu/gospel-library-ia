from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError
from botocore.client import Config

from app.core.config import get_settings
from app.utils.hashing import sha256_bytes


@dataclass(frozen=True)
class StoredObject:
    key: str
    checksum: str
    size_bytes: int
    content_type: str | None


class R2Storage:
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.r2_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=str(settings.r2_endpoint_url),
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name=settings.r2_region,
            config=Config(signature_version="s3v4"),
        )

    def ensure_bucket(self) -> None:
        try:
            buckets = self.client.list_buckets().get("Buckets", [])
            if not any(bucket["Name"] == self.bucket for bucket in buckets):
                self.client.create_bucket(Bucket=self.bucket)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code not in {"AccessDenied", "NotImplemented", "InvalidAccessKeyId"}:
                raise

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> StoredObject:
        checksum = sha256_bytes(data)
        extra_args = {"ContentType": content_type} if content_type else {}
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra_args)
        return StoredObject(
            key=key,
            checksum=checksum,
            size_bytes=len(data),
            content_type=content_type,
        )

    def get_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()
