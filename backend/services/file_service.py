import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import uuid
from datetime import datetime
import os
import math

from models.file import File, FileStatus
from core.config import settings
from exceptions.exceptions import FileUploadException
from services.folder_service import FolderService

PART_SIZE = 5 * 1024 * 1024
PRESIGNED_URL_EXPIRY = 3600

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
            File.status != FileStatus.DELETED,
            File.status != FileStatus.FAILED
        )
        
        if folder_id is not None:
            # Validate folder belongs to user
            if folder_id:
                folder = self.folder_service.get_folder_by_id(folder_id, user_id)
                if not folder:
                    raise FileUploadException("Folder not found or access denied")
            query = query.filter(File.folder_id == folder_id)
        else:
            query = query.filter(File.folder_id == None)
        
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

    def update_file(
        self,
        file_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        folder_id: Optional[UUID] = None
    ) -> File:
        """
        Update a file's name and/or folder.
        
        Args:
            file_id: ID of the file to update
            user_id: ID of the user (for authorization)
            name: Optional new name
            folder_id: Optional new folder ID
            
        Returns:
            Updated File object
        """
        file_record = self.get_file_by_id(file_id, user_id)
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        # Validate folder belongs to user if provided
        if folder_id is not None:
            if folder_id:
                folder = self.folder_service.get_folder_by_id(folder_id, user_id)
                if not folder:
                    raise FileUploadException("Folder not found or access denied")
        
        # Check for name conflicts if name is changing
        if name:
            existing = self.db.query(File).filter(
                File.user_id == user_id,
                File.name == name,
                File.folder_id == (folder_id if folder_id is not None else file_record.folder_id),
                File.id != file_id,
                File.status != FileStatus.DELETED,
                File.status != FileStatus.FAILED
            ).first()
            
            if existing:
                raise FileUploadException(f"File '{name}' already exists in this location")
        
        # Update file
        if name:
            file_record.name = name
        if folder_id is not None:
            file_record.folder_id = folder_id
        
        self.db.commit()
        return file_record

    def move_file(
        self,
        file_id: UUID,
        user_id: UUID,
        folder_id: Optional[UUID] = None
    ) -> File:
        """
        Move a file to a different folder.
        
        Args:
            file_id: ID of the file to move
            user_id: ID of the user (for authorization)
            folder_id: Destination folder ID (None for root)
            
        Returns:
            Updated File object
        """
        file_record = self.get_file_by_id(file_id, user_id)
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        # Validate folder belongs to user if provided
        if folder_id:
            folder = self.folder_service.get_folder_by_id(folder_id, user_id)
            if not folder:
                raise FileUploadException("Folder not found or access denied")
        
        # Check for name conflicts in the destination folder
        existing = self.db.query(File).filter(
            File.user_id == user_id,
            File.name == file_record.name,
            File.folder_id == folder_id,
            File.id != file_id,
            File.status != FileStatus.DELETED,
            File.status != FileStatus.FAILED
        ).first()
        
        if existing:
            folder_name = "root"
            if folder_id:
                folder = self.folder_service.get_folder_by_id(folder_id, user_id)
                folder_name = folder.name if folder else "selected folder"
            raise FileUploadException(f"File '{file_record.name}' already exists in {folder_name}")
        
        # Update folder_id (can be None)
        file_record.folder_id = folder_id
        
        self.db.commit()
        return file_record

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

    def initiate_multipart_upload(
        self,
        user_id: UUID,
        filename: str,
        size: int,
        mime_type: Optional[str] = None,
        folder_id: Optional[UUID] = None
    ) -> dict:
        """
        Initiate a multipart upload to R2.
        
        Args:
            user_id: ID of the user
            filename: Original filename
            size: Total file size in bytes
            mime_type: MIME type of the file
            folder_id: Optional folder ID
            
        Returns:
            Dict with file_id, upload_id, part_size, total_parts
        """
        try:
            if folder_id:
                folder = self.folder_service.get_folder_by_id(folder_id, user_id)
                if not folder:
                    raise FileUploadException("Folder not found or access denied")
            
            # Generate unique storage key
            storage_key = self._generate_storage_key(user_id, filename, folder_id)
            
            # Calculate total parts
            total_parts = math.ceil(size / PART_SIZE)
            
            # Initiate multipart upload in R2
            try:
                multipart_params = {
                    'Bucket': settings.R2_BUCKET_NAME,
                    'Key': storage_key,
                }
                if mime_type:
                    multipart_params['ContentType'] = mime_type
                
                response = self.s3_client.create_multipart_upload(**multipart_params)
                upload_id = response['UploadId']
                
            except ClientError as e:
                raise FileUploadException(f"Failed to initiate multipart upload: {str(e)}")
            
            # Create file record in database with UPLOADING status
            file_record = File(
                user_id=user_id,
                name=filename,
                size=size,
                mime=mime_type,
                storage_key=storage_key,
                status=FileStatus.UPLOADING,
                folder_id=folder_id,
                upload_id=upload_id,
                total_parts=total_parts,
                uploaded_parts_json="[]"
            )
            self.db.add(file_record)
            self.db.commit()
            
            return {
                "file_id": file_record.id,
                "upload_id": upload_id,
                "part_size": PART_SIZE,
                "total_parts": total_parts
            }
            
        except FileUploadException:
            raise
        except Exception as e:
            self.db.rollback()
            raise FileUploadException(f"Error initiating multipart upload: {str(e)}")

    def generate_presigned_url_for_part(
        self,
        file_id: UUID,
        user_id: UUID,
        part_number: int
    ) -> dict:
        """
        Generate a presigned URL for uploading a specific part.
        
        Args:
            file_id: ID of the file
            user_id: ID of the user
            part_number: Part number (1-indexed)
            
        Returns:
            Dict with url, part_number, expires_in
        """
        file_record = self.get_file_by_id(file_id, user_id)
        
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        if file_record.status != FileStatus.UPLOADING:
            raise FileUploadException("Upload is not in progress")
        
        if not file_record.upload_id:
            raise FileUploadException("No active multipart upload for this file")
        
        if part_number < 1 or part_number > file_record.total_parts:
            raise FileUploadException(f"Invalid part number. Must be between 1 and {file_record.total_parts}")
        
        try:
            url = self.s3_client.generate_presigned_url(
                'upload_part',
                Params={
                    'Bucket': settings.R2_BUCKET_NAME,
                    'Key': file_record.storage_key,
                    'UploadId': file_record.upload_id,
                    'PartNumber': part_number
                },
                ExpiresIn=PRESIGNED_URL_EXPIRY
            )
            
            return {
                "url": url,
                "part_number": part_number,
                "expires_in": PRESIGNED_URL_EXPIRY
            }
            
        except ClientError as e:
            raise FileUploadException(f"Failed to generate presigned URL: {str(e)}")

    def mark_part_uploaded(
        self,
        file_id: UUID,
        user_id: UUID,
        part_number: int,
        etag: str
    ) -> dict:
        """
        Mark a part as uploaded and store its ETag.
        
        Args:
            file_id: ID of the file
            user_id: ID of the user
            part_number: Part number that was uploaded
            etag: ETag returned by R2 for the uploaded part
            
        Returns:
            Dict with uploaded_parts count
        """
        file_record = self.get_file_by_id(file_id, user_id)
        
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        if file_record.status != FileStatus.UPLOADING:
            raise FileUploadException("Upload is not in progress")
        
        # Add the part to uploaded parts
        file_record.add_uploaded_part(part_number, etag)
        self.db.commit()
        
        return {
            "uploaded_parts": len(file_record.uploaded_parts),
            "total_parts": file_record.total_parts
        }

    def complete_multipart_upload(
        self,
        file_id: UUID,
        user_id: UUID,
        parts: list[dict]
    ) -> File:
        """
        Complete a multipart upload.
        
        Args:
            file_id: ID of the file
            user_id: ID of the user
            parts: List of {part_number, etag} dicts
            
        Returns:
            Updated File object
        """
        file_record = self.get_file_by_id(file_id, user_id)
        
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        if file_record.status != FileStatus.UPLOADING:
            raise FileUploadException("Upload is not in progress")
        
        if not file_record.upload_id:
            raise FileUploadException("No active multipart upload for this file")
        
        try:
            # Format parts for S3 API
            s3_parts = [
                {
                    'ETag': part['etag'],
                    'PartNumber': part['part_number']
                }
                for part in sorted(parts, key=lambda x: x['part_number'])
            ]
            
            # Complete the multipart upload in R2
            self.s3_client.complete_multipart_upload(
                Bucket=settings.R2_BUCKET_NAME,
                Key=file_record.storage_key,
                UploadId=file_record.upload_id,
                MultipartUpload={'Parts': s3_parts}
            )
            
            # Update file status
            file_record.status = FileStatus.COMPLETED
            file_record.upload_id = None  # Clear upload ID
            self.db.commit()
            
            return file_record
            
        except ClientError as e:
            file_record.status = FileStatus.FAILED
            self.db.commit()
            raise FileUploadException(f"Failed to complete multipart upload: {str(e)}")

    def abort_multipart_upload(self, file_id: UUID, user_id: UUID) -> bool:
        """
        Abort a multipart upload and cleanup.
        
        Args:
            file_id: ID of the file
            user_id: ID of the user
            
        Returns:
            True if successfully aborted
        """
        file_record = self.get_file_by_id(file_id, user_id)
        
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        if file_record.status != FileStatus.UPLOADING:
            raise FileUploadException("No upload in progress to abort")
        
        try:
            # Abort multipart upload in R2 if upload_id exists
            if file_record.upload_id:
                try:
                    self.s3_client.abort_multipart_upload(
                        Bucket=settings.R2_BUCKET_NAME,
                        Key=file_record.storage_key,
                        UploadId=file_record.upload_id
                    )
                except ClientError as e:
                    # Log but continue - upload might have already been aborted
                    print(f"Warning: Failed to abort multipart upload in R2: {str(e)}")
            
            # Mark file as deleted/failed
            file_record.status = FileStatus.FAILED
            file_record.upload_id = None
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise FileUploadException(f"Error aborting upload: {str(e)}")

    def get_upload_status(self, file_id: UUID, user_id: UUID) -> dict:
        """
        Get the current status of a multipart upload.
        
        Args:
            file_id: ID of the file
            user_id: ID of the user
            
        Returns:
            Dict with upload status information
        """
        file_record = self.get_file_by_id(file_id, user_id)
        
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        return {
            "file_id": file_record.id,
            "upload_id": file_record.upload_id,
            "filename": file_record.name,
            "total_size": file_record.size,
            "total_parts": file_record.total_parts or 0,
            "uploaded_parts": file_record.get_uploaded_part_numbers(),
            "status": file_record.status
        }

