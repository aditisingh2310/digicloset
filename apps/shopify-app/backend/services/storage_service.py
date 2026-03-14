"""
Image Storage Service

Handles storing generated images to S3 or local filesystem.
Provides fallback from S3 to local storage.
"""

import os
import logging
from typing import Optional, Union
from pathlib import Path
from datetime import datetime
import uuid
import httpx
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StorageAdapter(ABC):
    """Abstract storage adapter."""

    @abstractmethod
    async def save_image(
        self,
        image_data: bytes,
        filename: Optional[str] = None,
    ) -> str:
        """
        Save image and return public URL.

        Args:
            image_data: Image bytes
            filename: Optional filename

        Returns:
            Public URL to image
        """
        pass

    @abstractmethod
    async def delete_image(self, key: str) -> bool:
        """Delete image from storage."""
        pass

    @abstractmethod
    async def get_image(self, key: str) -> Optional[bytes]:
        """Get image from storage."""
        pass


class LocalStorageAdapter(StorageAdapter):
    """Local filesystem storage adapter."""

    def __init__(self, base_path: str = "/tmp/digicloset-storage"):
        """
        Initialize local storage.

        Args:
            base_path: Base directory for storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.tryons_dir = self.base_path / "try-ons"
        self.tryons_dir.mkdir(exist_ok=True)

    async def save_image(
        self,
        image_data: bytes,
        filename: Optional[str] = None,
    ) -> str:
        """Save image to local storage."""
        if not filename:
            filename = f"tryon_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"

        file_path = self.tryons_dir / filename

        try:
            file_path.write_bytes(image_data)
            logger.info(f"Saved image to {file_path}")

            # Return relative path that can be served
            return f"/storage/try-ons/{filename}"

        except Exception as e:
            logger.error(f"Failed to save image: {str(e)}")
            raise

    async def delete_image(self, key: str) -> bool:
        """Delete image from local storage."""
        file_path = self.tryons_dir / Path(key).name

        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted {file_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete image: {str(e)}")
            return False

    async def get_image(self, key: str) -> Optional[bytes]:
        """Get image from local storage."""
        file_path = self.tryons_dir / Path(key).name

        try:
            if file_path.exists():
                return file_path.read_bytes()
            return None

        except Exception as e:
            logger.error(f"Failed to read image: {str(e)}")
            return None


class S3StorageAdapter(StorageAdapter):
    """AWS S3 storage adapter."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        """
        Initialize S3 storage.

        Args:
            bucket: S3 bucket name
            region: AWS region
            access_key: AWS access key (from env if not provided)
            secret_key: AWS secret key (from env if not provided)
            endpoint_url: Custom endpoint (for MinIO, etc.)
        """
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 required for S3 storage: pip install boto3")

        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url

        # Get credentials from args or environment
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")

        if not self.access_key or not self.secret_key:
            raise ValueError("AWS credentials not provided")

        # Create client
        self.s3_client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=endpoint_url,
        )

    async def save_image(
        self,
        image_data: bytes,
        filename: Optional[str] = None,
    ) -> str:
        """Save image to S3."""
        if not filename:
            filename = f"tryon/{datetime.now().strftime('%Y/%m/%d')}/{uuid.uuid4().hex}.jpg"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=filename,
                Body=image_data,
                ContentType="image/jpeg",
                ACL="private",  # Changed to private for signed URLs
            )

            # Generate signed URL with expiration
            signed_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': filename},
                ExpiresIn=3600  # 1 hour expiration
            )

            logger.info(f"Saved image to S3 with signed URL: {filename}")
            return signed_url

        except Exception as e:
            logger.error(f"Failed to save image to S3: {str(e)}")
            raise

    async def delete_image(self, key: str) -> bool:
        """Delete image from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted from S3: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete from S3: {str(e)}")
            return False

    async def get_image(self, key: str) -> Optional[bytes]:
        """Get image from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()

        except self.s3_client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            logger.error(f"Failed to get image from S3: {str(e)}")
            return None

    async def schedule_cleanup(self, key: str, delay_hours: int = 24) -> None:
        """Schedule automatic deletion of image after delay."""
        try:
            # In production, use a job queue to schedule deletion
            # For now, set an expiration on the object
            from datetime import timedelta
            expiration = datetime.now() + timedelta(hours=delay_hours)
            self.s3_client.put_object_tagging(
                Bucket=self.bucket,
                Key=key,
                Tagging={
                    'TagSet': [
                        {'Key': 'auto-delete', 'Value': expiration.isoformat()}
                    ]
                }
            )
            logger.info(f"Scheduled cleanup for {key} at {expiration}")
        except Exception as e:
            logger.error(f"Failed to schedule cleanup for {key}: {str(e)}")


class StorageService:
    """High-level storage service with fallback support."""

    def __init__(self, primary: Optional[StorageAdapter] = None):
        """
        Initialize storage service.

        Args:
            primary: Primary storage adapter (defaults based on config)
        """
        self.primary = primary or self._create_default_adapter()
        self.fallback = LocalStorageAdapter()  # Always have local fallback

    @staticmethod
    def _create_default_adapter() -> StorageAdapter:
        """Create default adapter based on configuration."""
        storage_type = os.getenv("STORAGE_TYPE", "local").lower()

        if storage_type == "s3":
            return S3StorageAdapter(
                bucket=os.getenv("S3_BUCKET", "digicloset"),
                region=os.getenv("S3_REGION", "us-east-1"),
            )
        else:
            return LocalStorageAdapter(
                base_path=os.getenv(
                    "LOCAL_STORAGE_PATH",
                    "/tmp/digicloset-storage",
                )
            )

    async def save_image(
        self,
        image_data: bytes,
        filename: Optional[str] = None,
    ) -> str:
        """
        Save image with fallback support.

        Args:
            image_data: Image bytes
            filename: Optional filename

        Returns:
            Public URL to image
        """
        try:
            return await self.primary.save_image(image_data, filename)

        except Exception as e:
            logger.warning(f"Primary storage failed: {str(e)}, falling back to local")

            try:
                return await self.fallback.save_image(image_data, filename)

            except Exception as fallback_error:
                logger.error(f"Both storage methods failed: {str(fallback_error)}")
                raise

    async def download_and_save(
        self,
        image_url: str,
        filename: Optional[str] = None,
    ) -> str:
        """
        Download image from URL and save to storage.

        Args:
            image_url: URL to download from
            filename: Optional filename for storage

        Returns:
            Public URL in storage
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(image_url, follow_redirects=True)
                response.raise_for_status()

                image_data = response.content
                logger.info(f"Downloaded image: {image_url} ({len(image_data)} bytes)")

                return await self.save_image(image_data, filename)

        except Exception as e:
            logger.error(f"Failed to download and save image: {str(e)}")
            raise


_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
