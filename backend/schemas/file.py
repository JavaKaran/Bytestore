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

