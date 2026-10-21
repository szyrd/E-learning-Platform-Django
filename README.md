# LearnHub · E-learning Platform (Django)

A Coursera-style online learning platform built with **Django 5.1**, **Django REST Framework**, **PostgreSQL** and **Docker**.
Students browse a catalog, enroll (free or simulated checkout), watch video lessons, take graded quizzes and track progress.
Instructors create courses, lessons and quizzes, and follow their students' progress from a dashboard.

![stack](https://img.shields.io/badge/Django-5.1-0C4B33?logo=django) ![drf](https://img.shields.io/badge/DRF-3.15-a30000) ![postgres](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql) ![docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker)

---

## Features

**Learners**
- Public catalog with search, category / level / price filters, sorting and pagination
- Coursera-style course page: outcomes, syllabus with free previews, instructor bio, rating breakdown and reviews
- One-click enrollment for free courses, simulated card / PayPal checkout for paid ones
- Learning view with video player (YouTube, Vimeo or direct MP4), sidebar outline and live progress bar
- Graded multiple-choice quizzes with pass marks, per-question feedback and attempt history
- "My Learning" dashboard (in progress / completed), purchase history, course reviews

**Instructors**
- Dashboard with courses, students, average rating and revenue
- Course editor (thumbnail, level, price, outcomes, requirements, publish / draft)
- Lesson manager with reordering and free-preview flag
- Quiz builder with inline question editor and recent attempts
- Student list with per-enrollment progress

**Platform**
- Role-based accounts (student / instructor), email or username login, strong-password validation
- Ownership checks on every mutating view, POST-only deletes, CSRF everywhere
- REST API (`/api/`) with JWT auth: courses, lessons, reviews, categories, my enrollments, enroll action
- Django admin for everything, `/health/` endpoint, WhiteNoise static files, 12-factor settings via env vars
- 40 automated tests

---

## Quick start (Docker Desktop)

```bash
cp .env.example .env          # adjust if you like; defaults work out of the box
docker compose up --build
```

Then open <http://localhost:8000>. On first start the container waits for Postgres, runs migrations,
collects static files, seeds demo data (`SEED_DEMO=1`) and creates an admin user.

| Role       | Username     | Password       |
|------------|--------------|----------------|
| Student    | `student`    | `learnhub123`  |
| Instructor | `ana.silva`  | `learnhub123`  |
| Admin      | `admin`      | `admin12345`   |

Other demo instructors: `marcus.lee`, `priya.nair`. Other students: `jordan.kim`, `maria.garcia`, `li.wei`.

Useful commands:

```bash
docker compose logs -f web                      # tail the app
docker compose exec web python manage.py test   # run tests inside the container
docker compose exec web python manage.py shell
docker compose down -v                          # stop and wipe the database volume
```

Production-style run (gunicorn, no source mount, `DEBUG=0`):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## Local development without Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r elearning/requirements.txt
cp .env.example .env
# Leave DATABASE_URL empty in .env to use SQLite, or point it at a local Postgres.
cd elearning
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Run the test-suite: `python manage.py test main`

---

## Configuration

All settings come from environment variables (see `.env.example`):

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Secret key | insecure dev key |
| `DJANGO_DEBUG` | `1` / `0` | `0` |
| `DJANGO_ALLOWED_HOSTS` | comma-separated | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | comma-separated origins | `http://localhost:8000,...` |
| `DATABASE_URL` | e.g. `postgres://user:pass@db:5432/name` | SQLite file |
| `SEED_DEMO` | seed demo content on container start | `0` |
| `DJANGO_SUPERUSER_*` | auto-create admin on start | – |
| `CORS_ALLOWED_ORIGINS` | for a separate front-end | – |

---

## Project layout

```
.
├── Dockerfile · docker-compose.yml · docker-compose.prod.yml · entrypoint.sh
├── .env.example
└── elearning/                 # Django project root (manage.py)
    ├── elearning/settings.py  # env-driven settings
    ├── main/
    │   ├── models.py          # User, Category, Course, Lesson, Quiz, Question,
    │   │                      # Enrollment, LessonCompletion, QuizAttempt, Review, Payment
    │   ├── services.py        # enroll(), grade_quiz(), progress helpers
    │   ├── views/             # auth · catalog · student · learning · instructor · api
    │   ├── serializers.py · api_urls.py
    │   ├── management/commands/{seed_demo,wait_for_db}.py
    │   └── tests/
    ├── templates/             # base + auth / catalog / student / learning / instructor
    └── static/css/app.css     # design tokens (Coursera-inspired) + components
```

## API overview

| Method | Endpoint | Auth |
|---|---|---|
| POST | `/api/token/` · `/api/token/refresh/` | – |
| GET | `/api/courses/?search=&level=&category__slug=&ordering=` | public |
| GET | `/api/courses/{slug}/` · `/lessons/` · `/reviews/` | public (lesson content only when enrolled) |
| POST | `/api/courses/{slug}/enroll/` | JWT / session (student) |
| GET | `/api/me/enrollments/` | JWT / session |
| GET | `/api/categories/` | public |

---

## Notes

- Payments are **simulated**: no card data is stored, a `Payment` record is written and the learner is enrolled.
- Database schema was rebuilt from scratch in this version (single `0001_initial` migration). Old databases are not compatible.
