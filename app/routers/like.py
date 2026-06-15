# app/routers/like.py
# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS:
#   POST   /posts/{id}/like    → like a post      (auth required)
#   DELETE /posts/{id}/like    → unlike a post    (auth required)
#   GET    /posts/{id}/likes   → get like count   (public)
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import models
from app.dependencies.deps import get_db, get_current_user

router = APIRouter(tags=["Likes"])


# =============================================================================
# POST /posts/{post_id}/like — Like a post
# =============================================================================
@router.post(
    "/posts/{post_id}/like",
    status_code=status.HTTP_201_CREATED,
    summary="Like a post"
)
def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Likes the specified post on behalf of the authenticated user.

    Returns:
        201 → like added successfully
        404 → post not found
        409 → you have already liked this post
    """
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Post with id {post_id} not found")

    new_like = models.Like(post_id=post_id, user_id=current_user.id)

    try:
        db.add(new_like)
        db.commit()
    except IntegrityError:
        # The UniqueConstraint on (post_id, user_id) was violated
        # This means the user already liked this post
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already liked this post"
        )

    like_count = db.query(models.Like).filter(
        models.Like.post_id == post_id
    ).count()

    return {
        "message":    "Post liked successfully",
        "post_id":    post_id,
        "like_count": like_count
    }


# =============================================================================
# DELETE /posts/{post_id}/like — Unlike a post
# =============================================================================
@router.delete(
    "/posts/{post_id}/like",
    summary="Unlike a post"
)
def unlike_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Removes the authenticated user's like from the specified post.

    Returns:
        200 → like removed successfully
        404 → post not found, or you have not liked this post
    """
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Post with id {post_id} not found")

    like = db.query(models.Like).filter(
        models.Like.post_id == post_id,
        models.Like.user_id == current_user.id
    ).first()

    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not liked this post"
        )

    db.delete(like)
    db.commit()

    like_count = db.query(models.Like).filter(
        models.Like.post_id == post_id
    ).count()

    return {
        "message":    "Like removed successfully",
        "post_id":    post_id,
        "like_count": like_count
    }


# =============================================================================
# GET /posts/{post_id}/likes — Get like count for a post
# =============================================================================
@router.get(
    "/posts/{post_id}/likes",
    summary="Get like count for a post"
)
def get_likes(
    post_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns the total number of likes on a post.
    Public — no authentication required.
    """
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Post with id {post_id} not found")

    count = db.query(models.Like).filter(
        models.Like.post_id == post_id
    ).count()

    return {"post_id": post_id, "like_count": count}

    # ═══════════════════════════════════════════════════════════════════════════
# ADDITION FOR: app/routers/like.py
# ═══════════════════════════════════════════════════════════════════════════
#
# WHERE: Inside the like_post() function, AFTER this existing block:
#
#     try:
#         db.add(new_like)
#         db.commit()
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="You have already liked this post"
#         )
#
# ADD THESE LINES RIGHT AFTER THAT block (and BEFORE the
# "like_count = db.query(...)" line):

    # ── NEW: create a notification for the post owner ─────────────────────
    # Don't notify yourself if you like your own post
    if post.owner_id != current_user.id:
        notification = models.Notification(
            recipient_id=post.owner_id,
            actor_id=current_user.id,
            type="like",
            post_id=post_id
        )
        db.add(notification)
        db.commit()

