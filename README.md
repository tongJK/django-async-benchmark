# Django Async Benchmark

POC project comparing **sync vs async** performance in Django 6.0.

## What This Proves

| Scenario | Sync | Async | Winner | Why |
|---|---|---|---|---|
| **I/O Bound** (5 external API calls) | ~5s (sequential) | ~1s (concurrent) | 🟢 Async 5x | `asyncio.gather()` runs all calls concurrently |
| **DB Bound** (5 ORM queries) | Sequential | Concurrent | 🟡 Depends | Local DB: sync wins (async overhead > gain). Remote DB: async wins. |
| **Mixed** (APIs + DB) | All sequential | All concurrent | 🟢 Async | I/O and DB overlap |
| **CPU Bound** (hashing) | Blocking | Still blocking | 🔴 Same | Async doesn't parallelize CPU work |

### Bridge Patterns (sync ↔ async migration)

| Scenario | What it does | Compare with | Expected result |
|---|---|---|---|
| **sync_to_async** | Async view → sync ORM via thread pool | `/async/db-bound/` | Slightly slower (thread pool overhead) |
| **async_to_sync** | Sync view → async HTTP client | `/sync/io-bound/` | Much faster (concurrent HTTP inside sync view) |
| **Bridge Mixed** | Async view → sync ORM (bridged) + async HTTP | `/async/mixed/` | Close to pure async (ORM runs in thread, HTTP native) |

## Quick Start

```bash
# 1. Start PostgreSQL
make db

# 2. Install deps + migrate + seed data
make setup

# 3. Run with async support (uvicorn/ASGI)
make run-async

# 4. Test endpoints — compare sync vs async

# I/O-bound (the biggest difference: ~5s sync vs ~1s async)
curl http://localhost:8000/api/v1/sync/io-bound/
curl http://localhost:8000/api/v1/async/io-bound/

# DB-bound
curl http://localhost:8000/api/v1/sync/db-bound/
curl http://localhost:8000/api/v1/async/db-bound/

# CPU-bound (should be roughly the same)
curl http://localhost:8000/api/v1/sync/cpu-bound/
curl http://localhost:8000/api/v1/async/cpu-bound/

# Bridge — thread_sensitive footgun
curl http://localhost:8000/api/v1/bridge/sync-to-async/
curl http://localhost:8000/api/v1/bridge/sync-to-async-sensitive/

# Check timing header on any endpoint
curl -sI http://localhost:8000/api/v1/async/db-bound/ | grep X-Request

# 5. View results (after a few runs)
curl -s http://localhost:8000/api/v1/results/summary/ | python3 -m json.tool
```

## Run Benchmarks

```bash
# Run k6 against ASGI server (async)
make bench

# Run k6 against WSGI server (sync) — start with `make run-sync` first
make bench-sync

# Run with mock mode (offline, deterministic)
make bench-mock
```

k6 outputs a comparison table at the end:
```
╔══════════════════════════════════════════════════════════╗
║           SYNC vs ASYNC BENCHMARK RESULTS              ║
╠════════════╦══════════╦══════════╦══════════╦══════════╣
║ Scenario   ║ Sync p50 ║ Async p50║ Speedup  ║ Winner   ║
╠════════════╬══════════╬══════════╬══════════╬══════════╣
║ I/O Bound  ║ 5032ms   ║ 1021ms   ║ 4.9x     ║ Async    ║
║ DB Bound   ║ 45ms     ║ 55ms     ║ 0.8x     ║ Sync*    ║
║ Mixed      ║ 5078ms   ║ 1043ms   ║ 4.9x     ║ Async    ║
║ CPU Bound  ║ 312ms    ║ 310ms    ║ 1.0x     ║ Tie      ║
╚════════════╩══════════╩══════════╩══════════╩══════════╝
```

> *\*DB Bound*: With a local PostgreSQL, queries are so fast (~5-10ms each)
> that async overhead (event loop, connection setup) costs more than
> concurrency saves. Async DB wins when: queries are slower (remote DB,
> complex joins), or under high concurrency (many simultaneous requests).

## Mock Mode (Offline)

By default, I/O-bound benchmarks use a **local mock endpoint** instead of httpbin.org. This means:
- ✅ No internet required
- ✅ Deterministic results (configurable delay)
- ✅ Faster iteration during development

Configure in `.env` or environment:
```bash
BENCHMARK_IO_MODE=mock      # "mock" (default) or "external"
BENCHMARK_MOCK_DELAY=1.0    # seconds per mock call
```

To use real external APIs: `BENCHMARK_IO_MODE=external make run-async`

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/v1/health/` | Health check (DB connectivity) |
| `GET /api/v1/sync/io-bound/` | 5 external API calls (sequential) |
| `GET /api/v1/async/io-bound/` | 5 external API calls (concurrent) |
| `GET /api/v1/sync/db-bound/` | 5 DB queries (sequential) |
| `GET /api/v1/async/db-bound/` | 5 DB queries (concurrent) |
| `GET /api/v1/sync/mixed/` | APIs + DB (sequential) |
| `GET /api/v1/async/mixed/` | APIs + DB (concurrent) |
| `GET /api/v1/sync/cpu-bound/` | CPU computation |
| `GET /api/v1/async/cpu-bound/` | CPU computation (same speed) |
| `GET /api/v1/bridge/sync-to-async/` | Async view + sync ORM via `sync_to_async` |
| `GET /api/v1/bridge/async-to-sync/` | Sync view + async HTTP via `async_to_sync` |
| `GET /api/v1/bridge/mixed/` | Async view + bridged ORM + native async HTTP |
| `GET /api/v1/results/` | List benchmark results |
| `GET /api/v1/results/summary/` | Aggregated comparison |
| `POST /api/v1/results/clear/` | Clear all results |
| `GET /api/v1/mock/delay/` | Mock delay endpoint (for offline benchmarks) |

## Docker

```bash
# Run everything in containers
docker compose up -d

# ASGI server: http://localhost:8000
# WSGI server: http://localhost:8001

# Run migrations + seed inside container
docker compose exec app-async python manage.py migrate
docker compose exec app-async python manage.py seed_data
```

## Stack

- Python 3.14 + Django 6.0
- PostgreSQL 17 + psycopg3 (native async)
- uvicorn (ASGI) / gunicorn (WSGI)
- httpx (sync + async HTTP client)
- k6 (load testing)

## Project Structure

```
├── benchmarks/
│   ├── services/
│   │   ├── timing.py          # @benchmark_timer decorator
│   │   ├── external.py        # sync/async HTTP calls (mock + real)
│   │   ├── db_queries.py      # sync/async ORM queries
│   │   ├── cpu_tasks.py       # CPU-bound work
│   │   └── bridge_queries.py  # sync_to_async / async_to_sync wrappers
│   ├── views_sync.py          # sync benchmark views
│   ├── views_async.py         # async benchmark views
│   ├── views_bridge.py        # sync_to_async / async_to_sync views
│   ├── views_results.py       # results + summary
│   ├── views_health.py        # health check
│   ├── views_mock.py          # mock delay server
│   └── models.py              # BenchmarkResult, Product, Category
├── k6/
│   └── benchmark.js           # k6 load test with comparison table
├── docker-compose.yml         # PostgreSQL + ASGI + WSGI
├── Dockerfile                 # Multi-stage build
└── Makefile                   # All convenience commands
```

## Key Takeaway

> **Async is not a silver bullet.** It shines for I/O-bound work
> (external APIs, concurrent DB queries) but does nothing for
> CPU-bound tasks. Choose based on your workload.
