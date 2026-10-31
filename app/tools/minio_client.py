import asyncio
import io

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class MinioClient:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._bucket_created = False

    async def _ensure_bucket(self):
        if self._bucket_created:
            return
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._ensure_bucket_sync)
            self._bucket_created = True
        except S3Error:
            pass

    def _ensure_bucket_sync(self):
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    async def upload_image(self, object_name: str, image_data: bytes, content_type: str = "image/png") -> str:
        try:
            await self._ensure_bucket()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._upload_image_sync, object_name, image_data, content_type)
            return result
        except S3Error:
            return "https://example.com/placeholder.png"

    def _upload_image_sync(self, object_name: str, image_data: bytes, content_type: str) -> str:
        self.client.put_object(
            self.bucket_name,
            object_name,
            io.BytesIO(image_data),
            len(image_data),
            content_type=content_type,
        )
        return f"http://{settings.MINIO_ENDPOINT}/{self.bucket_name}/{object_name}"

    async def download_image(self, object_name: str) -> bytes:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._download_image_sync, object_name)
        except S3Error:
            return b""

    def _download_image_sync(self, object_name: str) -> bytes:
        response = self.client.get_object(self.bucket_name, object_name)
        return response.read()

    def get_image_url(self, object_name: str) -> str:
        return f"http://{settings.MINIO_ENDPOINT}/{self.bucket_name}/{object_name}"
