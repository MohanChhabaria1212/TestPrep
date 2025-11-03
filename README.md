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

  1. Install dependencies: `pip install -r requirements.txt`
  2. Configure environment variables (database, Redis URL, etc.) via `.env`
  3. Run migrations: `python manage.py migrate`
  4. Start services:
     - Django app: `python manage.py runserver`
     - Celery worker: `celery -A testprep worker -l info`
     - Celery beat (optional for scheduled jobs): `celery -A testprep beat -l info`
  5. Seed initial topics/questions or load fixtures as required.



