from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from database import get_db
from models.user import User
from schemas.file import (
    FileUploadResponse, 
    FileListResponse, 
    FileUpdate, 
    FileMove,
    UserFilesResponse,
)
from services.file_service import FileService
from dependencies.auth import get_current_active_user

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[UUID] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a file to Cloudflare R2.
    
    - **file**: The file to upload
    - **folder_id**: Optional folder ID to organize files
    
    Returns file metadata including storage key and status.
    """
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    mime_type = file.content_type
    
    file_service = FileService(db)
    
    try:
        file_record = file_service.upload_file(
            user_id=current_user.id,
            file_content=file_content,
            filename=file.filename,
            mime_type=mime_type,
            folder_id=folder_id
        )
        return file_record
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/", response_model=UserFilesResponse)
async def list_files(
    folder_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all files for the current user.
    
    - **folder_id**: Optional filter by folder ID (None for root files)
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    """
    file_service = FileService(db)
    try:
        files = file_service.get_user_files(
            user_id=current_user.id,
            folder_id=folder_id,
            skip=skip,
            limit=limit
        )
        return files
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Failed to list files'
        )


@router.get("/{file_id}", response_model=FileUploadResponse)
async def get_file(
    file_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get file metadata by ID."""
    file_service = FileService(db)
    file_record = file_service.get_file_by_id(file_id, current_user.id)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return file_record


@router.get("/{file_id}/download-url")
async def get_download_url(
    file_id: UUID,
    expires_in: int = 3600,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a presigned URL for downloading a file.
    
    - **file_id**: ID of the file to download
    - **expires_in**: URL expiration time in seconds (default: 3600 = 1 hour)
    """
    file_service = FileService(db)
    url = file_service.get_file_download_url(file_id, current_user.id, expires_in)
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or not available"
        )
    
    return {"download_url": url, "expires_in": expires_in}


@router.put("/{file_id}", response_model=FileUploadResponse)
async def update_file(
    file_id: UUID,
    file_data: FileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a file's name and/or folder.
    
    - **name**: Optional new file name
    - **folder_id**: Optional new folder ID
    """
    file_service = FileService(db)
    try:
        file_record = file_service.update_file(
            file_id=file_id,
            user_id=current_user.id,
            name=file_data.name,
            folder_id=file_data.folder_id
        )
        return file_record
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail)
        )


@router.put("/{file_id}/move", response_model=FileUploadResponse)
async def move_file(
    file_id: UUID,
    move_data: FileMove,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Move a file to a different folder.
    
    - **folder_id**: Destination folder ID (None for root)
    """
    file_service = FileService(db)
    try:
        file_record = file_service.move_file(
            file_id=file_id,
            user_id=current_user.id,
            folder_id=move_data.folder_id
        )
        return file_record
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail) if hasattr(e, 'detail') else str(e)
        )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a file from R2 and mark as deleted in database."""
    file_service = FileService(db)
    success = file_service.delete_file(file_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return None

