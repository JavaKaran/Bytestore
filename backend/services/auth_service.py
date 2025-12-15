from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional
from uuid import UUID

from models.user import User
from schemas.auth import UserCreate, Token
from core.security import verify_password, get_password_hash, create_access_token
from core.config import settings
from exceptions.exceptions import (
    EmailAlreadyRegisteredException,
    UsernameAlreadyTakenException,
    InvalidCredentialsException,
    InactiveUserException,
    UserNotFoundException,
)


class AuthService:
    """Service layer for authentication business logic"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def register_user(self, user_data: UserCreate) -> User:
        """
        Register a new user.
        
        Args:
            user_data: User creation data (email, username, password)
            
        Returns:
            Created User object
            
        Raises:
            EmailAlreadyRegisteredException: If email already exists
            UsernameAlreadyTakenException: If username already exists
        """
        # Check if user with email already exists
        if self._user_exists_by_email(user_data.email):
            raise EmailAlreadyRegisteredException()
        
        # Check if username already exists
        if self._user_exists_by_username(user_data.username):
            raise UsernameAlreadyTakenException()
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password
        )
        
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        
        return new_user
    
    def authenticate_user(self, username: str, password: str) -> User:
        """
        Authenticate a user with username/email and password.
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            Authenticated User object
            
        Raises:
            InvalidCredentialsException: If credentials are invalid
            InactiveUserException: If user account is inactive
        """
        # Try to find user by username first, then by email
        user = self._get_user_by_username(username)
        if not user:
            user = self._get_user_by_email(username)
        
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsException()
        
        if not user.is_active:
            raise InactiveUserException()
        
        return user
    
    def create_access_token_for_user(self, user: User) -> Token:
        """
        Create a JWT access token for a user.
        
        Args:
            user: User object
            
        Returns:
            Token object with access_token and token_type
        """
        access_token_expires = timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer")
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User object if found, None otherwise
        """
        return self._get_user_by_username(username)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email.
        
        Args:
            email: Email to search for
            
        Returns:
            User object if found, None otherwise
        """
        return self._get_user_by_email(email)
    
    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            User object if found, None otherwise
            
        Raises:
            UserNotFoundException: If user is not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundException()
        return user
    
    # Private helper methods
    def _user_exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists"""
        return self.db.query(User).filter(User.email == email).first() is not None
    
    def _user_exists_by_username(self, username: str) -> bool:
        """Check if a user with the given username exists"""
        return self.db.query(User).filter(User.username == username).first() is not None
    
    def _get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()
    
    def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()

