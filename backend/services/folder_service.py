from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from models.folder import Folder
from exceptions.exceptions import FileUploadException


class FolderService:
    def __init__(self, db: Session):
        self.db = db

    def _build_path(self, folder: Folder) -> str:
        """Build the full path for a folder by traversing up the parent chain"""
        if folder.parent_folder_id is None:
            return f"/{folder.name}"
        
        parent = self.db.query(Folder).filter(Folder.id == folder.parent_folder_id).first()
        if parent:
            parent_path = self._build_path(parent)
            return f"{parent_path}/{folder.name}"
        return f"/{folder.name}"

    def _update_path(self, folder: Folder):
        """Update the path for a folder and all its children"""
        folder.path = self._build_path(folder)
        self.db.flush()
        
        # Recursively update children paths
        children = self.db.query(Folder).filter(Folder.parent_folder_id == folder.id).all()
        for child in children:
            self._update_path(child)

    def create_folder(self, user_id: UUID, name: str, parent_folder_id: Optional[UUID] = None) -> Folder:
        """
        Create a new folder.
        
        Args:
            user_id: ID of the user creating the folder
            name: Name of the folder
            parent_folder_id: Optional parent folder ID for nested folders
            
        Returns:
            Created Folder object
        """
        # Validate parent folder exists and belongs to user
        if parent_folder_id:
            parent = self.get_folder_by_id(parent_folder_id, user_id)
            if not parent:
                raise FileUploadException("Parent folder not found or access denied")
        
        # Check if folder with same name already exists in the same parent
        existing = self.db.query(Folder).filter(
            and_(
                Folder.user_id == user_id,
                Folder.name == name,
                Folder.parent_folder_id == parent_folder_id
            )
        ).first()
        
        if existing:
            raise FileUploadException(f"Folder '{name}' already exists in this location")
        
        # Create folder with initial path to avoid null constraint violation
        # We'll calculate the proper path after flush when we have the folder ID
        if parent_folder_id is None:
            initial_path = f"/{name}"
        else:
            # Get parent path for initial calculation
            parent = self.db.query(Folder).filter(Folder.id == parent_folder_id).first()
            if parent:
                initial_path = f"{parent.path}/{name}"
            else:
                initial_path = f"/{name}"
        
        folder = Folder(
            user_id=user_id,
            name=name,
            parent_folder_id=parent_folder_id,
            path=initial_path  # Set initial path to avoid null constraint violation
        )
        
        self.db.add(folder)
        self.db.flush()
        
        # Build and set proper path (now that folder has an ID and can be referenced)
        self._update_path(folder)
        self.db.commit()
        
        return folder

    def get_folder_by_id(self, folder_id: UUID, user_id: UUID) -> Optional[Folder]:
        """Get a folder by ID, ensuring it belongs to the user"""
        return self.db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.user_id == user_id
        ).first()

    def get_user_folders(
        self,
        user_id: UUID,
        parent_folder_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Folder]:
        """
        Get all folders for a user, optionally filtered by parent.
        
        Args:
            user_id: ID of the user
            parent_folder_id: Optional parent folder ID to filter by (None for root folders)
            skip: Number of records to skip
            limit: Maximum number of records to return
        """
        query = self.db.query(Folder).filter(Folder.user_id == user_id)
        
        if parent_folder_id is None:
            # Get root folders (no parent)
            query = query.filter(Folder.parent_folder_id.is_(None))
        else:
            # Validate parent belongs to user
            parent = self.get_folder_by_id(parent_folder_id, user_id)
            if not parent:
                raise FileUploadException("Parent folder not found or access denied")
            query = query.filter(Folder.parent_folder_id == parent_folder_id)
        
        return query.order_by(Folder.name.asc()).offset(skip).limit(limit).all()

    def get_folder_tree(self, user_id: UUID, parent_folder_id: Optional[UUID] = None) -> List[dict]:
        """
        Get folder tree structure recursively.
        
        Args:
            user_id: ID of the user
            parent_folder_id: Optional parent folder ID to start from (None for root)
            
        Returns:
            List of folder dictionaries with nested children
        """
        query = self.db.query(Folder).filter(Folder.user_id == user_id)
        
        if parent_folder_id is None:
            query = query.filter(Folder.parent_folder_id.is_(None))
        else:
            query = query.filter(Folder.parent_folder_id == parent_folder_id)
        
        folders = query.order_by(Folder.name.asc()).all()
        
        result = []
        for folder in folders:
            # Count files in this folder
            from models.file import File, FileStatus
            files_count = self.db.query(File).filter(
                and_(
                    File.folder_id == folder.id,
                    File.status != FileStatus.DELETED,
                    File.status != FileStatus.FAILED
                )
            ).count()
            
            # Recursively get children
            children = self.get_folder_tree(user_id, folder.id)
            
            result.append({
                "id": folder.id,
                "name": folder.name,
                "path": folder.path,
                "parent_folder_id": folder.parent_folder_id,
                "files_count": files_count,
                "children": children,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at
            })
        
        return result

    def update_folder(
        self,
        folder_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        parent_folder_id: Optional[UUID] = None
    ) -> Folder:
        """
        Update a folder's name and/or parent.
        
        Args:
            folder_id: ID of the folder to update
            user_id: ID of the user (for authorization)
            name: Optional new name
            parent_folder_id: Optional new parent folder ID
            
        Returns:
            Updated Folder object
        """
        folder = self.get_folder_by_id(folder_id, user_id)
        if not folder:
            raise FileUploadException("Folder not found or access denied")
        
        # Prevent moving folder into itself or its descendants
        if parent_folder_id is not None:
            if parent_folder_id == folder_id:
                raise FileUploadException("Cannot move folder into itself")
            
            # Check if new parent is a descendant
            if self._is_descendant(folder_id, parent_folder_id):
                raise FileUploadException("Cannot move folder into its own descendant")
            
            # Validate new parent exists and belongs to user
            new_parent = self.get_folder_by_id(parent_folder_id, user_id)
            if not new_parent:
                raise FileUploadException("Parent folder not found or access denied")
        
        # Check for name conflicts if name or parent is changing
        if name or parent_folder_id is not None:
            new_name = name if name else folder.name
            new_parent_id = parent_folder_id if parent_folder_id is not None else folder.parent_folder_id
            
            existing = self.db.query(Folder).filter(
                and_(
                    Folder.user_id == user_id,
                    Folder.name == new_name,
                    Folder.parent_folder_id == new_parent_id,
                    Folder.id != folder_id
                )
            ).first()
            
            if existing:
                raise FileUploadException(f"Folder '{new_name}' already exists in this location")
        
        # Update folder
        if name:
            folder.name = name
        if parent_folder_id is not None:
            folder.parent_folder_id = parent_folder_id
        
        # Update path for folder and all descendants
        self._update_path(folder)
        self.db.commit()
        
        return folder

    def move_folder(
        self,
        folder_id: UUID,
        user_id: UUID,
        parent_folder_id: Optional[UUID] = None
    ) -> Folder:
        """
        Move a folder to a different parent folder.
        
        Args:
            folder_id: ID of the folder to move
            user_id: ID of the user (for authorization)
            parent_folder_id: Destination parent folder ID (None for root)
            
        Returns:
            Updated Folder object
        """
        folder = self.get_folder_by_id(folder_id, user_id)
        if not folder:
            raise FileUploadException("Folder not found or access denied")
        
        # Prevent moving folder into itself or its descendants
        if parent_folder_id == folder_id:
            raise FileUploadException("Cannot move folder into itself")
        
        if parent_folder_id and self._is_descendant(folder_id, parent_folder_id):
            raise FileUploadException("Cannot move folder into its own descendant")
        
        # Validate new parent exists and belongs to user
        if parent_folder_id:
            new_parent = self.get_folder_by_id(parent_folder_id, user_id)
            if not new_parent:
                raise FileUploadException("Parent folder not found or access denied")
        
        # Check for name conflicts in the destination folder
        existing = self.db.query(Folder).filter(
            and_(
                Folder.user_id == user_id,
                Folder.name == folder.name,
                Folder.parent_folder_id == parent_folder_id,
                Folder.id != folder_id
            )
        ).first()
        
        if existing:
            folder_name = "root"
            if parent_folder_id:
                parent = self.get_folder_by_id(parent_folder_id, user_id)
                folder_name = parent.name if parent else "selected folder"
            raise FileUploadException(f"Folder '{folder.name}' already exists in {folder_name}")
        
        # Update parent_folder_id (can be None)
        folder.parent_folder_id = parent_folder_id
        
        # Update path for folder and all descendants
        self._update_path(folder)
        self.db.commit()
        
        return folder

    def _is_descendant(self, ancestor_id: UUID, potential_descendant_id: UUID) -> bool:
        """Check if potential_descendant_id is a descendant of ancestor_id"""
        current = self.db.query(Folder).filter(Folder.id == potential_descendant_id).first()
        while current and current.parent_folder_id:
            if current.parent_folder_id == ancestor_id:
                return True
            current = self.db.query(Folder).filter(Folder.id == current.parent_folder_id).first()
        return False

    def delete_folder(self, folder_id: UUID, user_id: UUID, force: bool = False) -> bool:
        """
        Delete a folder.
        
        Args:
            folder_id: ID of the folder to delete
            user_id: ID of the user (for authorization)
            force: If True, delete folder even if it contains files/subfolders
            
        Returns:
            True if deleted, False if not found
        """
        folder = self.get_folder_by_id(folder_id, user_id)
        if not folder:
            return False
        
        # Check for children folders
        children_count = self.db.query(Folder).filter(Folder.parent_folder_id == folder_id).count()
        
        # Check for files
        from models.file import File, FileStatus
        files_count = self.db.query(File).filter(
            and_(
                File.folder_id == folder_id,
                File.status != FileStatus.DELETED,
                File.status != FileStatus.FAILED
            )
        ).count()
        
        if not force and (children_count > 0 or files_count > 0):
            raise FileUploadException(
                f"Cannot delete folder: it contains {children_count} subfolder(s) and {files_count} file(s). "
                "Use force=true to delete anyway."
            )
        
        # If force is True, delete all children and files first
        if force:
            # Delete all child folders recursively
            children = self.db.query(Folder).filter(Folder.parent_folder_id == folder_id).all()
            for child in children:
                self.delete_folder(child.id, user_id, force=True)
            
            # Mark all files as deleted
            files = self.db.query(File).filter(File.folder_id == folder_id).all()
            for file in files:
                file.status = FileStatus.DELETED
        
        # Delete the folder
        self.db.delete(folder)
        self.db.commit()
        
        return True

    def get_folder_by_path(self, user_id: UUID, path: str) -> Optional[Folder]:
        """
        Get a folder by its full path.
        
        Args:
            user_id: ID of the user
            path: Full path (e.g., "/documents/projects")
            
        Returns:
            Folder object or None if not found
        """
        return self.db.query(Folder).filter(
            and_(
                Folder.user_id == user_id,
                Folder.path == path
            )
        ).first()
    
    def get_all_folders(self, user_id: UUID) -> List[Folder]:
        """
        Get all folders for a user (flat list, no hierarchy).
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of all folders
        """
        return self.db.query(Folder).filter(
            Folder.user_id == user_id
        ).all()

