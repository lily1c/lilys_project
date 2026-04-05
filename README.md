
# snip.it — URL Shortener

A scalable URL shortener with a live dashboard, built for the MLH PE Hackathon Scalability Quest (Gold Tier).

```
                         ┌──────────────────┐
                         │    Nginx (LB)     │
                         └──┬─────┬─────┬───┘
                            │     │     │
                        ┌───▼┐ ┌──▼─┐ ┌─▼──┐
                        │App1│ │App2│ │App3│  ← 3× Flask/Gunicorn
                        └─┬──┘ └─┬──┘ └─┬──┘
                          │      │      │
                    ┌─────▼──┐ ┌─▼──────▼─┐
                    │Postgres│ │   Redis   │
                    └────────┘ └──────────┘
```

## Quick Start

### Local (no Docker)
```bash
git clone https://github.com/lily1c/lilys_project.git
cd lilys_project
pip install flask peewee python-dotenv psycopg2-binary redis
cp .env.example .env        # Edit DATABASE_USER to your Mac username
python setup_db.py           # Creates tables + loads 400 users, 2000 URLs, 3422 events
python run.py                # http://localhost:5000/dashboard
```

> **macOS note:** Port 5000 may be taken by AirPlay. Turn it off in System Settings → General → AirDrop & Handoff, or run on a different port with `python -c "from app import create_app; app = create_app(); app.run(port=5005)"`.

### Docker (full stack)
```bash
cp .env.example .env
docker-compose up -d --build   # Starts 6 containers
# http://localhost:5006/dashboard
```

## What It Does

**Shorten URLs** — `POST /shorten` generates an 8-character code. Visiting that code redirects to the original URL.

**Track analytics** — Every redirect logs the visitor's IP, browser, platform, referrer, and timestamp.

**Manage users** — Full CRUD with pagination, bulk CSV import, and cascade deletes.

**Live dashboard** — A single-file frontend at `/dashboard` that talks to the same API. No build step, no separate server.

## API

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `POST` | `/shorten` | Shorten a URL → returns `{short_code}` |
| `GET` | `/<code>` | Redirect to original URL |
| `GET` | `/dashboard` | Frontend UI |
| `GET` | `/health` | `{"status": "ok"}` |
| `GET` | `/metrics` | `{total_urls, total_users}` |
| `GET/POST/PUT/DELETE` | `/users` | User CRUD (paginated) |
| `GET/POST/PUT/DELETE` | `/urls` | URL CRUD |
| `GET/POST` | `/events` | Event log (filterable by type, user, URL) |

**Example:**
```bash
# Shorten
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/lily1c"}'

# Follow it
curl -L http://localhost:5000/xK4m7291
```

## Scalability Quest Progress

| Tier | Requirement | Status |
|------|-------------|--------|
| 🥉 Bronze | Unit tests, health check, CRUD, input validation, seed data | ✅ |
| 🥈 Silver | Docker, Nginx LB, Redis cache, k6 at 200 VUs | ✅ |
| 🥇 Gold | 500 VUs (p95 < 500ms, err < 0.2%), graceful recovery, frontend, docs | ✅ |

## Load Testing

```bash
brew install k6
k6 run k6/load_test.js
```

Ramps from 0 → 200 → 500 virtual users. Each VU creates a short URL and follows the redirect. The script auto-prints which tier you hit.

## How It Scales

- **3 Flask instances** behind Nginx round-robin — no single point of failure
- **Gunicorn** with 4 workers × 2 threads per instance = 24 concurrent handlers
- **Redis** caches URL lookups (1h TTL) so redirects skip the database
- **`restart: always`** on every app container — kill one, Docker restarts it, Nginx routes around it
- **Graceful Redis fallback** — if Redis dies, the app keeps working via PostgreSQL

## Project Structure

```
app/
├── models/          # User, URL, Event (Peewee ORM)
├── routes/          # CRUD endpoints + frontend serving
├── static/          # dashboard.html (vanilla JS, single file)
├── cache.py         # Redis with graceful fallback
└── database.py      # PostgreSQL connection

k6/load_test.js      # Load test (Bronze → Silver → Gold)
docker-compose.yml   # 6 containers, restart: always
nginx.conf           # Round-robin load balancer
setup_db.py          # Seed data loader
ARCHITECTURE.md      # Full architecture documentation
```

## Team

- [Assol Abasova (@lily1c)](https://github.com/lily1c)
- [Koleaje Olayinka (@koleajeolayinka)](https://github.com/koleajeolayinka)

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical deep dive — request flows, database schema, caching strategy, decision log, runbooks, and capacity planning.
