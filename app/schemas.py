# app/schemas.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   Pydantic schemas define the shape of data coming IN (requests)
#   and going OUT (responses) for every API endpoint.
#
# WHY SEPARATE FROM MODELS:
#   SQLAlchemy models define the database structure.
#   Pydantic schemas define the API contract.
#   Keeping them separate means you can control exactly what
#   data gets exposed — for example, the password hash is in the
#   User model but is NEVER included in any UserResponse schema.
#
# NAMING CONVENTION:
#   <Entity>Create   → fields required to create a new record
#   <Entity>Update   → fields allowed to update (all optional)
#   <Entity>Response → fields returned in API responses
#
# NEW IN THIS VERSION:
#   - UserResponse now includes avatar_url and cover_url
#   - UserProfileResponse → richer profile view with follower/following counts
#   - FollowResponse      → returned when following/unfollowing
#   - NotificationResponse → returned for the notifications feed
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from pydantic import EmailStr
from datetime import datetime
from typing import Optional, List


# =============================================================================
# USER SCHEMAS
# =============================================================================

class UserCreate(BaseModel):
    """
    Request body for POST /users/register
    All fields are required. Email is validated as a proper email address.
    """
    username:  str      = Field(..., min_length=3, max_length=50,
                                example="john_doe")
    email:     str = Field(..., example="john@example.com")
    password:  str      = Field(..., min_length=6, max_length=100,
                                example="secret123")
    full_name: Optional[str] = Field(None, max_length=100,
                                     example="John Doe")


class UserUpdate(BaseModel):
    """
    Request body for PUT /users/me
    All fields are optional — client sends only what they want to change.
    """
    full_name: Optional[str] = Field(None, max_length=100)
    bio:       Optional[str] = None


class UserResponse(BaseModel):
    """
    Returned in API responses wherever a user object is needed.
    NOTE: password is intentionally excluded — never expose hashes.

    NEW: avatar_url and cover_url let the frontend display
    a profile picture and cover banner.
    """
    id:         int
    username:   str
    email:      str
    full_name:  Optional[str]
    bio:        Optional[str]
    avatar_url: Optional[str] = None     # NEW
    cover_url:  Optional[str] = None     # NEW
    is_active:  bool
    is_admin:   bool
    created_at: datetime

    class Config:
        from_attributes = True   # allows ORM model → Pydantic conversion


class UserPublic(BaseModel):
    """
    Minimal user info embedded inside post/comment responses.
    Hides email for privacy on public-facing endpoints.

    NEW: avatar_url so post/comment cards can show profile pictures.
    """
    id:         int
    username:   str
    avatar_url: Optional[str] = None     # NEW

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    """
    NEW SCHEMA.
    Richer profile view returned by GET /users/{user_id}.
    Includes follower/following counts and whether the
    currently logged-in user follows this profile.
    """
    id:               int
    username:         str
    full_name:        Optional[str]
    bio:              Optional[str]
    avatar_url:       Optional[str] = None
    cover_url:        Optional[str] = None
    is_admin:         bool
    created_at:       datetime

    followers_count:  int = 0
    following_count:  int = 0
    posts_count:      int = 0

    # True if the CURRENTLY LOGGED-IN user follows this profile.
    # False if not logged in or not following.
    is_following:     bool = False

    class Config:
        from_attributes = True


# =============================================================================
# TOKEN SCHEMAS
# =============================================================================

class Token(BaseModel):
    """Returned by POST /auth/login on successful authentication."""
    access_token: str
    token_type:   str = "bearer"
    user_id:      int
    username:     str


class TokenData(BaseModel):
    """Decoded payload extracted from a JWT token during verification."""
    id: Optional[int] = None


# =============================================================================
# POST SCHEMAS
# =============================================================================

class PostCreate(BaseModel):
    """Request body for POST /posts/"""
    title:        str  = Field(..., min_length=3, max_length=255,
                               example="My First Post")
    content:      str  = Field(..., min_length=10,
                               example="This is the content of my post.")
    image_url:    Optional[str]  = Field(None, max_length=500)
    is_published: Optional[bool] = Field(True)


class PostUpdate(BaseModel):
    """
    Request body for PUT /posts/{id}
    All fields optional — supports partial updates.
    """
    title:        Optional[str]  = Field(None, min_length=3, max_length=255)
    content:      Optional[str]  = Field(None, min_length=10)
    image_url:    Optional[str]  = Field(None, max_length=500)
    is_published: Optional[bool] = None


class PostResponse(BaseModel):
    """Full post object returned by create, get, and update endpoints."""
    id:            int
    title:         str
    content:       str
    image_url:     Optional[str]
    is_published:  bool
    owner_id:      int
    owner:         UserPublic
    like_count:    int = 0
    comment_count: int = 0
    created_at:    datetime
    updated_at:    datetime

    class Config:
        from_attributes = True


# =============================================================================
# COMMENT SCHEMAS
# =============================================================================

class CommentCreate(BaseModel):
    """Request body for POST /posts/{id}/comments"""
    content:   str            = Field(..., min_length=1,
                                      example="Great post!")
    parent_id: Optional[int]  = Field(None,
                                      description="Set to reply to another comment")


class CommentUpdate(BaseModel):
    """Request body for PUT /comments/{id}"""
    content: str = Field(..., min_length=1)


class CommentResponse(BaseModel):
    """Comment object returned in API responses."""
    id:         int
    content:    str
    post_id:    int
    author_id:  int
    parent_id:  Optional[int]
    author:     UserPublic
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# LIKE SCHEMAS
# =============================================================================

class LikeResponse(BaseModel):
    """Returned after liking or unliking a post."""
    message:    str
    post_id:    int
    like_count: int


# =============================================================================
# FOLLOW SCHEMAS  ── NEW ───────────────────────────────────────────────────────
# =============================================================================

class FollowResponse(BaseModel):
    """
    Returned by POST /users/{id}/follow and DELETE /users/{id}/follow.

    message         → human-readable confirmation, e.g. "You are now following jalloh"
    followed_id     → the id of the user that was followed/unfollowed
    followers_count → updated follower count for that user
    """
    message:         str
    followed_id:     int
    followers_count: int


class FollowerItem(BaseModel):
    """
    NEW SCHEMA.
    One row in a followers/following list — a lightweight user summary.
    Used by GET /users/{id}/followers and GET /users/{id}/following.
    """
    id:         int
    username:   str
    full_name:  Optional[str]
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# NOTIFICATION SCHEMAS  ── NEW ─────────────────────────────────────────────────
# =============================================================================

class NotificationResponse(BaseModel):
    """
    Returned by GET /notifications.

    type    → "like", "comment", or "follow"
    actor   → the user who triggered the notification
    post_id → the related post (null for "follow" notifications)
    is_read → whether the recipient has seen this yet
    """
    id:         int
    type:       str
    actor:      UserPublic
    post_id:    Optional[int] = None
    is_read:    bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationMarkReadResponse(BaseModel):
    """Returned by PUT /notifications/{id}/read"""
    message: str
    id:      int
    is_read: bool


# =============================================================================
# AVATAR / COVER UPLOAD SCHEMAS  ── NEW ────────────────────────────────────────
# =============================================================================

class ImageUploadResponse(BaseModel):
    """
    Returned by PUT /users/me/avatar and PUT /users/me/cover.

    url → the path where the uploaded image can be accessed,
          e.g. "/uploads/avatar_3_a1b2c3.png"
    """
    message: str
    url:     str