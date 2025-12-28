from fastapi import APIRouter, Depends, status, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID
from models.user import User
from schemas.file import MultipartInitiateRequest, MultipartInitiateResponse, PresignedUrlResponse, PartUploadedRequest, MultipartCompleteRequest, FileUploadResponse
from services.upload_service import UploadService
from dependencies.auth import get_current_active_user
from database import get_db

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/initiate", response_model=MultipartInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_multipart_upload(
    request: MultipartInitiateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Initiate a resumable multipart upload.
    
    - **filename**: Name of the file to upload
    - **size**: Total file size in bytes
    - **fingerprint**: Fingerprint of the file
    - **mime_type**: Optional MIME type
    - **folder_id**: Optional folder ID
    
    Returns upload details including file_id, upload_id, part_size, total_parts and uploaded_parts.
    """
    upload_service = UploadService(db)
    try:
        result = upload_service.initiate_multipart_upload(
            user_id=current_user.id,
            filename=request.filename,
            size=request.size,
            fingerprint=request.fingerprint,
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
    upload_service = UploadService(db)
    try:
        result = upload_service.generate_presigned_url_for_part(
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
    upload_service = UploadService(db)
    try:
        result = upload_service.mark_part_uploaded(
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
    upload_service = UploadService(db)
    try:
        parts = [{"part_number": p.part_number, "etag": p.etag} for p in request.parts]
        file_record = upload_service.complete_multipart_upload(
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
    upload_service = UploadService(db)
    try:
        upload_service.abort_multipart_upload(
            file_id=file_id,
            user_id=current_user.id
        )
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )