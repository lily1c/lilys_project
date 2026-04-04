# 🚀 Scalability Quest - URL Shortener

A scalable URL shortener API built for the MLH PE Hackathon - Scalability Engineering Quest.

## Tech Stack

- **Backend:** Python/Flask, Peewee ORM
- **Database:** PostgreSQL
- **Caching:** Redis
- **Load Balancer:** Nginx
- **Containerization:** Docker Compose
- **Load Testing:** k6

## Features

- ✅ URL shortening with unique codes
- ✅ User management (CRUD)
- ✅ Event tracking
- ✅ Health check endpoint
- ✅ Metrics endpoint

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | App metrics |
| POST | `/shorten` | Create short URL |
| GET | `/<short_code>` | Redirect to original URL |
| GET | `/stats/<short_code>` | Get URL statistics |
| GET | `/users` | List users (paginated) |
| GET | `/users/<id>` | Get user by ID |
| POST | `/users` | Create user |
| PUT | `/users/<id>` | Update user |
| DELETE | `/users/<id>` | Delete user |
| GET | `/events` | List events |

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL
- uv (Python package manager)

### Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# Clone and install
git clone https://github.com/lily1c/lilys_project.git
cd lilys_project
uv sync

# Create database
createdb hackathon_db

# Configure environment
cp .env.example .env
# Edit .env: set DATABASE_USER to your Mac username, DATABASE_PASSWORD empty

# Load seed data
uv run setup_db.py

# Run server
uv run flask run --port 5005
```

### Test

```bash
curl http://localhost:5005/health
curl http://localhost:5005/users/1
curl -X POST http://localhost:5005/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com"}'
```

## Scalability Quest Progress

| Tier | Requirement | Status |
|------|-------------|--------|
| 🥉 Bronze | 50 concurrent users | ✅ Passed |
| 🥈 Silver | 200 users + load balancer | ✅ Passed |
| 🥇 Gold | 500 users + Redis caching | ✅ Passed |

## Load Testing

```bash
# Install k6
brew install k6

# Run load test
k6 run k6/load_test.js
```

## Architecture

```
                ┌─────────────┐
                │    Nginx    │
                │  (Port 80)  │
                └──────┬──────┘
                       │
           ┌───────────┼───────────┐
           │           │           │
       ┌───▼───┐   ┌───▼───┐   ┌───▼───┐
       │ App 1 │   │ App 2 │   │ App 3 │
       │ :8000 │   │ :8000 │   │ :8000 │
       └───┬───┘   └───┬───┘   └───┬───┘
           │           │           │
           └───────────┼───────────┘
                       │
               ┌───────┴───────┐
               │               │
           ┌───▼───┐       ┌───▼────┐
           │ Redis │       │Postgres│
           │ Cache │       │   DB   │
           └───────┘       └────────┘
```

## Project Structure

```
├── app/
│   ├── __init__.py          # App factory
│   ├── database.py          # Database connection
│   ├── models/
│   │   ├── user.py          # User model
│   │   ├── url.py           # URL model
│   │   └── event.py         # Event model
│   └── routes/
│       ├── users.py         # User endpoints
│       ├── urls.py          # URL shortener endpoints
│       └── events.py        # Event endpoints
├── seed_data/
│   ├── users.csv            # 400 users
│   ├── urls.csv             # 2000 URLs
│   └── events.csv           # 3422 events
├── k6/
│   └── load_test.js         # Load testing script
├── setup_db.py              # Database setup + seed loader
├── Dockerfile               # Container config
├── docker-compose.yml       # Multi-container setup
├── nginx.conf               # Load balancer config
└── README.md
```

## Team

- [Assol Abasova (@lily1c)](https://github.com/lily1c)
- [Koleaje Olayinka (@koleajeolayinka)](https://github.com/koleajeolayinka)

## License

MIT
