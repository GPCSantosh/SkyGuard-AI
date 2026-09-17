# SkyGuard AI — Operations Runbook & Maintenance Manual

---

## 1. System Overview & Operator Responsibilities

This runbook provides standard operating procedures (SOPs), system administration guides, health inspection workflows, and disaster recovery instructions for meteorological operators, field engineers, and DevOps personnel managing SkyGuard AI.

### Core Operator Responsibilities
1. **Network Monitoring**: Continuous observation of station status, telemetry latency, and live source health.
2. **Anomaly Triage**: Investigating detected anomaly events, reviewing TreeSHAP attributions, and validating genuine regional storms.
3. **Maintenance Dispatch**: Scheduling field inspections for stations exhibiting degrading longitudinal sensor health.
4. **Data Recovery & Imputation**: Auditing and approving recommended non-destructive value corrections.
5. **System Maintenance**: Executing scheduled database backups, monitoring API quotas, and performing rolling software updates.

---

## 2. Service Management & CLI Commands

### 2.1. Starting the Platform
```bash
# A. Local Development Mode (Backend + Frontend)
# Terminal 1 - Backend (FastAPI + WebSocket Stream)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Frontend Operations Console
cd frontend
npm.cmd run dev -- --host 0.0.0.0 --port 5173

# B. Production Docker Deployment
docker-compose up -d --build
```

### 2.2. Health Check & Diagnostics
```bash
# 1. System API Health Check
curl -s http://localhost:8000/health | jq .

# 2. Live Weather API Qualification Smoke Test
python scripts/smoke_test_live_api.py --mock
python scripts/smoke_test_live_api.py --live

# 3. Comprehensive Evaluation Runner
python scripts/run_final_evaluation.py --seed 42
```

---

## 3. Standard Operating Procedures (SOPs)

### SOP-01: Triage Anomaly Alert (`PROBABLE_SENSOR_ANOMALY`)
1. Open the **SkyGuard Operations Console** at `http://localhost:5173`.
2. Locate the flagged station on the **Network Map** (highlighted in Orange/Red).
3. Click the alert to open the **Anomaly Investigation Drawer**:
   - Check the **Gate Activated** (e.g. Gate 5: Spatial-ML Synergy Arbiter).
   - Check the **Top Feature Contributions** (e.g. `temp_rate_of_change` $+5.2\sigma$).
   - Check the **Neighbor Comparison**: Verify whether adjacent stations show similar trends or contradict the target reading.
4. If neighbor stations contradict the reading $\rightarrow$ Confirm sensor fault; dispatch maintenance crew.
5. If neighbor stations show identical steep gradients $\rightarrow$ Verify why regional consensus was not reached; override alert if a micro-climate storm is physically confirmed.

### SOP-02: Review Genuine Extreme Weather (`POSSIBLE_GENUINE_EVENT`)
1. When severe weather (squalls, convective storms, heatwaves) impacts multiple network nodes, SkyGuard emits `POSSIBLE_GENUINE_EVENT` (Blue status).
2. **Action Required**:
   - Confirm spatial consensus ($\ge 70\%$).
   - Do NOT mark sensor as faulty.
   - Do NOT apply health penalties.
   - Forward real-time observations to downstream numerical weather prediction (NWP) models.

### SOP-03: Investigate Longitudinal Sensor Health Degradation
1. Access the **Sensor Health Matrix** in the dashboard.
2. If overall health drops into `ATTENTION` ($50-74$) or `DEGRADED` ($25-49$):
   - Review the 5 component scores (`anomaly_health`, `dq_health`, `comm_health`, `temporal_health`, `spatial_health`).
   - Identify the deteriorating subsystem:
     - **Low `spatial_health`** $\rightarrow$ Sensor calibration drift ($+2-4^\circ\text{C}$ systematic offset).
     - **Low `temporal_health`** $\rightarrow$ Mechanical sticking / intermittent flatlines.
     - **Low `dq_health`** $\rightarrow$ Intermittent cable disconnection or packet corruption.
3. Generate maintenance work order with the recommended SOP action (`INSPECT` or `PRIORITY_INSPECTION`).

---

## 4. Live Source Health & Feed Recovery

### Source Health States & Operator Actions

| State | Indicator | Root Cause | Automatic Action | Operator Action |
| :--- | :---: | :--- | :--- | :--- |
| **`HEALTHY`** | Green | Normal HTTP 200 OK; latency $< 500$ms | Nominal processing | None |
| **`DEGRADED`** | Yellow | 1–2 poll failures or latency $> 2000$ms | Poller retries with exponential backoff | Monitor logs; check network bandwidth |
| **`STALE`** | Amber | Feed active but timestamps $> 30$min old | Station flagged as STALE in UI | Check upstream telemetry provider feed |
| **`DISCONNECTED`** | Red | $\ge 3$ consecutive network failures | Outage episode opened; loss tracked | Verify gateway IP, DNS, and firewall rules |
| **`RATE_LIMITED`** | Red | HTTP 429 Too Many Requests | Backoff until quota reset window | Adjust polling frequency or upgrade API tier |
| **`AUTH_ERROR`** | Red | HTTP 401 / 403 Invalid API Key | Ingestion paused | Update API credentials in `.env` |

---

## 5. Persistence, Backup & Disaster Recovery

### 5.1. Database Schema Migrations (Alembic)
```bash
# Check current migration version
alembic current

# Run pending migrations
alembic upgrade head

# Rollback single migration
alembic downgrade -1
```

### 5.2. Backup Execution
```powershell
# Execute automated database backup
python scripts/backup_database.py --backup-dir ./backups
```
- Creates timestamped, gzip-compressed snapshot: `backups/skyguard_backup_YYYYMMDD_HHMMSS.sql.gz`.
- Computes SHA256 checksum manifest to guarantee backup integrity.

### 5.3. Disaster Recovery / Database Restore
```powershell
# Restore from verified backup snapshot
python scripts/restore_database.py --backup-file ./backups/skyguard_backup_20260917_120000.sql.gz --verify-checksum
```
- Restores database schema, historical observations, and anomaly audit logs in $< 10$ seconds.

---

## 6. Incident Response & Troubleshooting Matrix

| Symptom | Probable Cause | Diagnostic Command | Remediation |
| :--- | :--- | :--- | :--- |
| **Dashboard disconnected (Offline badge)** | Backend server down or WebSocket port blocked | `curl http://localhost:8000/health` | Restart backend service; verify port 8000 open |
| **Live feed showing STALE status** | Upstream provider not updating timestamps | `python scripts/smoke_test_live_api.py --live` | Check provider status page; restart live poller |
| **High pipeline latency ($> 50$ms)** | SQLite lock contention or large unindexed queries | `python -m tests.performance.test_20_station_load` | Migrate to PostgreSQL; verify DB indexes |
| **Zero anomalies detected during test** | Threshold configuration mismatch | `pytest tests/unit/test_decision_engine.py` | Verify `configs/hybrid_decision.yaml` thresholds |
| **Database write errors / disk full** | Volume space exhausted | `df -h` or `Get-PSDrive` | Prune old logs; verify retention pruning policy |
