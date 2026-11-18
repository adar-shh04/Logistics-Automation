import os
import urllib.parse
from typing import Optional
import boto3
from botocore.config import Config


def get_s3_client():
    endpoint_url = os.environ.get("S3_ENDPOINT_URL") or None
    region_name = os.environ.get("AWS_REGION", "ap-south-1")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID") or None
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY") or None

    kwargs = {
        "region_name": region_name,
        "config": Config(s3={"addressing_style": "path"}),
    }
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key

    return boto3.client("s3", **kwargs)


def read_file_bytes(storage_uri: Optional[str] = None, file_path: Optional[str] = None) -> bytes:
    """Read binary file content from an s3:// URI or local file path."""
    if storage_uri and storage_uri.startswith("s3://"):
        parsed = urllib.parse.urlparse(storage_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        s3 = get_s3_client()
        resp = s3.get_object(Bucket=bucket, Key=key)
        return resp["Body"].read()

    # Local filesystem fallback
    target_path = None
    if storage_uri and storage_uri.startswith("file://"):
        target_path = storage_uri[len("file://"):]
    elif file_path:
        target_path = file_path

    if not target_path or not os.path.exists(target_path):
        raise FileNotFoundError(f"File not found at storage_uri='{storage_uri}', file_path='{file_path}'")

    with open(target_path, "rb") as f:
        return f.read()
