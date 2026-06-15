# app/utils.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   Utility functions for password hashing and verification.
#   Uses passlib with bcrypt — the industry-standard algorithm
#   for securely storing passwords.
#
# HOW BCRYPT WORKS:
#   - hash_password("secret") → "$2b$12$randomsalt...hashedvalue"
#   - The hash includes a random salt automatically
#   - verify_password() re-hashes and compares safely (timing-attack resistant)
#   - The original password can NEVER be recovered from the hash
# ─────────────────────────────────────────────────────────────────────────────

from passlib.context import CryptContext


# CryptContext handles algorithm selection and future-proofing
# schemes=["bcrypt"] → use bcrypt as the hashing algorithm
# deprecated="auto"  → automatically upgrade old hashes if needed
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Takes a plain-text password and returns a bcrypt hash.
    Called during user registration before saving to the database.

    Example:
        hash_password("mysecret123")
        → "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36..."
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.
    Called during login to check if the submitted password is correct.

    Example:
        verify_password("mysecret123", "$2b$12$Eix...") → True
        verify_password("wrongpass",   "$2b$12$Eix...") → False
    """
    return pwd_context.verify(plain_password, hashed_password)