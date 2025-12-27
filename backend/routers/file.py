from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException, Query
from fastapi.responses import JSONResponse
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
    MultipartInitiateRequest,
    MultipartInitiateResponse,
    PresignedUrlResponse,
    MultipartCompleteRequest,
    PartUploadedRequest,
    UploadStatusResponse
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


@router.get("/", response_model=list[FileListResponse])
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


@router.post("/upload/initiate", response_model=MultipartInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_multipart_upload(
    request: MultipartInitiateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Initiate a resumable multipart upload.
    
    - **filename**: Name of the file to upload
    - **size**: Total file size in bytes
    - **mime_type**: Optional MIME type
    - **folder_id**: Optional folder ID
    
    Returns upload details including file_id, upload_id, part_size, and total_parts.
    """
    file_service = FileService(db)
    try:
        result = file_service.initiate_multipart_upload(
            user_id=current_user.id,
            filename=request.filename,
            size=request.size,
            mime_type=request.mime_type,
            folder_id=request.folder_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{file_id}/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_url_for_part(
    file_id: UUID,
    part_number: int = Query(..., ge=1, description="Part number (1-indexed)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a presigned URL for uploading a specific part.
    
    - **file_id**: ID of the file from initiate response
    - **part_number**: Part number to upload (1-indexed)
    
    Returns a presigned URL valid for 1 hour.
    """
    file_service = FileService(db)
    try:
        result = file_service.generate_presigned_url_for_part(
            file_id=file_id,
            user_id=current_user.id,
            part_number=part_number
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{file_id}/part-uploaded")
async def mark_part_as_uploaded(
    file_id: UUID,
    request: PartUploadedRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark a part as successfully uploaded.
    
    - **part_number**: Part number that was uploaded
    - **etag**: ETag returned by R2 for the uploaded part
    
    Returns the current upload progress.
    """
    file_service = FileService(db)
    try:
        result = file_service.mark_part_uploaded(
            file_id=file_id,
            user_id=current_user.id,
            part_number=request.part_number,
            etag=request.etag
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{file_id}/complete", response_model=FileUploadResponse)
async def complete_multipart_upload(
    file_id: UUID,
    request: MultipartCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Complete a multipart upload.
    
    - **parts**: List of {part_number, etag} for all uploaded parts
    
    Returns the completed file metadata.
    """
    file_service = FileService(db)
    try:
        parts = [{"part_number": p.part_number, "etag": p.etag} for p in request.parts]
        file_record = file_service.complete_multipart_upload(
            file_id=file_id,
            user_id=current_user.id,
            parts=parts
        )
        return file_record
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{file_id}/abort", status_code=status.HTTP_204_NO_CONTENT)
async def abort_multipart_upload(
    file_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Abort a multipart upload and cleanup.
    
    This will cancel the upload in R2 and mark the file as failed.
    """
    file_service = FileService(db)
    try:
        file_service.abort_multipart_upload(
            file_id=file_id,
            user_id=current_user.id
        )
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{file_id}/upload-status", response_model=UploadStatusResponse)
async def get_upload_status(
    file_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the current status of a multipart upload.
    
    Returns information about which parts have been uploaded,
    useful for resuming interrupted uploads.
    """
    file_service = FileService(db)
    try:
        result = file_service.get_upload_status(
            file_id=file_id,
            user_id=current_user.id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

