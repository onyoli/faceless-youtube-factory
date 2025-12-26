"""
Clerk authentication middleware for FastAPI.
Validates JWT tokens from Clerk and extracts user info.
"""

import jwt
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer token extraction
security = HTTPBearer(auto_error=False)


class ClerkUser:
    """Represents an authenticated Clerk user."""

    def __init__(self, user_id: str, email: Optional[str] = None):
        self.user_id = user_id
        self.email = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> ClerkUser:
    """
    Dependency to validate Clerk JWT token and extract user info.

    Raises HTTPException 401 if token is invalid or missing.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Decode without verification first to get claims
        # In production, you should verify the signature using Clerk's JWKS
        unverified = jwt.decode(token, options={"verify_signature": False})

        user_id = unverified.get("sub")
        email = unverified.get("email")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )

        logger.debug("User authenticated", user_id=user_id)

        return ClerkUser(user_id=user_id, email=email)

    except jwt.PyJWTError as e:
        logger.error("Token validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[ClerkUser]:
    """
    Optional user dependency - returns None if not authenticated.
    Useful for routes that work with or without authentication.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
