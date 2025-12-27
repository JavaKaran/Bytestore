from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from database import get_db
from models.user import User
from schemas.folder import (
    FolderCreate,
    FolderUpdate,
    FolderMove,
    FolderResponse,
    FolderWithChildrenResponse,
    FolderTreeResponse
)
from services.folder_service import FolderService
from dependencies.auth import get_current_active_user

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post("/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new folder.
    
    - **name**: Name of the folder
    - **parent_folder_id**: Optional parent folder ID for nested folders
    """
    folder_service = FolderService(db)
    try:
        folder = folder_service.create_folder(
            user_id=current_user.id,
            name=folder_data.name,
            parent_folder_id=folder_data.parent_folder_id
        )
        return folder
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.detail
        )


@router.get("/", response_model=list[FolderResponse])
async def list_folders(
    parent_folder_id: Optional[UUID] = Query(None, description="Filter by parent folder ID (None for root folders)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List folders for the current user.
    
    - **parent_folder_id**: Optional parent folder ID to filter by (None for root folders)
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    """
    folder_service = FolderService(db)
    try:
        folders = folder_service.get_user_folders(
            user_id=current_user.id,
            parent_folder_id=parent_folder_id,
            skip=skip,
            limit=limit
        )
        return folders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Failed to list folders'
        )


@router.get("/tree", response_model=list[FolderTreeResponse])
async def get_folder_tree(
    parent_folder_id: Optional[UUID] = Query(None, description="Start from specific parent folder (None for root)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get folder tree structure recursively.
    
    - **parent_folder_id**: Optional parent folder ID to start from (None for root)
    
    Returns hierarchical folder structure with nested children.
    """
    folder_service = FolderService(db)
    try:
        tree = folder_service.get_folder_tree(
            user_id=current_user.id,
            parent_folder_id=parent_folder_id
        )
        return tree
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Failed to get folder tree'
        )


@router.get("/all", response_model=list[FolderResponse])
async def get_all_folders(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all folders for the current user (flat list).
    """
    folder_service = FolderService(db)
    try:
        folders = folder_service.get_all_folders(current_user.id)
        return folders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Failed to get all folders'
        )


@router.put("/{folder_id}/move", response_model=FolderResponse)
async def move_folder(
    folder_id: UUID,
    move_data: FolderMove,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Move a folder to a different parent folder.
    
    - **parent_folder_id**: New parent folder ID (None for root)
    """
    folder_service = FolderService(db)
    try:
        folder = folder_service.move_folder(
            folder_id=folder_id,
            user_id=current_user.id,
            parent_folder_id=move_data.parent_folder_id
        )
        return folder
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail) if hasattr(e, 'detail') else str(e)
        )


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get folder metadata by ID."""
    folder_service = FolderService(db)
    folder = folder_service.get_folder_by_id(folder_id, current_user.id)
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    return folder


@router.get("/path/{path:path}", response_model=FolderResponse)
async def get_folder_by_path(
    path: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get folder by its full path.
    
    - **path**: Full folder path (e.g., "/documents/projects")
    """
    folder_service = FolderService(db)
    folder = folder_service.get_folder_by_path(current_user.id, path)
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    return folder


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: UUID,
    folder_data: FolderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a folder's name and/or parent.
    
    - **name**: Optional new folder name
    - **parent_folder_id**: Optional new parent folder ID
    """
    folder_service = FolderService(db)
    try:
        folder = folder_service.update_folder(
            folder_id=folder_id,
            user_id=current_user.id,
            name=folder_data.name,
            parent_folder_id=folder_data.parent_folder_id
        )
        return folder
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail) if hasattr(e, 'detail') else 'Failed to update folder'
        )


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: UUID,
    force: bool = Query(False, description="Force delete even if folder contains files/subfolders"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a folder.
    
    - **folder_id**: ID of the folder to delete
    - **force**: If true, delete folder even if it contains files/subfolders
    """
    folder_service = FolderService(db)
    try:
        success = folder_service.delete_folder(folder_id, current_user.id, force=force)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )
        
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail) if hasattr(e, 'detail') else 'Failed to delete folder'
        )

