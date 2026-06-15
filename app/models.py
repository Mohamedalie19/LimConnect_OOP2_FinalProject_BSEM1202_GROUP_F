# app/models.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   Defines all database tables as Python classes using SQLAlchemy ORM.
#   Each class = one table in PostgreSQL.
#   Each Column = one column in that table.
#
# MODELS:
#   User         → stores registered users
#   Post         → stores posts created by users
#   Comment      → stores comments on posts (with reply threading)
#   Like         → stores likes (one per user per post, enforced by DB constraint)
#   Follow       → NEW: stores follower/following relationships between users
#   Notification → NEW: stores activity notifications for users
# ─────────────────────────────────────────────────────────────────────────────
 
from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
 
from app.database import Base
 
 
# =============================================================================
# USER
# =============================================================================
class User(Base):
    """
    Stores all registered user accounts.
 
    Relationships:
      - One user  → many posts          (User.posts)
      - One user  → many comments       (User.comments)
      - One user  → many likes          (User.likes)
      - One user  → many follows made   (User.following)   [NEW]
      - One user  → many follows received (User.followers) [NEW]
      - One user  → many notifications  (User.notifications) [NEW]
    """
    __tablename__ = "users"
 
    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(50),  unique=True, nullable=False, index=True)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    password   = Column(String(255), nullable=False)        # bcrypt hashed
    full_name  = Column(String(100), nullable=True)
    bio        = Column(Text,        nullable=True)
    is_active  = Column(Boolean, default=True,  nullable=False)
    is_admin   = Column(Boolean, default=False, nullable=False)
 
    # ── NEW: profile picture and cover photo ─────────────────────────────
    # Store the URL path to the uploaded image, e.g. "/uploads/avatar_3.png"
    avatar_url = Column(String(500), nullable=True)
    cover_url  = Column(String(500), nullable=True)
 
    # Timestamps — set by PostgreSQL server clock, not Python
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(),
                        onupdate=func.now(), nullable=False)
 
    # Relationships
    posts    = relationship("Post",    back_populates="owner",
                            cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author",
                            cascade="all, delete-orphan")
    likes    = relationship("Like",    back_populates="user",
                            cascade="all, delete-orphan")
 
    # ── NEW: follow relationships ─────────────────────────────────────────
    # "following" = rows where THIS user is the follower (Follow.follower_id == self.id)
    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan"
    )
    # "followers" = rows where THIS user is being followed (Follow.followed_id == self.id)
    followers = relationship(
        "Follow",
        foreign_keys="Follow.followed_id",
        back_populates="followed",
        cascade="all, delete-orphan"
    )
 
    # ── NEW: notifications received by this user ───────────────────────────
    notifications = relationship(
        "Notification",
        foreign_keys="Notification.recipient_id",
        back_populates="recipient",
        cascade="all, delete-orphan"
    )
 
    def __repr__(self):
        return f"<User id={self.id} username={self.username!r}>"
 
 
# =============================================================================
# POST
# =============================================================================
class Post(Base):
    """
    Stores posts authored by users.
 
    Relationships:
      - Many posts  → one user     (Post.owner)
      - One post    → many comments (Post.comments)
      - One post    → many likes    (Post.likes)
    """
    __tablename__ = "posts"
 
    id           = Column(Integer, primary_key=True, index=True)
    title        = Column(String(255), nullable=False)
    content      = Column(Text,        nullable=False)
    image_url    = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=True, nullable=False)
 
    # Foreign key → users.id
    # ondelete="CASCADE" means if the user is deleted,
    # all their posts are automatically deleted too (at DB level)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
 
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(),
                        onupdate=func.now(), nullable=False)
 
    # Relationships
    owner    = relationship("User",    back_populates="posts")
    comments = relationship("Comment", back_populates="post",
                            cascade="all, delete-orphan")
    likes    = relationship("Like",    back_populates="post",
                            cascade="all, delete-orphan")
 
    def __repr__(self):
        return f"<Post id={self.id} title={self.title!r}>"
 
 
# =============================================================================
# COMMENT
# =============================================================================
class Comment(Base):
    """
    Stores comments on posts.
    Supports one level of reply threading via self-referential parent_id.
 
    Relationships:
      - Many comments → one post   (Comment.post)
      - Many comments → one user   (Comment.author)
      - One comment   → many replies (Comment.replies)
    """
    __tablename__ = "comments"
 
    id        = Column(Integer, primary_key=True, index=True)
    content   = Column(Text, nullable=False)
 
    post_id   = Column(Integer, ForeignKey("posts.id",    ondelete="CASCADE"),
                       nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id",    ondelete="CASCADE"),
                       nullable=False, index=True)
 
    # Optional: if set, this comment is a reply to another comment
    parent_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"),
                       nullable=True, index=True)
 
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(),
                        onupdate=func.now(), nullable=False)
 
    # Relationships
    post    = relationship("Post", back_populates="comments")
    author  = relationship("User", back_populates="comments")
    replies = relationship("Comment", back_populates="parent",
                           cascade="all, delete-orphan")
    parent  = relationship("Comment", back_populates="replies",
                           remote_side="Comment.id")
 
    def __repr__(self):
        return f"<Comment id={self.id} post_id={self.post_id}>"
 
 
# =============================================================================
# LIKE
# =============================================================================
class Like(Base):
    """
    Stores likes given by users to posts.
 
    UniqueConstraint on (post_id, user_id) ensures a user
    can only like a specific post once — enforced at the database level.
    """
    __tablename__ = "likes"
 
    id      = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
 
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
 
    # Database-level constraint: one like per user per post
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_like_post_user"),
    )
 
    # Relationships
    post = relationship("Post", back_populates="likes")
    user = relationship("User", back_populates="likes")
 
    def __repr__(self):
        return f"<Like post_id={self.post_id} user_id={self.user_id}>"
 
 
# =============================================================================
# FOLLOW  ── NEW ──────────────────────────────────────────────────────────────
# =============================================================================
class Follow(Base):
    """
    Stores follower/following relationships between users.
 
    This is a "self-referential many-to-many" table:
    both follower_id and followed_id point back to users.id.
 
    Example row:
        follower_id = 3   (user 3 ...)
        followed_id = 7   (... follows user 7)
 
    UniqueConstraint on (follower_id, followed_id) ensures
    a user cannot follow the same person twice.
    """
    __tablename__ = "follows"
 
    id = Column(Integer, primary_key=True, index=True)
 
    # The user who is doing the following
    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)
 
    # The user who is being followed
    followed_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)
 
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
 
    # Prevent duplicate follows (one user can't follow another twice)
    __table_args__ = (
        UniqueConstraint("follower_id", "followed_id", name="uq_follow_pair"),
    )
 
    # Relationships
    # "follower" = the User row for follower_id
    follower = relationship("User", foreign_keys=[follower_id],
                            back_populates="following")
    # "followed" = the User row for followed_id
    followed = relationship("User", foreign_keys=[followed_id],
                            back_populates="followers")
 
    def __repr__(self):
        return f"<Follow follower_id={self.follower_id} followed_id={self.followed_id}>"
 
 
# =============================================================================
# NOTIFICATION  ── NEW ────────────────────────────────────────────────────────
# =============================================================================
class Notification(Base):
    """
    Stores activity notifications for users.
 
    Example:
      - "Jalloh liked your post"      → type="like"
      - "Fatima commented on your post" → type="comment"
      - "Ibrahim started following you" → type="follow"
 
    recipient_id = who RECEIVES the notification (whose feed it shows in)
    actor_id     = who CAUSED the notification (who liked/commented/followed)
    """
    __tablename__ = "notifications"
 
    id = Column(Integer, primary_key=True, index=True)
 
    # Who sees this notification
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                           nullable=False, index=True)
 
    # Who triggered this notification (the "actor")
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                       nullable=False, index=True)
 
    # Type of notification: "like", "comment", "follow"
    type = Column(String(20), nullable=False)
 
    # Optional: related post (for like/comment notifications)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"),
                      nullable=True, index=True)
 
    # Has the recipient read this notification yet?
    is_read = Column(Boolean, default=False, nullable=False)
 
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
 
    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_id],
                             back_populates="notifications")
    actor     = relationship("User", foreign_keys=[actor_id])
    post      = relationship("Post")
 
    def __repr__(self):
        return f"<Notification id={self.id} type={self.type!r} recipient_id={self.recipient_id}>"