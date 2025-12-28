from .auth import router as auth_router
from .file import router as file_router
from .folder import router as folder_router
from .upload import router as upload_router

__all__ = ["auth_router", "file_router", "folder_router", "upload_router"]