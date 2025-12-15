import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import uuid
from datetime import datetime
import os

from models.file import File, FileStatus
from core.config import settings
from exceptions.exceptions import FileUploadException
from services.folder_service import FolderService


class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.s3_client = self._create_r2_client()
        self.folder_service = FolderService(db)

    def _create_r2_client(self):
        """Create and return a boto3 S3 client configured for Cloudflare R2"""
        return boto3.client(
            's3',
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name='auto'  # R2 uses 'auto' as the region
        )

    def _generate_storage_key(self, user_id: UUID, filename: str, folder_id: Optional[UUID] = None) -> str:
        """Generate a unique storage key for the file in R2"""
        # Create a unique filename to avoid collisions
        unique_id = str(uuid.uuid4())
        file_ext = os.path.splitext(filename)[1]
        base_name = os.path.splitext(filename)[0]
        
        # Get folder path if folder_id is provided
        if folder_id:
            folder = self.folder_service.get_folder_by_id(folder_id, user_id)
            if folder:
                # Use folder path, sanitize it
                folder_path = folder.path.strip('/').replace(' ', '_').replace('/', '_')
                storage_key = f"users/{user_id}/{folder_path}/{unique_id}_{base_name}{file_ext}"
            else:
                storage_key = f"users/{user_id}/{unique_id}_{base_name}{file_ext}"
        else:
            storage_key = f"users/{user_id}/{unique_id}_{base_name}{file_ext}"
        
        return storage_key

    def upload_file(
        self,
        user_id: UUID,
        file_content: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        folder_id: Optional[UUID] = None
    ) -> File:
        """
        Upload a file to Cloudflare R2 and save metadata to database.
        
        Args:
            user_id: ID of the user uploading the file
            file_content: Binary content of the file
            filename: Original filename
            mime_type: MIME type of the file
            folder_id: Optional folder ID
            
        Returns:
            File object with metadata
        """
        try:
            # Validate folder belongs to user if provided
            if folder_id:
                folder = self.folder_service.get_folder_by_id(folder_id, user_id)
                if not folder:
                    raise FileUploadException("Folder not found or access denied")
            
            # Generate unique storage key
            storage_key = self._generate_storage_key(user_id, filename, folder_id)
            
            # Create file record in database with UPLOADING status
            file_record = File(
                user_id=user_id,
                name=filename,
                size=len(file_content),
                mime=mime_type,
                storage_key=storage_key,
                status=FileStatus.UPLOADING,
                folder_id=folder_id
            )
            self.db.add(file_record)
            self.db.flush()  # Flush to get the ID
            
            # Upload to R2
            try:
                upload_params = {
                    'Bucket': settings.R2_BUCKET_NAME,
                    'Key': storage_key,
                    'Body': file_content,
                }
                
                # Add content type if provided
                if mime_type:
                    upload_params['ContentType'] = mime_type
                
                self.s3_client.put_object(**upload_params)
                
                # Update status to COMPLETED
                file_record.status = FileStatus.COMPLETED
                self.db.commit()
                
                return file_record
                
            except ClientError as e:
                # If upload fails, update status to FAILED
                file_record.status = FileStatus.FAILED
                self.db.commit()
                raise FileUploadException(f"Failed to upload file to R2: {str(e)}")
                
        except Exception as e:
            self.db.rollback()
            raise FileUploadException(f"Error uploading file: {str(e)}")

    def get_file_by_id(self, file_id: UUID, user_id: UUID) -> Optional[File]:
        """Get a file by ID, ensuring it belongs to the user"""
        return self.db.query(File).filter(
            File.id == file_id,
            File.user_id == user_id
        ).first()

    def get_user_files(
        self,
        user_id: UUID,
        folder_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[File]:
        """Get all files for a user, optionally filtered by folder"""
        query = self.db.query(File).filter(
            File.user_id == user_id,
            File.status != FileStatus.DELETED
        )
        
        if folder_id is not None:
            # Validate folder belongs to user
            if folder_id:
                folder = self.folder_service.get_folder_by_id(folder_id, user_id)
                if not folder:
                    raise FileUploadException("Folder not found or access denied")
            query = query.filter(File.folder_id == folder_id)
        
        return query.order_by(File.created_at.desc()).offset(skip).limit(limit).all()

    def delete_file(self, file_id: UUID, user_id: UUID) -> bool:
        """Delete a file from R2 and mark as deleted in database"""
        file_record = self.get_file_by_id(file_id, user_id)
        
        if not file_record:
            return False
        
        try:
            # Delete from R2
            try:
                self.s3_client.delete_object(
                    Bucket=settings.R2_BUCKET_NAME,
                    Key=file_record.storage_key
                )
            except ClientError as e:
                # Log error but continue with database update
                print(f"Warning: Failed to delete file from R2: {str(e)}")
            
            # Mark as deleted in database
            file_record.status = FileStatus.DELETED
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise FileUploadException(f"Error deleting file: {str(e)}")

    def get_file_download_url(self, file_id: UUID, user_id: UUID, expires_in: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for downloading a file from R2.
        
        Args:
            file_id: ID of the file
            user_id: ID of the user requesting the file
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL or None if file not found
        """
        file_record = self.get_file_by_id(file_id, user_id)
        
        if not file_record or file_record.status != FileStatus.COMPLETED:
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.R2_BUCKET_NAME,
                    'Key': file_record.storage_key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            raise FileUploadException(f"Failed to generate download URL: {str(e)}")

