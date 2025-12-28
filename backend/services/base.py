import boto3
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import uuid
import os
from core.config import settings

class BaseService:
    def __init__(self, db: Session):
        self.db = db
        self.s3_client = self._create_r2_client()
        self.PART_SIZE = 5 * 1024 * 1024
        self.PRESIGNED_URL_EXPIRY = 3600

    def _create_r2_client(self):
        """Create and return a boto3 S3 client configured for Cloudflare R2"""

        return boto3.client(
            's3',
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name='auto'
        )

    def _generate_storage_key(
        self, 
        user_id: UUID, 
        filename: str, 
        folder_id: Optional[UUID] = None,
        folder_service = None
    ) -> str:
        """Generate a unique storage key for the file in R2"""

        unique_id = str(uuid.uuid4())
        file_ext = os.path.splitext(filename)[1]
        base_name = os.path.splitext(filename)[0]
        
        if folder_id and folder_service:
            folder = folder_service.get_folder_by_id(folder_id, user_id)
            if folder:
                folder_path = folder.path.strip('/').replace(' ', '_').replace('/', '_')
                return f"users/{user_id}/{folder_path}/{unique_id}_{base_name}{file_ext}"
        
        return f"users/{user_id}/{unique_id}_{base_name}{file_ext}"