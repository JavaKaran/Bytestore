from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid
from database import Base

class FileStatus(str, enum.Enum):
    INITIATED = "initiated"
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
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id"), nullable=True, index=True)
    storage_key = Column(String, nullable=False, unique=True, index=True)
    status = Column(Enum(FileStatus), default=FileStatus.INITIATED, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="file")
    upload = relationship("Upload", back_populates="file", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"File(id={self.id}, user_id={self.user_id}, name={self.name}, size={self.size}, mime={self.mime}, folder_id={self.folder_id}, storage_key={self.storage_key}, status={self.status}, created_at={self.created_at}, updated_at={self.updated_at})"
