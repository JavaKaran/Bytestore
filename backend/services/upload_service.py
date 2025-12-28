from sqlalchemy.orm import Session
from models.uploads import Upload, UploadStatus
from typing import Optional
from uuid import UUID
from core.config import settings
from botocore.exceptions import ClientError
from services.file_service import FileService
from services.folder_service import FolderService
from models.file import File, FileStatus
from exceptions.exceptions import FileUploadException
import math
from core.config import settings
from models.upload_parts import UploadPart
from sqlalchemy.exc import IntegrityError
from services.base import BaseService

class UploadService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)
        self.file_service = FileService(db)
        self.folder_service = FolderService(db)

    def _get_upload_by_fingerprint(self, fingerprint: str) -> Optional[Upload]:
        """Get an upload by fingerprint"""
        return (
            self
                .db
                .query(Upload)
                .join(Upload.file)
                .filter(
                    Upload.file_fingerprint == fingerprint,
                    Upload.status == UploadStatus.INPROGRESS
                )
                .first()
        )

    def initiate_multipart_upload(
        self,
        user_id: UUID,
        filename: str,
        size: int,
        fingerprint: str,
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
            fingerprint: Fingerprint of the file
            folder_id: Optional folder ID
            
        Returns:
            Dict with file_id, upload_id, part_size, total_parts
        """
        try:
            upload = self._get_upload_by_fingerprint(fingerprint)
            
            if upload and upload.status == UploadStatus.INPROGRESS:
                file = upload.file

                return {
                    "file_id": file.id,
                    "upload_id": upload.upload_id,
                    "part_size": self.PART_SIZE,
                    "total_parts": upload.total_parts,
                    "uploaded_parts": [
                        {"part_number": p.part_number, "etag": p.etag}
                        for p in upload.parts
                    ]
                }
            
            storage_key = self._generate_storage_key(user_id, filename, folder_id, self.folder_service)
            
            total_parts = math.ceil(size / self.PART_SIZE)
            
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
            
            file_record = File(
                user_id=user_id,
                name=filename,
                size=size,
                mime=mime_type,
                folder_id=folder_id,
                storage_key=storage_key,
                status=FileStatus.INITIATED
            )

            upload_record = Upload(
                upload_id=upload_id,
                file_fingerprint=fingerprint,
                chunk_size=self.PART_SIZE,
                total_parts=total_parts,
                status=UploadStatus.INPROGRESS
            )

            file_record.upload = upload_record

            self.db.add(file_record)
            self.db.commit()
            
            return {
                "file_id": file_record.id,
                "upload_id": upload_id,
                "part_size": self.PART_SIZE,
                "total_parts": total_parts,
                "uploaded_parts": []
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
        file_record = self.file_service.get_file_by_id(file_id, user_id)
        
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        if file_record.status != FileStatus.INITIATED:
            raise FileUploadException("Upload is not in progress")
        
        if not file_record.upload.upload_id:
            raise FileUploadException("No active multipart upload for this file")
        
        if part_number < 1 or part_number > file_record.upload.total_parts:
            raise FileUploadException(f"Invalid part number. Must be between 1 and {file_record.upload.total_parts}")
        
        try:
            url = self.s3_client.generate_presigned_url(
                'upload_part',
                Params={
                    'Bucket': settings.R2_BUCKET_NAME,
                    'Key': file_record.storage_key,
                    'UploadId': file_record.upload.upload_id,
                    'PartNumber': part_number
                },
                ExpiresIn=self.PRESIGNED_URL_EXPIRY
            )
            
            return {
                "url": url,
                "part_number": part_number,
                "expires_in": self.PRESIGNED_URL_EXPIRY
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
        file_record = self.file_service.get_file_by_id(file_id, user_id)
        
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        if file_record.status != FileStatus.INITIATED or file_record.upload.status != UploadStatus.INPROGRESS:
            raise FileUploadException("Upload is not in progress")

        try:
            upload_part = UploadPart(
                part_number=part_number,
                etag=etag
            )

            file_record.upload.parts.append(upload_part)
            self.db.commit()

            uploaded_parts = (
                self.db.query(UploadPart)
                .filter(UploadPart.upload_id == file_record.upload.id)
                .count()
            )

            return {
                "uploaded_parts": uploaded_parts,
                "total_parts": file_record.upload.total_parts
            }
        
        except IntegrityError:
            self.db.rollback()
            pass

        except Exception as e:
            self.db.rollback()
            raise FileUploadException(f"Error marking part as uploaded: {str(e)}")

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
        file_record = self.file_service.get_file_by_id(file_id, user_id)
        
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        if file_record.status != FileStatus.INITIATED:
            raise FileUploadException("Upload is not in progress")
        
        if not file_record.upload.upload_id:
            raise FileUploadException("No active multipart upload for this file")
        
        try:
            s3_parts = [
                {
                    'ETag': part['etag'],
                    'PartNumber': part['part_number']
                }
                for part in sorted(parts, key=lambda x: x['part_number'])
            ]
            
            self.s3_client.complete_multipart_upload(
                Bucket=settings.R2_BUCKET_NAME,
                Key=file_record.storage_key,
                UploadId=file_record.upload.upload_id,
                MultipartUpload={'Parts': s3_parts}
            )
            
            file_record.status = FileStatus.COMPLETED
            file_record.upload.status = UploadStatus.COMPLETED

            self.db.commit()
            
            return file_record
            
        except ClientError as e:
            file_record.status = FileStatus.FAILED
            file_record.upload.status = UploadStatus.ABORTED
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
        file_record = self.file_service.get_file_by_id(file_id, user_id)
        
        if not file_record:
            raise FileUploadException("File not found or access denied")
        
        if file_record.status != FileStatus.INITIATED:
            raise FileUploadException("No upload in progress to abort")
        
        try:
            if file_record.upload.upload_id:
                try:
                    self.s3_client.abort_multipart_upload(
                        Bucket=settings.R2_BUCKET_NAME,
                        Key=file_record.storage_key,
                        UploadId=file_record.upload.upload_id
                    )
                except ClientError as e:
                    print(f"Warning: Failed to abort multipart upload in R2: {str(e)}")
            
            file_record.status = FileStatus.FAILED
            file_record.upload.status = UploadStatus.ABORTED
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise FileUploadException(f"Error aborting upload: {str(e)}")