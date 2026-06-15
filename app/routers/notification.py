# app/routers/notification.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   Lets users view and manage their activity notifications.
#
# ENDPOINTS:
#   GET /notifications              → list my notifications  (auth required)
#   PUT /notifications/{id}/read    → mark one as read        (auth required)
#   PUT /notifications/read-all     → mark all as read        (auth required)
#
# WHERE NOTIFICATIONS COME FROM:
#   - follow.py    → creates a "follow" notification when someone follows you
#   - like.py      → creates a "like" notification when someone likes your post
#   - comment.py   → creates a "comment" notification when someone comments
#
#   (The like.py and comment.py routers need a small addition —
#    see the notes at the bottom of this file.)
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from app import models, schemas
from app.dependencies.deps import get_db, get_current_user

router = APIRouter(tags=["Notifications"])


# =============================================================================
# GET /notifications — List my notifications
# =============================================================================
@router.get(
    "/notifications",
    response_model=List[schemas.NotificationResponse],
    summary="Get my notifications"
)
def get_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    limit: int = 50
):
    """
    Returns the authenticated user's notifications,
    most recent first.

    Each notification includes the "actor" (who triggered it)
    and the type: "like", "comment", or "follow".
    """
    notifications = (
        db.query(models.Notification)
        .options(joinedload(models.Notification.actor))
        .filter(models.Notification.recipient_id == current_user.id)
        .order_by(models.Notification.created_at.desc())
        .limit(limit)
        .all()
    )

    return notifications


# =============================================================================
# GET /notifications/unread-count — Count unread notifications
# =============================================================================
@router.get(
    "/notifications/unread-count",
    summary="Get count of unread notifications"
)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns how many of the authenticated user's notifications
    are unread. Useful for showing a badge number in the frontend,
    e.g. a red "3" on the bell icon.
    """
    count = db.query(models.Notification).filter(
        models.Notification.recipient_id == current_user.id,
        models.Notification.is_read == False
    ).count()

    return {"unread_count": count}


# =============================================================================
# PUT /notifications/{notification_id}/read — Mark one as read
# =============================================================================
@router.put(
    "/notifications/{notification_id}/read",
    response_model=schemas.NotificationMarkReadResponse,
    summary="Mark a notification as read"
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Marks a single notification as read.

    Returns:
        200 → marked as read
        404 → notification not found, or it does not belong to you
    """
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.recipient_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with id {notification_id} not found"
        )

    notification.is_read = True
    db.commit()

    return {
        "message": "Notification marked as read",
        "id":      notification.id,
        "is_read": notification.is_read
    }


# =============================================================================
# PUT /notifications/read-all — Mark ALL as read
# =============================================================================
@router.put(
    "/notifications/read-all",
    summary="Mark all notifications as read"
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Marks every unread notification belonging to the
    authenticated user as read. Useful for a
    "Mark all as read" button in the notifications dropdown.
    """
    updated = (
        db.query(models.Notification)
        .filter(
            models.Notification.recipient_id == current_user.id,
            models.Notification.is_read == False
        )
        .update({"is_read": True})
    )
    db.commit()

    return {
        "message":      "All notifications marked as read",
        "updated_count": updated
    }


# =============================================================================
# NOTES — wiring notifications into like.py and comment.py
# =============================================================================
#
# To make "X liked your post" and "X commented on your post" notifications
# actually appear, add this small snippet at the end of the like_post()
# function in app/routers/like.py (after the like is successfully created):
#
#     if post.owner_id != current_user.id:   # don't notify yourself
#         notification = models.Notification(
#             recipient_id=post.owner_id,
#             actor_id=current_user.id,
#             type="like",
#             post_id=post_id
#         )
#         db.add(notification)
#         db.commit()
#
# And similarly in create_comment() in app/routers/comment.py:
#
#     if post.owner_id != current_user.id:
#         notification = models.Notification(
#             recipient_id=post.owner_id,
#             actor_id=current_user.id,
#             type="comment",
#             post_id=post_id
#         )
#         db.add(notification)
#         db.commit()
#
# The follow.py router (previous file) already includes this pattern
# for "follow" notifications — use it as a reference.
# =============================================================================