"""S3 storage client for generated images"""

import logging
import os
from typing import Optional
from urllib.parse import urljoin
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3StorageService:
    """Manages image uploads and storage in AWS S3"""
    
    def __init__(
        self,
        bucket: Optional[str] = None,
        region: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        """Initialize S3 client"""
        self.bucket = bucket or os.getenv("S3_BUCKET")
        self.region = region or os.getenv("S3_REGION", "us-east-1")
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_KEY")
        self.s3_endpoint = os.getenv("S3_ENDPOINT_URL", None)
        
        # Validate configuration
        if not self.bucket:
            logger.warning("S3_BUCKET not configured - storage disabled")
            self.client = None
            return
        
        if not (self.access_key and self.secret_key):
            logger.warning("AWS credentials not configured - storage disabled")
            self.client = None
            return
        
        try:
            # Initialize S3 client
            session_kwargs = {
                "aws_access_key_id": self.access_key,
                "aws_secret_access_key": self.secret_key,
                "region_name": self.region
            }
            
            client_kwargs = {}
            if self.s3_endpoint:
                client_kwargs["endpoint_url"] = self.s3_endpoint
            
            session = boto3.Session(**session_kwargs)
            self.client = session.client("s3", **client_kwargs)
            
            # Test connection
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"S3 storage initialized: bucket={self.bucket}, region={self.region}")
            
        except ClientError as e:
            logger.error(f"S3 initialization failed: {e}")
            self.client = None
    
    def upload_image(
        self,
        file_data: bytes,
        key: str,
        content_type: str = "image/png",
        metadata: Optional[dict] = None
    ) -> Optional[str]:
        """
        Upload image to S3
        
        Args:
            file_data: Image file bytes
            key: S3 object key (path)
            content_type: MIME type
            metadata: Additional metadata
            
        Returns:
            Public URL of uploaded image or None
        """
        if not self.client:
            logger.warning("S3 client not initialized")
            return None
        
        try:
            # Build S3 put args
            put_args = {
                "Bucket": self.bucket,
                "Key": key,
                "Body": file_data,
                "ContentType": content_type
            }
            
            # Add metadata
            if metadata:
                put_args["Metadata"] = {
                    k: str(v) for k, v in metadata.items()
                }
            
            # Upload
            self.client.put_object(**put_args)
            
            # Generate public URL
            url = self._generate_public_url(key)
            logger.info(f"Uploaded image to S3: {key}")
            
            return url
            
        except ClientError as e:
            logger.error(f"Failed to upload image to S3: {e}")
            return None
    
    def generate_public_url(self, key: str, expiry_hours: int = 24) -> str:
        """
        Generate public URL for S3 object
        
        Args:
            key: S3 object key
            expiry_hours: URL expiry time
            
        Returns:
            Public URL
        """
        return self._generate_public_url(key, expiry_hours)
    
    def _generate_public_url(self, key: str, expiry_hours: int = 24) -> str:
        """
        Internal method to generate URL
        
        For public buckets, returns HTTPS URL.
        For private, generates signed URL.
        """
        if self.s3_endpoint:
            # Custom endpoint (e.g., MinIO)
            return f"{self.s3_endpoint}/{self.bucket}/{key}"
        
        # AWS S3
        if expiry_hours > 0:
            # Generate signed URL for private access
            try:
                url = self.client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': key},
                    ExpiresIn=expiry_hours * 3600
                )
                return url
            except ClientError as e:
                logger.error(f"Failed to generate signed URL: {e}")
                return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
        else:
            # Public URL
            return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
    
    def delete_image(self, key: str) -> bool:
        """
        Delete image from S3
        
        Args:
            key: S3 object key
            
        Returns:
            True if successful
        """
        if not self.client:
            return False
        
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted image from S3: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete image from S3: {e}")
            return False
    
    def delete_expired_files(self, prefix: str, age_hours: int = 48) -> int:
        """
        Delete images older than specified age
        
        Args:
            prefix: S3 key prefix
            age_hours: Age threshold in hours
            
        Returns:
            Number of deleted files
        """
        if not self.client:
            return 0
        
        try:
            from datetime import datetime, timedelta
            
            deleted_count = 0
            threshold = datetime.utcnow() - timedelta(hours=age_hours)
            
            # List objects with prefix
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    if obj['LastModified'].replace(tzinfo=None) < threshold:
                        self.client.delete_object(Bucket=self.bucket, Key=obj['Key'])
                        deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} expired images from S3")
            return deleted_count
            
        except ClientError as e:
            logger.error(f"Failed to delete expired files from S3: {e}")
            return 0


# Global storage instance
_storage_service = None


def get_storage_service() -> S3StorageService:
    """Get or create storage service singleton"""
    global _storage_service
    if _storage_service is None:
        _storage_service = S3StorageService()
    return _storage_service
