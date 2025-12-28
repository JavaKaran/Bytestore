from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from models.file import FileStatus


class FileUploadResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    size: int
    mime: Optional[str]
    storage_key: str
    status: FileStatus
    folder_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    size: int
    mime: Optional[str]
    storage_key: str
    status: FileStatus
    folder_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileUpdate(BaseModel):
    name: Optional[str] = None
    folder_id: Optional[UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "renamed_file.pdf",
                "folder_id": None
            }
        }


class FileMove(BaseModel):
    folder_id: Optional[UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "folder_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class MultipartInitiateRequest(BaseModel):
    """Request to initiate a multipart upload"""
    filename: str
    size: int
    fingerprint: str
    mime_type: Optional[str] = None
    folder_id: Optional[UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "large_video.mp4",
                "size": 104857600,
                "fingerprint": "1234567890",
                "mime_type": "video/mp4",
                "folder_id": None
            }
        }


class MultipartInitiateResponse(BaseModel):
    """Response after initiating multipart upload"""
    file_id: UUID
    upload_id: str
    part_size: int
    total_parts: int
    uploaded_parts: list[dict]

    class Config:
        from_attributes = True


class PresignedUrlResponse(BaseModel):
    """Presigned URL for uploading a part"""
    url: str
    part_number: int
    expires_in: int


class CompletedPart(BaseModel):
    """A completed upload part with its ETag"""
    part_number: int
    etag: str


class MultipartCompleteRequest(BaseModel):
    """Request to complete a multipart upload"""
    parts: list[CompletedPart]

    class Config:
        json_schema_extra = {
            "example": {
                "parts": [
                    {"part_number": 1, "etag": "\"abc123\""},
                    {"part_number": 2, "etag": "\"def456\""}
                ]
            }
        }


class PartUploadedRequest(BaseModel):
    """Request to mark a part as uploaded"""
    part_number: int
    etag: str


class UploadStatusResponse(BaseModel):
    """Current status of a multipart upload"""
    file_id: UUID
    upload_id: Optional[str]
    filename: str
    total_size: int
    total_parts: int
    uploaded_parts: list[int]
    status: FileStatus

    class Config:
        from_attributes = True

class UploadPartResponse(BaseModel):
    uploaded_parts: int
    total_parts: int

    class Config:
        from_attributes = True