# snip.it — URL Shortener

A scalable URL shortener with a live dashboard, built for the MLH PE Hackathon Scalability Quest (Gold Tier).

## Table of Contents

- [Quick Start](#quick-start)
  - [Local (no Docker)](#local-no-docker)
  - [Docker (full stack)](#docker-full-stack)
- [What It Does](#what-it-does)
- [API](#api)
- [Frontend](#frontend)
  - [Features](#features)
  - [Why a Frontend?](#why-a-frontend)
- [Scalability Quest Progress](#scalability-quest-progress)
- [Load Testing](#load-testing)
- [How It Scales](#how-it-scales)
- [Project Structure](#project-structure)
- [Team](#team)
- [Bonus Quest: Documentation](#bonus-quest-documentation)
  - [🥉 Bronze: The Map](#-bronze-the-map)
    - [Setup Instructions](#setup-instructions)
    - [Architecture Diagram](#architecture-diagram)
    - [API Docs](#api-docs)
  - [🥈 Silver: The Manual](#-silver-the-manual)
    - [Deploy Guide](#deploy-guide)
    - [Troubleshooting](#troubleshooting)
    - [Configuration](#configuration)
  - [🥇 Gold: The Codex](#-gold-the-codex)
    - [Runbooks](#runbooks)
    - [Decision Log](#decision-log)
    - [Capacity Plan](#capacity-plan)

## Quick Start

### Local (no Docker)

1. Clone the repository and navigate to the project directory:
   ```
   git clone https://github.com/lily1c/lilys_project.git
   cd lilys_project
   ```

2. Install the required dependencies:
   ```
   pip install flask peewee python-dotenv psycopg2-binary redis
   ```

3. Create a `.env` file based on the example:
   ```
   cp .env.example .env
   ```
   Edit the `DATABASE_USER` in `.env` to your Mac username.

4. Set up the database and load seed data:
   ```
   python setup_db.py
   ```
   This creates the necessary tables and loads 400 users, 2000 URLs, and 3422 events.

5. Run the application:
   ```
   python run.py
   ```
   Access the dashboard at http://localhost:5000/dashboard.

   Note: On macOS, port 5000 may be taken by AirPlay. If that's the case, turn it off in System Settings → General → AirDrop & Handoff, or run the app on a different port:
   ```
   python -c "from app import create_app; app = create_app(); app.run(port=5005)"
   ```

### Docker (full stack)

1. Create a `.env` file based on the example:
   ```
   cp .env.example .env
   ```

2. Start the Docker containers:
   ```
   docker-compose up -d --build
   ```
   This starts 6 containers for the full stack.

3. Access the dashboard at http://localhost:5006/dashboard.

## What It Does

- Shorten URLs — `POST /shorten` generates an 8-character code. Visiting that code redirects to the original URL.
- Track analytics — Every redirect logs the visitor's IP, browser, platform, referrer, and timestamp.
- Manage users — Full CRUD with pagination, bulk CSV import, and cascade deletes.
- Live dashboard — A single-file frontend at `/dashboard` that talks to the same API. No build step, no separate server.

## API

| Method | Endpoint | What it does |
|--------|----------|--------------|
| POST   | /shorten | Shorten a URL → returns {short_code} |
| GET    | /<code>  | Redirect to original URL |
| GET    | /dashboard | Frontend UI |
| GET    | /health  | {"status": "ok"} |
| GET    | /metrics | {total_urls, total_users} |
| GET/POST/PUT/DELETE | /users | User CRUD (paginated) |
| GET/POST/PUT/DELETE | /urls | URL CRUD |
| GET/POST | /events | Event log (filterable by type, user, URL) |

Example:

```bash
# Shorten
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/lily1c"}'

# Follow it  
curl -L http://localhost:5000/xK4m7291
```

## Frontend

The snip.it URL shortener includes a live dashboard frontend that provides visibility into the system's usage and performance. The frontend is a single HTML file (`dashboard.html`) that communicates with the backend API to display real-time metrics, manage URLs and users, and perform load testing.

### Features

- **Overview**: Displays key metrics such as total URLs, users, events, and redirects. Also shows the latest k6 load test results with performance metrics for each scalability tier.
- **Tests**: Allows running API smoke tests directly from the dashboard to verify the health and functionality of the system.
- **Shorten**: Provides a simple interface to create new short URLs and view the session events associated with each URL.
- **URLs**: Lists all the shortened URLs with their details, allows searching and filtering, and provides actions to activate/deactivate or delete URLs.
- **Users**: Displays the list of users with pagination, allows searching and filtering, and provides actions to create new users or delete existing ones.
- **Events**: Shows the event log with pagination and filtering options, including event type (redirect, created) and associated URL or user.

### Why a Frontend?

The frontend dashboard serves several purposes:

1. **Visibility**: It provides a clear overview of the system's usage and performance, allowing administrators and developers to monitor the URL shortener's health and identify any issues or trends.

2. **Management**: The dashboard offers a user-friendly interface to manage URLs and users without the need to interact with the API directly. This makes it easier for non-technical users to perform common tasks.

3. **Testing**: The built-in API smoke tests enable quick verification of the system's functionality and performance directly from the dashboard, making it convenient to ensure the URL shortener is working as expected.

4. **Demonstration**: The frontend showcases the URL shortener's capabilities and performance in a visual and interactive way, making it easier to demonstrate the system's scalability and features to stakeholders or users.

The frontend is designed to be lightweight and self-contained, using vanilla JavaScript and minimal dependencies. It can be easily customized and extended to add more features or integrate with other tools as needed.

## Scalability Quest Progress

| Tier | Requirement | Status |
|------|-------------|--------|
| 🥉 Bronze | Unit tests, health check, CRUD, input validation, seed data | ✅ |
| 🥈 Silver | Docker, Nginx LB, Redis cache, k6 at 200 VUs | ✅ |
| 🥇 Gold | 500 VUs (p95 < 500ms, err < 0.2%), graceful recovery, frontend, docs | ✅ |

## Load Testing

1. Install k6:
   ```
   brew install k6
   ```

2. Run the load test:
   ```
   k6 run k6/load_test.js
   ```
   This ramps from 0 → 200 → 500 virtual users. Each VU creates a short URL and follows the redirect. The script auto-prints which tier you hit.

## How It Scales

- 3 Flask instances behind Nginx round-robin — no single point of failure
- Gunicorn with 4 workers × 2 threads per instance = 24 concurrent handlers
- Redis caches URL lookups (1h TTL) so redirects skip the database
- `restart: always` on every app container — kill one, Docker restarts it, Nginx routes around it
- Graceful Redis fallback — if Redis dies, the app keeps working via PostgreSQL

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

- Assol Abasova (@lily1c)
- Koleaje Olayinka (@koleajeolayinka)

## Bonus Quest: Documentation

### 🥉 Bronze: The Map

#### Setup Instructions

See the [Quick Start](#quick-start) section for detailed setup instructions for both local and Docker environments.

#### Architecture Diagram

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

#### API Docs

See the [API](#api) section for a list of available endpoints and their functionalities.

### 🥈 Silver: The Manual

#### Deploy Guide

1. Set up the required infrastructure (PostgreSQL, Redis, Nginx).
2. Clone the repository and navigate to the project directory.
3. Create a `.env` file with the necessary environment variables (see [Configuration](#configuration)).
4. Build and start the Docker containers using `docker-compose up -d --build`.
5. The application should now be accessible via the configured Nginx port.

To rollback to a previous version:
1. Stop the running containers using `docker-compose down`.
2. Checkout the desired version from the Git repository.
3. Rebuild and start the containers using `docker-compose up -d --build`.

#### Troubleshooting

- If the application is not accessible, check if the containers are running using `docker-compose ps`.
- Check the container logs for any error messages using `docker-compose logs`.
- Ensure that the required environment variables are properly set in the `.env` file.
- Verify that the PostgreSQL and Redis services are running and accessible.

#### Configuration

The following environment variables are required to run the application:

- `DATABASE_URL`: PostgreSQL connection URL (e.g., `postgresql://user:password@host:port/database`)
- `REDIS_URL`: Redis connection URL (e.g., `redis://host:port`)
- `PORT`: Port number for the Flask application (default: `5000`)

### 🥇 Gold: The Codex

#### Runbooks

- **High CPU Usage**: If the CPU usage exceeds 80%:
  1. Check the container metrics to identify the affected service.
  2. Investigate the application logs for any resource-intensive operations.
  3. Consider scaling up the number of containers or optimizing the code.

- **Database Connection Errors**: If there are frequent database connection errors:
  1. Verify that the PostgreSQL service is running and accessible.
  2. Check the `DATABASE_URL` environment variable for the correct connection details.
  3. Investigate the PostgreSQL logs for any errors or resource constraints.

#### Decision Log

- **Redis**: Redis was chosen as the caching layer to improve performance by storing frequently accessed data in memory. It provides fast read and write operations, reducing the load on the database.

- **Nginx**: Nginx was selected as the load balancer due to its high performance, reliability, and ease of configuration. It efficiently distributes incoming requests across multiple application instances, ensuring high availability and scalability.

- **Flask**: Flask was chosen as the web framework for its simplicity, flexibility, and extensibility. It provides a lightweight and modular foundation for building the API and handling HTTP requests.

- **Peewee**: Peewee was selected as the ORM (Object-Relational Mapping) library for its simplicity and ease of use. It provides a clean and expressive way to interact with the PostgreSQL database, reducing boilerplate code and improving development productivity.

#### Capacity Plan

Based on load testing results and the current infrastructure setup:

- The application can handle up to 500 concurrent users with a 95th percentile latency below 500ms and an error rate below 0.2%.
- The bottleneck is likely to be the database connection pool. Increasing the number of database connections and optimizing queries can help handle higher loads.
- Vertical scaling (increasing resources of existing instances) and horizontal scaling (adding more instances) can be employed to accommodate future growth.
- Monitoring and profiling should be implemented to identify performance bottlenecks and optimize resource utilization.

See ARCHITECTURE.md for the full technical deep dive — request flows, database schema, caching strategy, decision log, runbooks, and capacity planning.
