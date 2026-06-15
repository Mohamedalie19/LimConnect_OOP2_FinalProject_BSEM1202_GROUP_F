# app/routers/post.py
# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS:
#   POST   /posts/        → create post       (auth required)
#   GET    /posts/        → get all posts     (public, paginated)
#   GET    /posts/{id}    → get single post   (public)
#   PUT    /posts/{id}    → update post       (owner only)
#   DELETE /posts/{id}    → delete post       (owner or admin)
# ─────────────────────────────────────────────────────────────────────────────

import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app import models
from app.schemas import PostCreate, PostUpdate, PostResponse
from app.dependencies.deps import get_db, get_current_user

router = APIRouter(
    prefix="/posts",
    tags=["Posts"]
)


# ── Helper: fetch post or raise 404 ──────────────────────────────────────────
def get_post_or_404(post_id: int, db: Session) -> models.Post:
    post = (
        db.query(models.Post)
        .options(joinedload(models.Post.owner))
        .filter(models.Post.id == post_id)
        .first()
    )
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )
    return post


# =============================================================================
# POST /posts/ — Create a new post
# =============================================================================
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=PostResponse,
    summary="Create a new post"
)
def create_post(
    title: str = Form(...),
    content: str = Form(...),
    image_url: Optional[str] = Form(None),
    is_published: bool = Form(True),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Creates a new post owned by the authenticated user.

    Example request body:
        {
            "title": "My First Post",
            "content": "Hello, Sierra Leone! This is my first post.",
            "is_published": true
        }
    """
    saved_image_url = image_url or None

    if image_file and image_file.filename:
        uploads_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{image_file.filename}"
        save_path = uploads_dir / safe_name
        with save_path.open("wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        saved_image_url = f"/uploads/{safe_name}"

    new_post = models.Post(
        title=title,
        content=content,
        image_url=saved_image_url,
        is_published=is_published,
        owner_id=current_user.id
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    new_post.like_count    = 0
    new_post.comment_count = 0

    return new_post


# =============================================================================
# GET /posts/ — Get all published posts (paginated + searchable)
# =============================================================================
@router.get(
    "/",
    response_model=List[PostResponse],
    summary="Get all published posts"
)
def get_all_posts(
    db:     Session = Depends(get_db),
    limit:  int     = Query(default=10, ge=1, le=100),
    skip:   int     = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None,
                                  description="Filter by keyword in title")
):
    """
    Returns paginated list of all published posts.

    Query parameters:
        limit  → posts per page (default 10, max 100)
        skip   → offset for pagination
        search → keyword filter on post title (case-insensitive)

    Examples:
        GET /posts/
        GET /posts/?limit=5&skip=10
        GET /posts/?search=fastapi
    """
    query = (
        db.query(models.Post)
        .options(joinedload(models.Post.owner))
        .filter(models.Post.is_published == True)
    )

    if search:
        query = query.filter(models.Post.title.ilike(f"%{search}%"))

    posts = (
        query
        .order_by(models.Post.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    for post in posts:
        post.like_count    = len(post.likes)
        post.comment_count = len(post.comments)

    return posts


# =============================================================================
# GET /posts/{id} — Get a single post
# =============================================================================
@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Get a single post by ID"
)
def get_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns full details of a single post including owner and counts.
    Public — no authentication required.
    Returns 404 if the post does not exist.
    """
    post = get_post_or_404(post_id, db)
    post.like_count    = len(post.likes)
    post.comment_count = len(post.comments)
    return post


# =============================================================================
# PUT /posts/{id} — Update a post (owner only)
# =============================================================================
@router.put(
    "/{post_id}",
    response_model=PostResponse,
    summary="Update a post"
)
def update_post(
    post_id: int,
    payload: PostUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Updates an existing post. Only the post owner can update it.
    Supports partial updates — only send the fields you want to change.

    Errors:
        404 → post not found
        403 → you are not the owner of this post
        400 → no fields provided to update
    """
    post = get_post_or_404(post_id, db)

    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this post"
        )

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update"
        )

    for field, value in update_data.items():
        setattr(post, field, value)

    db.commit()
    db.refresh(post)

    post.like_count    = len(post.likes)
    post.comment_count = len(post.comments)

    return post


# =============================================================================
# DELETE /posts/{id} — Delete a post (owner or admin)
# =============================================================================
@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post"
)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Permanently deletes a post and all its comments and likes (CASCADE).
    Only the post owner or an admin can delete a post.
    Returns 204 No Content on success (no response body).

    Errors:
        404 → post not found
        403 → not the owner or admin
    """
    post = get_post_or_404(post_id, db)

    if post.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this post"
        )

    db.delete(post)
    db.commit()