# SkyGuard AI — Production Deployment & Runtime Architecture

## 1. Overview & Architecture Blueprint

SkyGuard AI's production architecture is designed for high availability, deterministic schema migrations, seamless WebSocket stream ingestion, and zero-loss restart recovery. The system uses a multi-container topology orchestrated via Docker Compose or Kubernetes.

```mermaid
graph TD
    Client[Web Browser / AWS Operator] -->|HTTP :80 / HTTPS :443| Ingress[Nginx Reverse Proxy]
    Client -->|WebSocket /ws/stream| Ingress

    subgraph "SkyGuard Container Network (skyguard-net)"
        Ingress -->|Static SPA / Assets| FrontendStatic[Compiled React Bundle]
        Ingress -->|REST API Ingress /api/*| Backend[FastAPI Backend :8000]
        Ingress -->|WS Upgrade /ws/stream| Backend
        Ingress -->|Health Probes /health/*| Backend

        MigrationRunner[Alembic Migration Container] -->|1. alembic upgrade head| DB[(PostgreSQL 16 Engine)]
        Backend -->|2. Connection Pool (10/20)| DB
        Backend -->|Poll Telemetry / Outage FSM| LiveSource[External AWS / Open-Meteo API]
    end
```

---

## 2. Containerized Services & Network Topology

| Service | Container Name | Image / Base | Internal Port | External Port | Healthcheck |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | `skyguard-postgres` | `postgres:16-alpine` | `5432` | `5432` (configurable) | `pg_isready -U <user> -d <db>` |
| **Migration** | `skyguard-migration` | `Dockerfile.backend` | N/A (One-off) | None | Exits 0 on migration success |
| **Backend** | `skyguard-backend` | `Dockerfile.backend` | `8000` | `8000` | `curl -f http://localhost:8000/health/ready` |
| **Frontend/Proxy** | `skyguard-frontend` | `Dockerfile.frontend` | `80` | `80` (or `3000`) | `wget -qO- http://localhost/health/live` |

---

## 3. Environment Configuration & Secret Separation

Application configuration is strictly isolated from credentials and secrets:

### Application Configuration (Public / Non-sensitive)
- `SKYGUARD_ENV`: Environment identifier (`production`, `staging`, `development`).
- `SKYGUARD_LOG_LEVEL`: Logging verbosity (`INFO`, `WARNING`, `DEBUG`).
- `SKYGUARD_LOG_FORMAT`: `json` (for Docker/Kubernetes aggregators) or `text`.
- `SKYGUARD_OBSERVATION_INTERVAL_SECONDS`: Cadence (default: `300` seconds / 5 min).
- `SKYGUARD_AUTO_MIGRATE`: `false` in production (migrations handled by container step).
- `SKYGUARD_CORS_ORIGINS`: Allowed web origins (`["http://localhost", "https://skyguard.gov.in"]`).
- `SKYGUARD_LIVE_SOURCE_ENABLED`: Toggle for live external meteorological ingestion (`true`/`false`).
- `SKYGUARD_LIVE_SOURCE_PROVIDER`: Provider identifier (`open_meteo`).

### Secrets & Operational Security (Sensitive / Encrypted / Injected)
- `POSTGRES_PASSWORD`: Secret database password.
- `SKYGUARD_DATABASE_URL`: Full PostgreSQL connection string (`postgresql://skyguard_user:PASSWORD@postgres:5432/skyguard_ai`).
- `SKYGUARD_LIVE_SOURCE_API_KEY`: API token for authenticated weather feeds.
- `SKYGUARD_OPERATIONAL_API_KEY`: Secret key required to execute manual administrative triggers (`POST /api/v1/live/poll-now`).

---

## 4. Controlled Migration Execution Strategy

In production, application worker replicas do **not** run migrations on startup. This prevents race conditions and corrupted schema states.

### Startup Pipeline:
```mermaid
sequenceDiagram
    autonumber
    participant Compose as Orchestrator / CI
    participant DB as PostgreSQL
    participant Mig as skyguard-migration
    participant App as skyguard-backend
    participant Proxy as skyguard-frontend

    Compose->>DB: Start Database Container
    DB-->>Compose: Healthcheck passing (pg_isready)
    Compose->>Mig: Launch Migration Runner
    Mig->>DB: Execute 'alembic upgrade head'
    DB-->>Mig: Migration 001_initial applied
    Mig-->>Compose: Exits with Code 0
    Compose->>App: Launch Backend API Container
    App->>DB: Connect via Connection Pool
    App-->>Compose: Healthcheck passing (/health/ready)
    Compose->>Proxy: Launch Reverse Proxy / UI
    Proxy-->>Client: Ready to serve traffic
```

### Rollback Strategy:
To rollback a schema change safely:
1. Stop the application backend: `docker compose stop backend`
2. Run target downgrade: `docker compose run --rm backend alembic downgrade <target_revision>`
3. Deploy the previous compatible backend image.

---

## 5. Operational Health & Readiness Probes

### `GET /health/live` (Liveness Probe)
- **Purpose**: Verifies that the Python process and event loop are responsive.
- **Contract**: Returns HTTP `200 OK` with `{ "status": "alive", "uptime_seconds": 120.5 }`.
- **Failure**: Process freeze, deadlock, or unhandled crash.

### `GET /health/ready` (Readiness Probe)
- **Purpose**: Evaluates end-to-end readiness across database, application engine, live source, and WebSocket managers.
- **Contract**:
  ```json
  {
    "status": "ready",
    "timestamp": "2026-09-17T12:00:00Z",
    "dependencies": {
      "application": { "status": "healthy", "stations_monitored": 8 },
      "database": { "status": "healthy", "type": "postgresql", "persistence_degraded": false },
      "live_source": { "status": "healthy", "enabled": true },
      "websocket": { "status": "healthy", "active_connections": 4 }
    }
  }
  ```
- **Degradation Tolerance**: Transient external source outages or non-fatal persistence delays return HTTP `200 OK` with `"status": "degraded"`. Process is not terminated prematurely.

---

## 6. Reverse Proxy & WebSocket Ingress

Nginx terminates client HTTP and WebSocket traffic:
- **WebSocket Route**: `/ws/` routes to `backend:8000` with `Upgrade: websocket` and `Connection: Upgrade` headers. Read timeout is set to `86400s` (24 hours).
- **REST API Route**: `/api/` proxies upstream with original host and `X-Forwarded-For` client headers.
- **Security Headers**: HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, and `Referrer-Policy: strict-origin-when-cross-origin`.

---

## 7. PostgreSQL Backup & Disaster Recovery Runbook

### Automated Logical Backups
Execute regular logical dumps via cron or container sidecar:
```bash
# Full Database Logical Dump
docker exec -t skyguard-postgres pg_dump -U skyguard_user -d skyguard_ai -Fc > /backups/skyguard_ai_$(date +%Y%m%d_%H%M%S).dump

# Prune dumps older than 30 days
find /backups -name "skyguard_ai_*.dump" -mtime +30 -delete
```

### Restore Procedure & Verification
```bash
# 1. Stop backend application to prevent concurrent writes
docker compose stop backend

# 2. Restore database from dump
docker exec -i skyguard-postgres pg_restore -U skyguard_user -d skyguard_ai --clean --if-exists /backups/target_backup.dump

# 3. Verify table counts and latest records
docker exec -it skyguard-postgres psql -U skyguard_user -d skyguard_ai -c "SELECT COUNT(*) FROM weather_observations; SELECT COUNT(*) FROM anomaly_events;"

# 4. Restart backend
docker compose start backend
```

---

## 8. Graceful Shutdown & Restart Semantics

On receipt of `SIGTERM` / `SIGINT`:
1. **Live Poller**: Halts scheduling of new external API cycles, permits any in-flight station request to finish (up to 5s timeout).
2. **WebSocket Manager**: Broadcasts server shutdown notice to connected clients and closes active sessions.
3. **Database Pool**: Closes active SQLAlchemy engine pool connections gracefully.
4. **Process Exit**: Process terminates with return code 0.
