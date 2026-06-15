# app/routers/user.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   User registration and profile management routes.
#
# ENDPOINTS:
#   POST /users/register       → create a new account (public)
#   GET  /users/me              → get your own profile (auth required)
#   PUT  /users/me              → update your own profile (auth required)
#   GET  /users/{id}             → view any user's profile + follow info (public)
#   PUT  /users/me/avatar       → upload/replace profile picture (auth) [NEW]
#   PUT  /users/me/cover        → upload/replace cover photo (auth)     [NEW]
#
# NEW IN THIS VERSION:
#   - Image upload endpoints save files to the /uploads folder and
#     store the URL path in the user's avatar_url / cover_url column.
#   - GET /users/{id} now returns UserProfileResponse, which includes
#     followers_count, following_count, posts_count, and is_following.
# ─────────────────────────────────────────────────────────────────────────────

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from app import models
from app.schemas import (
    UserCreate, UserUpdate, UserResponse,
    UserProfileResponse, ImageUploadResponse
)
from app.utils import hash_password
from app.dependencies.deps import get_db, get_current_user, get_current_user_optional

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


# ── Upload configuration ───────────────────────────────────────────────────
# Folder where uploaded images are physically stored.
# app/main.py mounts this folder at the "/uploads" URL path,
# so a file saved here at "avatar_3_abc123.png" becomes
# accessible at "http://127.0.0.1:8000/uploads/avatar_3_abc123.png"
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Only allow common image formats
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Limit file size to 5 MB to prevent abuse
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB in bytes


def _save_upload(file: UploadFile, prefix: str, user_id: int) -> str:
    """
    Shared helper: validates and saves an uploaded image file.

    Returns the URL path (e.g. "/uploads/avatar_3_a1b2c3d4.png")
    that should be stored in the database and returned to the client.

    Raises:
        400 → file type not allowed, or file too large
    """
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. "
                   f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content (also lets us check size)
    contents = file.file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5 MB."
        )

    # Build a unique filename so two users' uploads never collide
    # e.g. "avatar_3_9f8e7d6c.png"
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{prefix}_{user_id}_{unique_id}{ext}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        f.write(contents)

    # This is the URL path the frontend will use as <img src="...">
    return f"/uploads/{filename}"


# =============================================================================
# POST /users/register — Create a new user account
# =============================================================================
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    summary="Register a new user account"
)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Registers a new user account.

    Validates that the email and username are not already taken.
    Hashes the password with bcrypt before saving.
    Returns the created user (without password).

    Example request body:
        {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "secret123",
            "full_name": "John Doe"
        }
    """
    # Check email is not already registered
    existing_email = db.query(models.User).filter(
        models.User.email == payload.email
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists"
        )

    # Check username is not already taken
    existing_username = db.query(models.User).filter(
        models.User.username == payload.username
    ).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken"
        )

    # Hash the password — NEVER store plain-text passwords
    hashed = hash_password(payload.password)

    new_user = models.User(
        username  = payload.username,
        email     = payload.email,
        password  = hashed,
        full_name = payload.full_name
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# =============================================================================
# GET /users/me — Get authenticated user's own profile
# =============================================================================
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get your own profile"
)
def get_my_profile(
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns the full profile of the currently authenticated user.
    Requires a valid JWT token in the Authorization header.

    Example request:
        GET /users/me
        Authorization: Bearer eyJhbGci...
    """
    return current_user


# =============================================================================
# PUT /users/me — Update authenticated user's profile
# =============================================================================
@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update your own profile"
)
def update_my_profile(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Updates the authenticated user's profile.
    Only full_name and bio can be updated (email/username are immutable).

    Supports partial updates — only send the fields you want to change:
        { "bio": "Backend developer from Sierra Leone" }
    """
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update"
        )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return current_user


# =============================================================================
# PUT /users/me/avatar — Upload/replace profile picture  ── NEW ──────────────
# =============================================================================
@router.put(
    "/me/avatar",
    response_model=ImageUploadResponse,
    summary="Upload or replace your profile picture"
)
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Uploads a new profile picture for the authenticated user.

    Accepts: multipart/form-data with a "file" field.
    Allowed types: .png, .jpg, .jpeg, .gif, .webp (max 5 MB)

    The image is saved to the /uploads folder and the user's
    avatar_url is updated to point to it.

    Example (curl):
        curl -X PUT http://127.0.0.1:8000/users/me/avatar \\
             -H "Authorization: Bearer <token>" \\
             -F "file=@profile.png"
    """
    url = _save_upload(file, prefix="avatar", user_id=current_user.id)

    current_user.avatar_url = url
    db.commit()

    return {"message": "Profile picture updated successfully", "url": url}


# =============================================================================
# PUT /users/me/cover — Upload/replace cover photo  ── NEW ───────────────────
# =============================================================================
@router.put(
    "/me/cover",
    response_model=ImageUploadResponse,
    summary="Upload or replace your cover photo"
)
def upload_cover(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Uploads a new cover photo (banner image) for the authenticated user.

    Accepts: multipart/form-data with a "file" field.
    Allowed types: .png, .jpg, .jpeg, .gif, .webp (max 5 MB)

    The image is saved to the /uploads folder and the user's
    cover_url is updated to point to it.

    Example (curl):
        curl -X PUT http://127.0.0.1:8000/users/me/cover \\
             -H "Authorization: Bearer <token>" \\
             -F "file=@banner.png"
    """
    url = _save_upload(file, prefix="cover", user_id=current_user.id)

    current_user.cover_url = url
    db.commit()

    return {"message": "Cover photo updated successfully", "url": url}


# =============================================================================
# GET /users/{id} — Get any user's profile (with follow info)
# =============================================================================
@router.get(
    "/{user_id}",
    response_model=UserProfileResponse,
    summary="Get a user's public profile by ID"
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional)
):
    """
    Returns the public profile of any user by their ID, including:
      - followers_count
      - following_count
      - posts_count
      - is_following → True if the CURRENTLY LOGGED-IN visitor
                        follows this profile (False if not logged in)

    Does not require authentication — but if a valid token IS
    provided, is_following will be personalised for that visitor.

    Example request:
        GET /users/3
        Authorization: Bearer eyJhbGci...   (optional)
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

    followers_count = db.query(models.Follow).filter(
        models.Follow.followed_id == user_id
    ).count()

    following_count = db.query(models.Follow).filter(
        models.Follow.follower_id == user_id
    ).count()

    posts_count = db.query(models.Post).filter(
        models.Post.owner_id == user_id
    ).count()

    is_following = False
    if current_user:
        is_following = db.query(models.Follow).filter(
            models.Follow.follower_id == current_user.id,
            models.Follow.followed_id == user_id
        ).first() is not None

    return {
        "id":              user.id,
        "username":        user.username,
        "full_name":       user.full_name,
        "bio":             user.bio,
        "avatar_url":      user.avatar_url,
        "cover_url":       user.cover_url,
        "is_admin":        user.is_admin,
        "created_at":      user.created_at,
        "followers_count": followers_count,
        "following_count": following_count,
        "posts_count":     posts_count,
        "is_following":    is_following,
    }