# app/routers/comment.py
# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS:
#   POST   /posts/{post_id}/comments   → add a comment   (auth required)
#   GET    /posts/{post_id}/comments   → get comments    (public)
#   PUT    /comments/{id}              → edit comment    (author only)
#   DELETE /comments/{id}              → delete comment  (author or admin)
#
# NEW IN THIS VERSION:
#   - create_comment() now creates a Notification for the post owner
#     ("X commented on your post"), unless you comment on your own post.
# ─────────────────────────────────────────────────────────────────────────────

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app import models
from app.schemas import CommentCreate, CommentUpdate, CommentResponse
from app.dependencies.deps import get_db, get_current_user

router = APIRouter(tags=["Comments"])


# =============================================================================
# POST /posts/{post_id}/comments — Add a comment to a post
# =============================================================================
@router.post(
    "/posts/{post_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentResponse,
    summary="Add a comment to a post"
)
def create_comment(
    post_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Adds a comment to the specified post.
    Set parent_id to reply to an existing comment.

    Example request body:
        { "content": "Great post!", "parent_id": null }

    Reply example:
        { "content": "I agree!", "parent_id": 5 }
    """
    # Confirm post exists
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Post with id {post_id} not found")

    # If replying, confirm the parent comment exists on this post
    if payload.parent_id:
        parent = db.query(models.Comment).filter(
            models.Comment.id      == payload.parent_id,
            models.Comment.post_id == post_id
        ).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found on this post"
            )

    comment = models.Comment(
        content   = payload.content,
        post_id   = post_id,
        author_id = current_user.id,
        parent_id = payload.parent_id
    )
    db.add(comment)
    db.commit()

    # ── NEW: create a notification for the post owner ─────────────────────
    # Don't notify yourself if you comment on your own post
    if post.owner_id != current_user.id:
        notification = models.Notification(
            recipient_id=post.owner_id,
            actor_id=current_user.id,
            type="comment",
            post_id=post_id
        )
        db.add(notification)
        db.commit()

    db.refresh(comment)
    return comment


# =============================================================================
# GET /posts/{post_id}/comments — Get all comments on a post
# =============================================================================
@router.get(
    "/posts/{post_id}/comments",
    response_model=List[CommentResponse],
    summary="Get all comments on a post"
)
def get_comments(
    post_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns all top-level comments on a post, ordered oldest first.
    Public — no authentication required.
    """
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Post with id {post_id} not found")

    comments = (
        db.query(models.Comment)
        .options(joinedload(models.Comment.author))
        .filter(
            models.Comment.post_id   == post_id,
            models.Comment.parent_id == None    # top-level only
        )
        .order_by(models.Comment.created_at.asc())
        .all()
    )

    return comments


# =============================================================================
# PUT /comments/{id} — Edit a comment (author only)
# =============================================================================
@router.put(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    summary="Edit a comment"
)
def update_comment(
    comment_id: int,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Updates the content of a comment.
    Only the comment author can edit it.
    """
    comment = db.query(models.Comment).filter(
        models.Comment.id == comment_id
    ).first()

    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Comment with id {comment_id} not found")

    if comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You are not authorized to edit this comment")

    comment.content = payload.content
    db.commit()
    db.refresh(comment)

    return comment


# =============================================================================
# DELETE /comments/{id} — Delete a comment (author or admin)
# =============================================================================
@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment"
)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Deletes a comment. Author or admin only.
    Returns 204 No Content on success.
    """
    comment = db.query(models.Comment).filter(
        models.Comment.id == comment_id
    ).first()

    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Comment with id {comment_id} not found")

    if comment.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You are not authorized to delete this comment")

    db.delete(comment)
    db.commit()