"""Integration tests for S3-compatible object storage operations."""

import json


def test_bucket_creation(s3_client):
    """Create a bucket and verify it appears in the bucket list."""
    s3_client.create_bucket(Bucket="test-bucket")
    buckets = s3_client.list_buckets()["Buckets"]
    bucket_names = [b["Name"] for b in buckets]
    assert "test-bucket" in bucket_names


def test_upload_and_download_json(s3_client):
    """Upload a JSON object and download it back."""
    s3_client.create_bucket(Bucket="json-bucket")
    payload = {"key": "value", "count": 42}
    s3_client.put_object(
        Bucket="json-bucket",
        Key="data/test.json",
        Body=json.dumps(payload),
        ContentType="application/json",
    )
    response = s3_client.get_object(Bucket="json-bucket", Key="data/test.json")
    body = json.loads(response["Body"].read())
    assert body == payload


def test_list_objects(s3_client):
    """List objects under a given prefix."""
    s3_client.create_bucket(Bucket="list-bucket")
    for i in range(3):
        s3_client.put_object(Bucket="list-bucket", Key=f"prefix/file{i}.txt", Body=f"data{i}")
    response = s3_client.list_objects_v2(Bucket="list-bucket", Prefix="prefix/")
    keys = [obj["Key"] for obj in response["Contents"]]
    assert len(keys) == 3
    assert "prefix/file0.txt" in keys


def test_delete_object(s3_client):
    """Delete an object and verify it is gone."""
    s3_client.create_bucket(Bucket="del-bucket")
    s3_client.put_object(Bucket="del-bucket", Key="to-delete.txt", Body="bye")
    s3_client.delete_object(Bucket="del-bucket", Key="to-delete.txt")
    response = s3_client.list_objects_v2(Bucket="del-bucket", Prefix="to-delete.txt")
    assert response.get("KeyCount", 0) == 0
