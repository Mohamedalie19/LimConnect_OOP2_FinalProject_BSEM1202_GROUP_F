# app/routers/follow.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   Handles follower / following relationships between users.
#
# ENDPOINTS:
#   POST   /users/{user_id}/follow      → follow a user        (auth required)
#   DELETE /users/{user_id}/follow      → unfollow a user       (auth required)
#   GET    /users/{user_id}/followers   → list of followers     (public)
#   GET    /users/{user_id}/following   → list of users followed (public)
#
# NOTES:
#   - A user cannot follow themselves (400 error).
#   - Following the same user twice returns 409 Conflict
#     (enforced by the UniqueConstraint on the follows table).
#   - When a follow happens, a Notification row is also created
#     so the followed user sees "X started following you".
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from app import models, schemas
from app.dependencies.deps import get_db, get_current_user

router = APIRouter(tags=["Follows"])


# =============================================================================
# POST /users/{user_id}/follow — Follow a user
# =============================================================================
@router.post(
    "/users/{user_id}/follow",
    response_model=schemas.FollowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Follow a user"
)
def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Makes the authenticated user follow the user with the given id.

    Returns:
        201 → followed successfully
        400 → cannot follow yourself
        404 → user to follow does not exist
        409 → you already follow this user
    """
    # Cannot follow yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself"
        )

    # Check the target user exists
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

    new_follow = models.Follow(
        follower_id=current_user.id,
        followed_id=user_id
    )

    try:
        db.add(new_follow)
        db.commit()
    except IntegrityError:
        # UniqueConstraint(follower_id, followed_id) was violated
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already following this user"
        )

    # Create a notification for the followed user
    notification = models.Notification(
        recipient_id=user_id,
        actor_id=current_user.id,
        type="follow"
    )
    db.add(notification)
    db.commit()

    followers_count = db.query(models.Follow).filter(
        models.Follow.followed_id == user_id
    ).count()

    return {
        "message":         f"You are now following {target_user.username}",
        "followed_id":     user_id,
        "followers_count": followers_count
    }


# =============================================================================
# DELETE /users/{user_id}/follow — Unfollow a user
# =============================================================================
@router.delete(
    "/users/{user_id}/follow",
    response_model=schemas.FollowResponse,
    summary="Unfollow a user"
)
def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Removes the authenticated user's follow relationship
    with the user with the given id.

    Returns:
        200 → unfollowed successfully
        404 → user not found, or you do not follow this user
    """
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

    follow = db.query(models.Follow).filter(
        models.Follow.follower_id == current_user.id,
        models.Follow.followed_id == user_id
    ).first()

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You do not follow this user"
        )

    db.delete(follow)
    db.commit()

    followers_count = db.query(models.Follow).filter(
        models.Follow.followed_id == user_id
    ).count()

    return {
        "message":         f"You have unfollowed {target_user.username}",
        "followed_id":     user_id,
        "followers_count": followers_count
    }


# =============================================================================
# GET /users/{user_id}/followers — List a user's followers
# =============================================================================
@router.get(
    "/users/{user_id}/followers",
    response_model=List[schemas.FollowerItem],
    summary="Get a user's followers"
)
def get_followers(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns the list of users who follow the given user.
    Public — no authentication required.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

    # Join Follow -> User to get the follower's user records
    followers = (
        db.query(models.User)
        .join(models.Follow, models.Follow.follower_id == models.User.id)
        .filter(models.Follow.followed_id == user_id)
        .all()
    )

    return followers


# =============================================================================
# GET /users/{user_id}/following — List users a user follows
# =============================================================================
@router.get(
    "/users/{user_id}/following",
    response_model=List[schemas.FollowerItem],
    summary="Get users that this user follows"
)
def get_following(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns the list of users that the given user follows.
    Public — no authentication required.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

    # Join Follow -> User to get the followed user's records
    following = (
        db.query(models.User)
        .join(models.Follow, models.Follow.followed_id == models.User.id)
        .filter(models.Follow.follower_id == user_id)
        .all()
    )

    return following