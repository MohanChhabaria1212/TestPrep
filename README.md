 # TestPrep Platform

  A Django & Django REST Framework backend for powering an online test-preparation product. It models competitive exams, manages question banks, tracks user attempts, and serves real-time leaderboards
  with post-exam analytics.

  ## Features

  - **Exam orchestration**: Define timed exams with configurable duration, marks, year, and supported exam types (CAT, GATE, JEE, NEET, etc.).
  - **Topic mapping & question bank**: Organize questions by topic, difficulty, and type (MCQ or puzzle), with rich-text content via CKEditor uploads.
  - **Secure session management**: Generate hash-based exam/user mappings so only authorized candidates can start or resume an exam; auto-creates question instances per user.
  - **Answer capture & validation**: Accept choice submissions during the test window, marking correctness instantly for MCQs and puzzle inputs.
  - **Scoring & analytics**: Compute total and per-topic scores, maintain historical performance profiles per user, and cache subject-level leaderboards.
  - **Leaderboard pipeline**: Use Celery + Redis to finalize incomplete attempts after the exam closes, rank users, and calculate overall/subject percentiles.
  - **Result forecasting**: Predict a candidate’s rank and percentile using historical exam stats with interpolation helpers.
  - **Optimized data access**: Cache-aware leaderboard queries, bulk updates, and JSON-based subject breakdowns for efficient analytics.

  ## Tech Stack

  - Django & Django REST Framework
  - PostgreSQL (or another Django-supported RDBMS)
  - Celery with Redis broker/locking
  - cacheops for query caching
  - CKEditor uploader for rich question content
  - NumPy for score interpolation utilities

  ## Key Apps & Modules

  - `tests/` – primary app housing models, serializers, URLs, views, Celery tasks, and utilities.
  - `testprep/celery.py` – Celery configuration for asynchronous jobs.
  - `testprep/utils.py` – shared helpers (e.g., UUID hash generator for public URLs).

  ## API Highlights

  | Endpoint | Description |
  | --- | --- |
  | `POST /tests/exams/<hash>/start/` | Start or resume a user’s exam session; reserves time window. |
  | `GET /tests/exam-user-mappings/<hash>/` | Fetch live exam state, including question payloads (answers hidden until completion). |
  | `PUT /tests/exam-user-mappings/<hash>/` | Mark the exam attempt as complete. |
  | `PUT /tests/exam-user-multiple-choice-question-mappings/<hash>/submit/` | Submit an answer for a specific question instance. |
  | `GET /tests/exams/<hash>/leaderboard/` | View finalized leaderboard; supports overall or topic-specific rankings. |

  Additional endpoints can be wired for result prediction or admin tooling as needed.

  ## Data Model Overview

  - `Topic` – Tagged subjects for grouping questions and exams.
  - `Exam` – Core exam entity with timing, marks, and mappings to topics/questions.
  - `MultipleChoiceQuestion` – Question bank entries with text/media and answer metadata.
  - `ExamUserMapping` – Represents a user’s attempt, tracking timing, scores, and percentiles.
  - `ExamUserMultipleChoiceQuestionMapping` – Per-question state for user answers.
  - `UserExamTypeProfile` & `UserTopicPerformanceProfile` – Historical performance aggregates.
  - `PastExamStats` – Stores prior-year rank vs. score/percentile curves for prediction.

## Running Locally

### 1. Install system prerequisites

- Python 3.10+ with `pip` and `virtualenv`
- PostgreSQL 13+ (local server or Docker)
- Redis (required for Celery; optional if you only need the Django app)

On macOS with Homebrew:

```bash
brew install postgresql redis
brew services start postgresql
brew services start redis
```

### 2. Create and activate a virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Provision the PostgreSQL database

Create a dedicated database and user for the project. Adjust names/passwords as desired.

```bash
createdb testprep
createuser testprep_user --pwprompt
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE testprep TO testprep_user;"
```

### 4. Configure environment variables

Duplicate `.env.example` (or create a new `.env`) and set the connection details, not required in this case but has to be done for security reasons.:

```env
DJANGO_SECRET_KEY=replace-me
DATABASE_URL=postgres://testprep_user:change-me@localhost:5432/testprep
CELERY_BROKER_URL=redis://localhost:6379/0
```


### 5. Apply database migrations and create a superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Run the services

- Start the Django dev server: `python manage.py runserver`
- Start a Celery worker: `celery -A testprep worker -l info`
- (Optional) Start Celery beat for scheduled jobs: `celery -A testprep beat -l info`

You should now be able to sign in at `http://127.0.0.1:8000/admin/` using the superuser credentials and begin creating exams, questions, and assignments.


