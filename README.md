# Social Media Post API

A professional REST API for a social media platform built with **FastAPI**,
**PostgreSQL**, and **JWT Authentication**.

Built as a final group project for **PROG315 — Object-Oriented Programming 2**
at Limkokwing University of Creative Technology, Sierra Leone.

---

## Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.11+ | Programming language |
| FastAPI | Web framework |
| PostgreSQL | Database |
| SQLAlchemy | ORM |
| Pydantic v2 | Validation |
| JWT + bcrypt | Auth & Security |
| Uvicorn | ASGI Server |

---

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/social-media-api.git
cd social-media-api
```

### 2. Create and activate virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 5. Create the PostgreSQL database
```sql
CREATE DATABASE social_media_db;
```

### 6. Run the server
```bash
uvicorn app.main:app --reload
```

### 7. Open API documentation
- Swagger UI → http://localhost:8000/docs
- ReDoc      → http://localhost:8000/redoc

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /auth/login | None | Login and get JWT token |
| POST | /users/register | None | Register new account |
| GET | /users/me | Required | Get own profile |
| PUT | /users/me | Required | Update own profile |
| GET | /users/{id} | None | Get public profile |
| POST | /posts/ | Required | Create a post |
| GET | /posts/ | None | Get all posts |
| GET | /posts/{id} | None | Get single post |
| PUT | /posts/{id} | Required | Update post (owner) |
| DELETE | /posts/{id} | Required | Delete post (owner/admin) |
| POST | /posts/{id}/comments | Required | Add comment |
| GET | /posts/{id}/comments | None | Get comments |
| PUT | /comments/{id} | Required | Edit comment |
| DELETE | /comments/{id} | Required | Delete comment |
| POST | /posts/{id}/like | Required | Like a post |
| DELETE | /posts/{id}/like | Required | Unlike a post |
| GET | /posts/{id}/likes | None | Get like count |

---

## License
MIT — see [LICENSE](LICENSE)