from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Enum, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid
import json
from database import Base

class FileStatus(str, enum.Enum):
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"

class File(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    size = Column(BigInteger, nullable=False)
    mime = Column(String, nullable=True)
    storage_key = Column(String, nullable=False, unique=True, index=True)
    status = Column(Enum(FileStatus), default=FileStatus.UPLOADING, nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id"), nullable=True, index=True)
    upload_id = Column(String, nullable=True)
    total_parts = Column(Integer, nullable=True)
    uploaded_parts_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="files")

    @property
    def uploaded_parts(self) -> list[dict]:
        """Get uploaded parts as a list of dicts"""
        if self.uploaded_parts_json:
            return json.loads(self.uploaded_parts_json)
        return []

    @uploaded_parts.setter
    def uploaded_parts(self, parts: list[dict]):
        """Set uploaded parts from a list of dicts"""
        self.uploaded_parts_json = json.dumps(parts)

    def add_uploaded_part(self, part_number: int, etag: str):
        """Add a completed part to the uploaded parts list"""
        parts = self.uploaded_parts

        for part in parts:
            if part["part_number"] == part_number:
                part["etag"] = etag
                self.uploaded_parts = parts
                return
        parts.append({"part_number": part_number, "etag": etag})
        self.uploaded_parts = parts

    def get_uploaded_part_numbers(self) -> list[int]:
        """Get list of part numbers that have been uploaded"""
        return [part["part_number"] for part in self.uploaded_parts]

