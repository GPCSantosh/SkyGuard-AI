# SkyGuard AI — Production Deployment Guide

This directory contains the production-ready deployment specifications for SkyGuard AI.

## Quickstart: Local Production-Like Environment

### 1. Configure Environment
Copy the example environment configuration:
```bash
cp .env.example .env
```
Ensure `POSTGRES_PASSWORD` and `SKYGUARD_OPERATIONAL_API_KEY` are customized for your environment.

### 2. Launch Container Stack
Start the full stack (PostgreSQL, Alembic Migration Runner, FastAPI Backend, and Nginx Frontend):
```bash
docker compose up --build -d
```

### 3. Verify Deployment
Run the automated smoke test suite:
```bash
python deploy/smoke_test.py --base-url http://localhost
```

---

## Service Endpoints & Operator URLs

- **Mission Control Dashboard**: [http://localhost](http://localhost)
- **REST API Base**: [http://localhost/api/v1](http://localhost/api/v1)
- **Interactive OpenAPI Docs**: [http://localhost/docs](http://localhost/docs)
- **Liveness Probe**: [http://localhost/health/live](http://localhost/health/live)
- **Readiness Probe**: [http://localhost/health/ready](http://localhost/health/ready)
- **WebSocket Telemetry Stream**: `ws://localhost/ws/stream`

---

## Operational Commands

### Trigger Immediate Ingestion Cycle
In production mode, manual triggers require the operational key:
```bash
curl -X POST http://localhost/api/v1/live/poll-now \
  -H "X-Operational-Key: YOUR_CONFIGURED_OPERATIONAL_KEY"
```

### View Real-Time Structured Logs
```bash
docker compose logs -f backend
```

### Execute Database Migrations Manually
```bash
docker compose run --rm migration
```

### Graceful Teardown
```bash
docker compose down
```
To also remove database volume data:
```bash
docker compose down -v
```
