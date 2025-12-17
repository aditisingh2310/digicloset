import os
import boto3
from botocore.exceptions import ClientError

S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
S3_BUCKET = os.environ.get("S3_BUCKET", "digicloset")

_s3 = boto3.resource('s3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name="us-east-1"
)

def ensure_bucket():
    try:
        _s3.meta.client.head_bucket(Bucket=S3_BUCKET)
    except ClientError:
        _s3.create_bucket(Bucket=S3_BUCKET)

def upload_fileobj(fileobj, key, content_type=None):
    ensure_bucket()
    obj = _s3.Object(S3_BUCKET, key)
    extra = {}
    if content_type:
        extra['ContentType'] = content_type
    obj.put(Body=fileobj.read(), **extra)
    return key
