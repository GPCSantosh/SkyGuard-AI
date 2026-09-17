# SkyGuard AI — Disaster Recovery & Incident Response Runbook

This runbook provides copy-paste commands and incident recovery procedures for system operators.

---

## 1. Backup Procedures

### Manual Backup Creation
Execute the disaster recovery utility inside the container or host:
```bash
python deploy/backup_restore.py backup --out backups
```
Or generate direct PostgreSQL dump:
```bash
docker exec -t skyguard-postgres pg_dump -U skyguard_user -d skyguard_ai -Fc > backups/skyguard_$(date +%Y%m%d_%H%M%S).dump
```

### Verify Backup Integrity
```bash
python deploy/backup_restore.py verify --path backups/skyguard_backup_YYYYMMDD_HHMMSS
```

---

## 2. Restore Procedures

### Clean Restore into Database Instance
```bash
python deploy/backup_restore.py restore \
  --path backups/skyguard_backup_YYYYMMDD_HHMMSS \
  --target-db "postgresql://skyguard_user:PASSWORD@postgres:5432/skyguard_ai"
```

### Direct PostgreSQL Restore
```bash
# 1. Stop backend application to prevent writes
docker compose stop backend

# 2. Restore schema and data
docker exec -i skyguard-postgres pg_restore -U skyguard_user -d skyguard_ai --clean --if-exists < backups/target_backup.dump

# 3. Restart application
docker compose start backend
```

---

## 3. Incident Recovery Procedures

### Scenario A: Backend Process Crash
1. Docker Compose will automatically restart `skyguard-backend` (`restart: unless-stopped`).
2. Verify liveness probe: `curl http://localhost:8000/health/live`
3. Verify readiness probe: `curl http://localhost:8000/health/ready`
4. Confirm single poller instance in logs: `docker compose logs -n 50 backend`

### Scenario B: Database Network Disconnection
1. Backend transitions to `persistence_degraded: true` without dropping streaming pipelines.
2. In-memory circular buffer retains observations and latest station statuses for UI queries.
3. Once database reconnects, backend automatically resumes database writes and clears degraded status.

### Scenario C: Corrupted Database / Schema Failure
1. Stop backend: `docker compose stop backend`
2. Apply restore from latest verified backup archive:
   ```bash
   python deploy/backup_restore.py restore --path backups/LATEST_BACKUP --target-db "$SKYGUARD_DATABASE_URL"
   ```
3. Run schema verification: `alembic current`
4. Restart backend: `docker compose start backend`

### Scenario D: Live Meteorological Source Outage
1. Backend `SourceHealthStateMachine` transitions `HEALTHY -> TRANSIENT_FAILURE -> DISCONNECTED`.
2. UI displays `SOURCE DISCONNECTED` badge with root cause diagnostics.
3. System logs outage duration and calculates estimated observation gap.
4. When provider recovers, state machine progresses through `WARMUP` before restoring `HEALTHY`.
