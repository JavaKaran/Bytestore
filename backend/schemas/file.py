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

