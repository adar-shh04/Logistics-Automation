import os
import pytest
import boto3
from moto import mock_aws
from app.storage import read_file_bytes, get_s3_client


def test_read_local_file_via_path(tmp_path):
    f = tmp_path / "test.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\nfakecontent")

    data = read_file_bytes(file_path=str(f))
    assert data == b"\x89PNG\r\n\x1a\nfakecontent"


def test_read_local_file_via_uri(tmp_path):
    f = tmp_path / "test.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\nfakecontent")
    uri = f"file://{f.resolve()}"

    data = read_file_bytes(storage_uri=uri)
    assert data == b"\x89PNG\r\n\x1a\nfakecontent"


def test_read_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_file_bytes(file_path="/nonexistent/path/never_there.png")


@mock_aws
def test_read_s3_file(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)

    s3 = boto3.client("s3", region_name="ap-south-1")
    s3.create_bucket(
        Bucket="logistics-uploads",
        CreateBucketConfiguration={"LocationConstraint": "ap-south-1"}
    )
    s3.put_object(
        Bucket="logistics-uploads",
        Key="uploads/inv_123.png",
        Body=b"\x89PNG\r\n\x1a\ncloudcontent"
    )

    data = read_file_bytes(storage_uri="s3://logistics-uploads/uploads/inv_123.png")
    assert data == b"\x89PNG\r\n\x1a\ncloudcontent"
