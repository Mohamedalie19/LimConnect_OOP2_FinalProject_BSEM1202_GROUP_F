# app/routers/auth.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   Handles user login and JWT token issuance.
#   This is the only route that doesn't require an existing token.
#
# ENDPOINT:
#   POST /auth/login
#     - Accepts: email + password (as OAuth2 form fields)
#     - Returns: JWT access token + user info
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, oauth2
from app.schemas import Token
from app.utils import verify_password
from app.dependencies.deps import get_db

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive a JWT access token"
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticates a user and returns a JWT Bearer token.

    The client must send credentials as form-data (not JSON):
        username → the user's email address
        password → the user's plain-text password

    Example request (Postman → Body → form-data):
        username: john@example.com
        password: secret123

    Example response:
        {
            "access_token": "eyJhbGci...",
            "token_type": "bearer",
            "user_id": 1,
            "username": "john_doe"
        }

    Error responses:
        403 → invalid email or password
        403 → account is deactivated
    """
    # Find user by email
    # NOTE: OAuth2PasswordRequestForm uses "username" field for the email
    user = db.query(models.User).filter(
        models.User.email == form_data.username
    ).first()

    # SECURITY: use the same generic error for both wrong email AND wrong
    # password — this prevents user enumeration attacks where an attacker
    # can tell whether an email address is registered
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid credentials"
        )

    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support."
        )

    # Create and return the JWT token
    access_token = oauth2.create_access_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type":   "bearer",
        "user_id":      user.id,
        "username":     user.username
    }