# app/oauth2.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   Handles everything related to JWT (JSON Web Token) authentication:
#     1. Creating access tokens when a user logs in
#     2. Verifying tokens on protected route requests
#     3. Extracting the current user from a token
#
# JWT FLOW:
#   Login → create_access_token() → returns signed token to client
#   Client sends token in header: Authorization: Bearer <token>
#   Protected route → verify_access_token() → returns User object
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app import models
from app.database import SessionLocal


# ── OAuth2 scheme ─────────────────────────────────────────────────────────────
# Tells FastAPI:
#   - Clients must send the token in: Authorization: Bearer <token>
#   - The token is obtained at the /auth/login endpoint
# This also makes the Authorize button appear in Swagger UI (/docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# =============================================================================
# CREATE ACCESS TOKEN
# =============================================================================
def create_access_token(data: dict,
                        expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a signed JWT access token.

    Args:
        data: dict — payload to encode, typically {"sub": str(user.id)}
        expires_delta: optional custom expiry duration

    Returns:
        A signed JWT string, e.g. "eyJhbGciOiJIUzI1NiIsInR5cCI6..."

    The token contains:
        "sub" → the user's ID (as string)
        "exp" → expiry timestamp
    """
    to_encode = data.copy()

    # Calculate expiry time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    # Sign the token with our secret key
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


# =============================================================================
# VERIFY ACCESS TOKEN
# =============================================================================
def verify_access_token(token: str, db: Session) -> models.User:
    """
    Decodes and validates a JWT token, then fetches the user from the DB.

    Called by get_current_user() on every protected request.

    Raises:
        401 Unauthorized — if token is missing, expired, or tampered with
        401 Unauthorized — if the user ID in the token doesn't exist in DB
        403 Forbidden    — if the user account has been deactivated

    Returns:
        The User ORM object for the authenticated user
    """

    # Standard 401 exception we'll raise on any token problem
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the JWT using our secret key and algorithm
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Extract the user ID from the "sub" claim
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        # Catches: expired tokens, bad signature, malformed tokens
        raise credentials_exception

    # Fetch the user from the database
    user = db.query(models.User).filter(
        models.User.id == int(user_id)
    ).first()

    if user is None:
        raise credentials_exception

    # Check the account is still active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact support."
        )

    return user


# =============================================================================
# HELPER: get_db (local — used only inside this file)
# =============================================================================
def _get_db():
    """Local session generator for use inside oauth2.py only."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# DEPENDENCY: get_current_user
# =============================================================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(_get_db)
) -> models.User:
    """
    FastAPI dependency that extracts and validates the authenticated user
    from the Bearer token in the Authorization header.

    Usage in any protected route:
        current_user: models.User = Depends(get_current_user)

    FastAPI automatically:
        1. Extracts the token from the Authorization header
        2. Passes it to this function
        3. Injects the returned User into the route handler
    """
    return verify_access_token(token, db)


# =============================================================================
# DEPENDENCY: get_current_admin
# =============================================================================
def get_current_admin(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Extends get_current_user — additionally requires is_admin == True.
    Use this on routes that only admins should access.

    Usage:
        admin: models.User = Depends(get_current_admin)

    Raises:
        403 Forbidden — if the authenticated user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required to access this resource"
        )
    return current_user