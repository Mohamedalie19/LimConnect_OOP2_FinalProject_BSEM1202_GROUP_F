# app/database.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   Sets up the SQLAlchemy connection to PostgreSQL.
#   Provides three things every other file needs:
#     1. engine       — the raw database connection
#     2. SessionLocal — factory that creates database sessions
#     3. Base         — the class all ORM models inherit from
#
# HOW IT WORKS:
#   create_engine() reads the DATABASE_URL from .env and creates
#   a connection pool to PostgreSQL. SessionLocal() produces one
#   session per request (opened and closed by get_db() in deps.py).
# ─────────────────────────────────────────────────────────────────────────────

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
# The engine manages the connection pool to PostgreSQL.
# echo=False means SQL queries won't be printed to the terminal.
# Set echo=True temporarily if you want to debug raw SQL statements.
engine = create_engine(
    settings.DATABASE_URL,
    echo=False
)


# ── Session Factory ───────────────────────────────────────────────────────────
# SessionLocal() creates a new database session.
# autocommit=False → we control when changes are committed (safer)
# autoflush=False  → changes aren't sent to DB until we call commit()
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ── Base Class ────────────────────────────────────────────────────────────────
# All ORM models in models.py inherit from Base.
# SQLAlchemy uses Base to track all model classes and their table mappings.
# When we call Base.metadata.create_all(bind=engine) in main.py,
# SQLAlchemy reads all models registered under Base and creates
# the corresponding PostgreSQL tables if they don't exist yet.
Base = declarative_base()