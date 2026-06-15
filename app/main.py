# app/main.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   The entry point of the entire application.
#   This file:
#     1. Creates the FastAPI app instance
#     2. Creates all database tables on startup
#     3. Registers all routers (auth, users, posts, comments, likes,
#        follows, notifications)
#     4. Adds CORS middleware
#     5. Serves uploaded images from /uploads
#     6. Serves the frontend HTML at GET /app
#     7. Defines a health-check route at GET /
#
# TO RUN THE SERVER:
#   uvicorn app.main:app --reload --reload-dir app
#
# FRONTEND:
#   Open → http://127.0.0.1:8000/app
#
# API DOCS:
#   Swagger UI → http://127.0.0.1:8000/docs
#   ReDoc      → http://127.0.0.1:8000/redoc
#
# NEW IN THIS VERSION:
#   - Registered follow.router (follow/unfollow, followers/following lists)
#   - Registered notification.router (activity notifications)
# ─────────────────────────────────────────────────────────────────────────────

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import Base, engine
from app import models
from app.routers import auth, user, post, comment, like, follow, notification


# ── Create all database tables ────────────────────────────────────────────────
# SQLAlchemy reads all classes that inherit from Base (defined in models.py)
# and creates the corresponding tables in PostgreSQL if they don't exist yet.
# This will create the new "follows" and "notifications" tables,
# and add the new avatar_url/cover_url columns... actually NOTE:
# create_all() only creates tables that don't exist — it does NOT
# add new columns to EXISTING tables. See the note at the bottom
# of this file for how to add the new columns to "users".
# NOTE: For production, replace this with Alembic migrations.
models.Base.metadata.create_all(bind=engine)


# ── FastAPI application instance ──────────────────────────────────────────────
app = FastAPI(
    title       = "Social Media Post API",
    description = (
        "A professional FastAPI-based social media backend.\n\n"
        "Features: User registration, JWT authentication, "
        "posts, comments, likes, follows, notifications, "
        "profile/cover photo uploads, role-based access control.\n\n"
        "Built for PROG315 — Object-Oriented Programming 2\n"
        "Limkokwing University of Creative Technology, Sierra Leone."
    ),
    version     = "1.1.0",
    contact     = {
        "name":  "Your Group Name",
        "email": "yourgroup@example.com"
    },
    license_info = {
        "name": "MIT",
        "url":  "https://opensource.org/licenses/MIT"
    },
    docs_url    = "/docs",     # Swagger UI
    redoc_url   = "/redoc"     # ReDoc
)


# ── CORS Middleware ───────────────────────────────────────────────────────────
# Allows frontend applications running on different origins to call this API.
# For production: replace allow_origins=["*"] with your actual frontend URL
# e.g. allow_origins=["https://yourapp.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ── Uploads folder ────────────────────────────────────────────────────────────
# Serves uploaded avatar/cover images at http://127.0.0.1:8000/uploads/<filename>
uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


# ── Register Routers ──────────────────────────────────────────────────────────
# Each router handles a specific resource domain.
# The prefix defined in each router file is used for all its endpoints.
app.include_router(auth.router)         # /auth/login
app.include_router(user.router)         # /users/...
app.include_router(post.router)         # /posts/...
app.include_router(comment.router)      # /posts/{id}/comments, /comments/{id}
app.include_router(like.router)         # /posts/{id}/like, /posts/{id}/likes
app.include_router(follow.router)       # NEW: /users/{id}/follow, followers, following
app.include_router(notification.router) # NEW: /notifications


# ── Frontend route ────────────────────────────────────────────────────────────
# Serves index.html at http://127.0.0.1:8000/app
# The index.html file must be in the ROOT of your project folder
# (same level as the app/ folder, NOT inside app/)
@app.get("/app", include_in_schema=False)
def frontend():
    index_path = Path(__file__).resolve().parent.parent / "index.html"
    return FileResponse(str(index_path))


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health Check"])
def root():
    """
    Root endpoint — confirms the API is running.
    Frontend  → http://127.0.0.1:8000/app
    Swagger   → http://127.0.0.1:8000/docs
    ReDoc     → http://127.0.0.1:8000/redoc
    """
    return {
        "status":   "running",
        "message":  "Social Media Post API is live",
        "frontend": "http://127.0.0.1:8000/app",
        "docs":     "http://127.0.0.1:8000/docs",
        "redoc":    "http://127.0.0.1:8000/redoc",
        "version":  "1.1.0"
    }


# =============================================================================
# IMPORTANT NOTE — ADDING NEW COLUMNS TO AN EXISTING TABLE
# =============================================================================
#
# models.Base.metadata.create_all(bind=engine) ONLY creates tables that
# do not exist yet. Since your "users" table ALREADY exists from before,
# create_all() will NOT automatically add the new avatar_url and cover_url
# columns to it.
#
# To add these two columns to your existing "users" table, run this ONCE
# in pgAdmin's Query Tool (connected to social_media_db):
#
#     ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);
#     ALTER TABLE users ADD COLUMN cover_url  VARCHAR(500);
#
# After running that SQL once, restart your server. The new "follows" and
# "notifications" tables WILL be created automatically by create_all()
# since they are brand new tables.
# =============================================================================
