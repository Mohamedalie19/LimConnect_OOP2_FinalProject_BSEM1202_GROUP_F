# app/dependencies/deps.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   Central module for all FastAPI dependency injection providers.
#   Any file that needs a DB session or the current user imports from here.
#
# DEPENDENCY INJECTION EXPLAINED:
#   Instead of creating a DB session inside every route function,
#   we declare get_db as a dependency. FastAPI calls it automatically
#   before the route runs, passes the session in, and closes it after.
#
#   This means route handlers stay clean:
#     def get_posts(db: Session = Depends(get_db)):
#         return db.query(Post).all()
#
# NEW IN THIS VERSION:
#   get_current_user_optional() — like get_current_user(), but returns
#   None instead of raising 401 when no token is provided.
#   Used by GET /users/{id} so it can show "is_following" only when
#   someone is logged in, while still working for anonymous visitors.
# ─────────────────────────────────────────────────────────────────────────────

from typing import Generator, Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session
from jose import JWTError

from app.database import SessionLocal
from app import models, oauth2
from app.oauth2 import oauth2_scheme


# =============================================================================
# DATABASE SESSION DEPENDENCY
# =============================================================================
def get_db() -> Generator:
    """
    Yields one SQLAlchemy database session per HTTP request.
    The session is automatically closed after the request completes,
    even if an exception was raised (guaranteed by the finally block).

    Usage in any route:
        db: Session = Depends(get_db)

    How it works:
        FastAPI sees Depends(get_db), calls the generator,
        yields the session into the route, then resumes after
        yield to close the session once the response is sent.

    Example:
        @router.get("/posts")
        def list_posts(db: Session = Depends(get_db)):
            return db.query(models.Post).all()
    """
    db = SessionLocal()
    try:
        yield db          # ← FastAPI injects this into the route
    finally:
        db.close()        # ← always runs, even after exceptions


# =============================================================================
# CURRENT USER DEPENDENCY
# =============================================================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db)
) -> models.User:
    """
    Extracts and validates the JWT Bearer token from the request header.
    Returns the authenticated User ORM object.

    Usage in any protected route:
        current_user: models.User = Depends(get_current_user)

    Raises:
        401 Unauthorized — invalid, expired, or missing token
        403 Forbidden    — account deactivated
    """
    return oauth2.verify_access_token(token, db)


# =============================================================================
# OPTIONAL CURRENT USER DEPENDENCY  ── NEW ────────────────────────────────────
# =============================================================================
def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """
    Like get_current_user(), but does NOT raise an error if there is
    no token, an invalid token, or an expired token.

    Returns:
        models.User → if a valid Bearer token was provided
        None        → if no token, or the token is invalid/expired

    Why this exists:
        Some endpoints (like GET /users/{id}) should work for
        EVERYONE — logged in or not — but show extra information
        (like "is_following") only when the visitor is logged in.

    Usage:
        current_user: Optional[models.User] = Depends(get_current_user_optional)
        if current_user:
            ... show personalised data ...
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]

    try:
        return oauth2.verify_access_token(token, db)
    except Exception:
        # Invalid or expired token — treat as anonymous instead of erroring
        return None


# =============================================================================
# ADMIN USER DEPENDENCY
# =============================================================================
def get_current_admin(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Requires the authenticated user to have is_admin == True.
    Used on admin-only routes such as deleting any user's content.

    Usage:
        admin: models.User = Depends(get_current_admin)

    Raises:
        403 Forbidden — if user is not an admin
    """
    from fastapi import HTTPException, status
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required"
        )
    return current_user
