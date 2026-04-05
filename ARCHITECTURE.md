
# Architecture — snip.it URL Shortener

## Overview

snip.it is a production-grade URL shortener built for the MLH PE Hackathon Scalability Quest. The system shortens URLs, tracks redirect analytics, manages users, and serves a live dashboard — all behind a load-balanced, cached, containerized stack designed to handle 500+ concurrent users with graceful failure recovery.

## Architecture Diagram

```
                         ┌──────────────────────┐
                         │       Browser         │
                         │  localhost:5006        │
                         └──────────┬─────────────┘
                                    │
                         ┌──────────▼─────────────┐
                         │     Nginx (port 80)     │
                         │    Load Balancer         │
                         │   Round-robin across     │
                         │    3 app instances        │
                         └──┬───────┬──────┬───────┘
                            │       │      │
                ┌───────────▼─┐ ┌───▼────┐ ┌▼───────────┐
                │  Flask App 1 │ │ App 2  │ │  Flask App 3│
                │  Gunicorn    │ │Gunicorn│ │  Gunicorn   │
                │  4 workers   │ │4 wrkrs │ │  4 workers  │
                │  2 threads   │ │2 thrds │ │  2 threads  │
                │  :8000       │ │ :8000  │ │  :8000      │
                └──┬────────┬──┘ └┬─────┬┘ └──┬────────┬──┘
                   │        │     │     │     │        │
            ┌──────▼────────▼─────▼─┐ ┌─▼─────▼────────▼──────┐
            │    PostgreSQL 14       │ │     Redis 7 (Alpine)   │
            │                        │ │                        │
            │  Tables:               │ │  Cached keys:          │
            │   • users (400 rows)   │ │   • url:{short_code}   │
            │   • urls  (2000 rows)  │ │   • TTL: 3600s         │
            │   • events (3422 rows) │ │                        │
            └────────────────────────┘ └────────────────────────┘
```

## Request Flow

### URL Shortening (POST /shorten)
```
Browser ──POST──▶ Nginx ──▶ Flask (any instance)
                                │
                                ├── Validate URL format (must start with http:// or https://)
                                ├── Check for duplicates in PostgreSQL
                                ├── Generate 8-char short code (4 random + 4 timestamp)
                                ├── INSERT into urls table
                                ├── Cache in Redis: url:{short_code} → original_url (TTL 1h)
                                └── Return JSON with short_code
```

### URL Redirect (GET /:short_code)
```
Browser ──GET──▶ Nginx ──▶ Flask (any instance)
                                │
                                ├── Check Redis cache for url:{short_code}
                                │     HIT  → use cached original_url (skip DB)
                                │     MISS → query PostgreSQL, then cache result
                                ├── Check is_active flag (return 410 if deactivated)
                                ├── Log event to events table (IP, user agent, referrer)
                                └── HTTP 302 redirect to original_url
```

### Dashboard (GET /dashboard)
```
Browser ──GET──▶ Nginx ──▶ Flask (any instance)
                                │
                                └── send_from_directory('app/static', 'dashboard.html')

Page loads, then JS fetches:
   fetch('/metrics')   → {total_urls, total_users}
   fetch('/events')    → paginated event list
   fetch('/urls')      → all shortened URLs
```

## Database Schema

```
┌─────────────────────────────┐
│           users              │
├─────────────────────────────┤
│ id          SERIAL PK        │
│ username    VARCHAR(255)      │
│ email       VARCHAR(255) UQ   │
│ created_at  TIMESTAMP         │
└──────────────┬──────────────┘
               │ 1:N
               │
┌──────────────▼──────────────┐
│            urls              │
├─────────────────────────────┤
│ id           SERIAL PK       │
│ user_id      INT FK → users  │
│ short_code   VARCHAR(10) UQ  │
│ original_url VARCHAR(2048)   │
│ title        VARCHAR(255)    │
│ is_active    BOOLEAN         │
│ created_at   TIMESTAMP       │
│ updated_at   TIMESTAMP       │
└──────────────┬──────────────┘
               │ 1:N
               │
┌──────────────▼──────────────┐
│           events             │
├─────────────────────────────┤
│ id          SERIAL PK        │
│ url_id      INT FK → urls    │
│ user_id     INT FK → users   │
│ event_type  VARCHAR(50)      │
│ timestamp   TIMESTAMP        │
│ details     TEXT (JSON)       │
└─────────────────────────────┘
```

## API Documentation

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check — returns `{"status": "ok"}` |
| `GET` | `/metrics` | Total URLs and users count |
| `GET` | `/dashboard` | Serves the frontend UI |

### URL Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/shorten` | Create a short URL |
| `GET` | `/<short_code>` | Redirect to original URL (302) |
| `GET` | `/urls` | List all URLs (filterable by user_id, is_active) |
| `GET` | `/urls/<id>` | Get URL by ID |
| `PUT` | `/urls/<id>` | Update URL (title, is_active, original_url) |
| `DELETE` | `/urls/<id>` | Delete a URL |
| `GET` | `/stats/<short_code>` | Get URL statistics |

**POST /shorten** — Request:
```json
{
  "url": "https://github.com/lily1c",
  "title": "My GitHub",
  "user_id": 1
}
```
Response (201):
```json
{
  "id": 2001,
  "short_code": "xK4m7291",
  "original_url": "https://github.com/lily1c",
  "short_url": "http://localhost:5006/xK4m7291",
  "title": "My GitHub",
  "user_id": 1,
  "is_active": true
}
```

### User Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users` | List users (paginated: `?page=1&per_page=20`) |
| `GET` | `/users/<id>` | Get user by ID |
| `POST` | `/users` | Create user (requires username, email) |
| `PUT` | `/users/<id>` | Update user |
| `DELETE` | `/users/<id>` | Delete user (cascades to URLs and events) |
| `POST` | `/users/bulk` | Bulk load users from CSV |

### Event Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/events` | List events (filterable: `?url_id=&user_id=&event_type=`) |
| `GET` | `/events/<id>` | Get event by ID |
| `POST` | `/events` | Create event |

## Input Validation

All endpoints enforce strict input validation:

- URL format must start with `http://` or `https://`
- URL length capped at 2048 characters
- Title length capped at 255 characters
- Username length capped at 50 characters
- Email length capped at 255 characters
- Event type length capped at 50 characters
- Type checking rejects non-string values for string fields and non-boolean for is_active
- Malformed JSON returns 400 with descriptive error message

## Caching Strategy

Redis caches the hot path — URL redirects:

- **Key pattern**: `url:{short_code}` → original URL string
- **TTL**: 3600 seconds (1 hour)
- **Write-through**: on URL creation, the mapping is cached immediately
- **Graceful degradation**: if Redis is down, the app falls back to PostgreSQL queries — `get_cache()` returns `None` and all Redis calls are wrapped in try/except
- **Why redirects**: they are the highest-traffic operation (every click on a short link) and they are read-only with a stable result — a perfect cache candidate

## Deployment

### Local Development
```bash
pip install flask peewee python-dotenv psycopg2-binary redis
cp .env.example .env          # Edit DATABASE_USER if needed
python setup_db.py             # Create tables + load seed data
python run.py                  # Starts on port 5000
# Open http://localhost:5000/dashboard
```

### Docker (Production)
```bash
cp .env.example .env
docker-compose up -d --build
# Open http://localhost:5006/dashboard
```

### Container Topology
```
NAME         SERVICE   STATUS          PORTS
db           db        running         5432:5432
redis        redis     running         6379:6379
app1         app1      running         (internal 8000)
app2         app2      running         (internal 8000)
app3         app3      running         (internal 8000)
nginx        nginx     running         5006:80
```

All app instances use `restart: always` — Docker automatically restarts any crashed container.

## Config

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_NAME` | `hackathon_db` | PostgreSQL database name |
| `DATABASE_HOST` | `localhost` | DB host (`db` in Docker) |
| `DATABASE_PORT` | `5432` | DB port |
| `DATABASE_USER` | `postgres` | DB user |
| `DATABASE_PASSWORD` | `postgres` | DB password |
| `REDIS_HOST` | `localhost` | Redis host (`redis` in Docker) |
| `REDIS_PORT` | `6379` | Redis port |

## Load Testing

k6 tests live in `k6/load_test.js`. The test ramps through all three tiers:

```
Stage 1:  0 → 200 VUs over 30s     (Silver threshold)
Stage 2:  200 → 500 VUs over 60s   (Gold threshold)
Stage 3:  500 → 0 VUs over 30s     (cooldown)
```

Each virtual user hits `/health`, creates a short URL via `POST /shorten`, then follows the redirect.

### Thresholds
| Metric | Requirement |
|--------|-------------|
| p95 latency | < 500ms |
| Error rate | < 0.2% |

### Running
```bash
brew install k6
k6 run k6/load_test.js
```

## Scalability Quest — Tier Checklist

### 🥉 Bronze — Foundation
- [x] Models: User, URL, Event with proper field types and constraints
- [x] Full CRUD: all endpoints for users, URLs, events
- [x] Health check: `GET /health` returns `{"status": "ok"}`
- [x] Seed data: 400 users, 2000 URLs, 3422 events loaded via `setup_db.py`
- [x] Input validation: length limits, type checks, URL format enforcement
- [x] Unit tests: health endpoint, URL creation, invalid input rejection

### 🥈 Silver — Scale
- [x] Docker Compose: 6 containers (db, redis, 3x app, nginx)
- [x] Nginx load balancer: round-robin across 3 Flask/Gunicorn instances
- [x] Gunicorn: 4 workers × 2 threads per container = 24 concurrent handlers
- [x] Redis caching: URL redirect lookups cached with 1h TTL
- [x] k6 load test: ramps to 200 VUs, passes thresholds

### 🥇 Gold — Resilience
- [x] 500 concurrent users: k6 ramps to 500 VUs, p95 < 500ms, errors < 0.2%
- [x] Graceful recovery: `restart: always` on all app containers — kill one, Nginx routes around it, Docker restarts it
- [x] Frontend dashboard: live UI at `/dashboard` served by Flask, no separate build
- [x] Analytics tracking: every redirect logs IP, user agent, referrer, browser, platform
- [x] Documentation: this file

## Troubleshooting

**App not responding**
```bash
docker-compose ps              # Check container status
docker logs <container_name>   # Check for errors
```

**Database connection errors**
- Verify `.env` credentials match PostgreSQL config
- In Docker the host is `db`, not `localhost`
- Check healthcheck: `pg_isready -U postgres -d hackathon_db`

**Redis not working**
- The app degrades gracefully — if Redis is unreachable it falls back to DB queries
- Check: `docker exec -it <redis-container> redis-cli ping`

**Port 5000 occupied on macOS**
- AirPlay Receiver uses port 5000 — turn it off in System Settings → General → AirDrop & Handoff
- Or use a different port: `python -c "from app import create_app; app = create_app(); app.run(port=5005)"`

**Load test failing thresholds**
- Check if all 3 app containers are running
- Verify Redis is connected (cache misses increase DB load)
- Monitor with `docker stats` during the test

## Runbooks

### High Latency Under Load
1. Run `docker stats` to identify which container is CPU-bound
2. Check Redis hit rate — cache misses mean every redirect hits PostgreSQL
3. If DB is the bottleneck: `urls.short_code` is already unique + indexed
4. If a single app instance is overloaded: check if one instance crashed — Nginx round-robin should distribute evenly

### Container Crash Recovery
1. `docker-compose ps` — identify the stopped container
2. With `restart: always`, Docker restarts it automatically within seconds
3. Nginx detects the dead upstream and stops routing to it until it recovers
4. No manual intervention needed — this is the gold tier recovery behavior

### Database Migration
1. Stop all app containers: `docker-compose stop app1 app2 app3`
2. Apply schema changes directly or via a migration script
3. Restart: `docker-compose start app1 app2 app3`
4. Peewee's `create_tables(..., safe=True)` won't break existing tables

## Decision Log

| Decision | Choice | Why |
|----------|--------|-----|
| Web framework | Flask | Lightweight, minimal boilerplate, great for API-first design |
| ORM | Peewee | Simpler than SQLAlchemy for hackathon scope, clean model syntax |
| Database | PostgreSQL 14 | ACID compliance, robust under concurrent writes |
| Cache | Redis 7 | Sub-millisecond reads, perfect for the redirect hot path |
| Load balancer | Nginx | Industry standard, simple round-robin config, handles upstream failures |
| WSGI server | Gunicorn | Production-grade, multi-worker, pairs well with Flask |
| Containers | Docker Compose | Single command to spin up the full stack |
| Load testing | k6 | Scriptable in JS, built-in threshold checking and VU ramping |
| Frontend | Vanilla HTML/JS | Zero build step, served by Flask, no CORS issues |

## Capacity Plan

**Current capacity** (3 instances, 4 workers × 2 threads each):
- 24 concurrent request handlers
- Redis absorbs redirect reads so DB only handles writes and cache misses
- Tested at 500 concurrent users with p95 < 500ms

**Scaling path if needed**:
- Horizontal: add `app4`, `app5` to docker-compose and nginx upstream — linear scaling
- Vertical: increase Gunicorn workers per instance (limited by container CPU/RAM)
- Database: add read replicas for query-heavy endpoints like `/events`
- Cache: extend Redis caching to user lookups and event queries

## Project Structure

```
├── app/
│   ├── __init__.py              # App factory (create_app)
│   ├── database.py              # DatabaseProxy, BaseModel, connection hooks
│   ├── cache.py                 # Redis init + graceful fallback
│   ├── models/
│   │   ├── user.py              # User model
│   │   ├── url.py               # URL model (short_code unique + indexed)
│   │   └── event.py             # Event model (redirect tracking)
│   ├── routes/
│   │   ├── __init__.py          # Blueprint registration
│   │   ├── urls.py              # URL shortening, redirect, CRUD
│   │   ├── users.py             # User CRUD + bulk CSV load
│   │   ├── events.py            # Event logging + querying
│   │   └── frontend.py          # Serves dashboard.html
│   └── static/
│       └── dashboard.html       # Single-file frontend (vanilla JS)
├── seed_data/
│   ├── users.csv                # 400 users
│   ├── urls.csv                 # 2000 URLs
│   └── events.csv               # 3422 events
├── k6/
│   └── load_test.js             # Bronze → Silver → Gold load test
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_health.py           # Health endpoint test
│   ├── test_urls.py             # URL creation + validation tests
│   └── test_users.py            # User creation + validation tests
├── setup_db.py                  # Creates tables + loads seed CSVs
├── Dockerfile                   # Python 3.11, Gunicorn, 4w/2t
├── docker-compose.yml           # 6 services, restart: always
├── nginx.conf                   # Round-robin upstream
├── .env.example                 # Environment template
└── ARCHITECTURE.md              # This file
```
