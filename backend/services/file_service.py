from services.base import BaseService
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from models.file import File, FileStatus
from core.config import settings
from exceptions.exceptions import FileUploadException
from services.folder_service import FolderService

class FileService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)
        self.folder_service = FolderService(db)

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
            if folder_id:
                folder = self.folder_service.get_folder_by_id(folder_id, user_id)
                if not folder:
                    raise FileUploadException("Folder not found or access denied")
            
            storage_key = self._generate_storage_key(user_id, filename, folder_id, self.folder_service)
            
            file_record = File(
                user_id=user_id,
                name=filename,
                size=len(file_content),
                mime=mime_type,
                storage_key=storage_key,
                status=FileStatus.INITIATED,
                folder_id=folder_id
            )
            self.db.add(file_record)
            self.db.flush()
            
            try:
                upload_params = {
                    'Bucket': settings.R2_BUCKET_NAME,
                    'Key': storage_key,
                    'Body': file_content,
                }
                
                if mime_type:
                    upload_params['ContentType'] = mime_type
                
                self.s3_client.put_object(**upload_params)
                
                file_record.status = FileStatus.COMPLETED
                self.db.commit()
                
                return file_record
                
            except ClientError as e:
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
            try:
                self.s3_client.delete_object(
                    Bucket=settings.R2_BUCKET_NAME,
                    Key=file_record.storage_key
                )
            except ClientError as e:
                print(f"Warning: Failed to delete file from R2: {str(e)}")
            
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
        
        if folder_id is not None:
            if folder_id:
                folder = self.folder_service.get_folder_by_id(folder_id, user_id)
                if not folder:
                    raise FileUploadException("Folder not found or access denied")
        
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
        
        if folder_id:
            folder = self.folder_service.get_folder_by_id(folder_id, user_id)
            if not folder:
                raise FileUploadException("Folder not found or access denied")
        
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
