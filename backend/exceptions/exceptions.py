from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base exception for all API errors"""
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers or {})


# Authentication Exceptions
class EmailAlreadyRegisteredException(BaseAPIException):
    """Raised when trying to register with an email that already exists"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )


class UsernameAlreadyTakenException(BaseAPIException):
    """Raised when trying to register with a username that already exists"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )


class InvalidCredentialsException(BaseAPIException):
    """Raised when login credentials are incorrect"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )


class InactiveUserException(BaseAPIException):
    """Raised when trying to access with an inactive user account"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )


class UserNotFoundException(BaseAPIException):
    """Raised when a user is not found"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


class AuthenticationException(BaseAPIException):
    """Raised when authentication fails"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


# File Upload Exceptions
class FileUploadException(BaseAPIException):
    """Raised when file upload fails"""
    def __init__(self, detail: str = "File upload failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class StorageLimitReachedException(BaseAPIException):
    """Raised when storage limit is reached or about to be reached"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only upload up to 30MB of files. Please delete some files to free up space."
        )