# SkyGuard AI — Hackathon Demonstration & Presentation Runbook

> **Target Demonstration Duration:** 8 – 12 Minutes  
> **Authoritative Baseline:** Phase 13B Hardened Release  
> **Mode Classification:** Dual Mode (`LIVE` vs `DEMO REPLAY`)  

---

## 1. 30-Second Executive Pitch
> *"Every meteorological agency relies on Automatic Weather Stations (AWS) to predict extreme weather, cyclones, and heatwaves. But when a sensor degrades or spikes, classical QC either lets corrupted data poison numerical models or misclassifies genuine violent storms as sensor failures.  
> **SkyGuard AI** is a real-time meteorological data quality and anomaly detection platform that combines Machine Learning, TreeSHAP explainability, and geodesic spatial consensus. It detects isolated sensor faults in milliseconds while strictly protecting genuine regional extreme events—without ever mutating raw historical observations."*

---

## 2. System Architecture in 60 Seconds
```
                       ┌──────────────────────────────────────────────┐
                       │           INCOMING TELEMETRY STREAM          │
                       │   (Live Open-Meteo API or Replay Dataset)    │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                         ┌─────────────────────────────────────────┐
                         │   LIVE SOURCE QUALIFICATION & GATE      │
                         │ (Freshness, Cadence, Upstream Outages)  │
                         └────────────────────┬────────────────────┘
                                              │
                                              ▼
                         ┌─────────────────────────────────────────┐
                         │       FEATURE ENGINEERING (CAUSAL)      │
                         │   Rolling Lags, Lapse-Adjusted Context  │
                         └────────────────────┬────────────────────┘
                                              │
                                              ▼
                         ┌─────────────────────────────────────────┐
                         │        HYBRID DECISION ENGINE           │
                         │  Statistical + TreeSHAP + Geodesic Cons.│
                         └──────────────┬───────────────────┬──────┘
                                        │                   │
                     ┌──────────────────┴───┐       ┌───────┴─────────────────┐
                     ▼                      ▼       ▼                         ▼
             [NORMAL WEATHER]     [PROBABLE SENSOR FAULT]            [GENUINE REGIONAL STORM]
             Passed to Model      • TreeSHAP Evidence                • 85% Consensus Shield
                                  • Sensor Health Score -25%         • Health Score Protected
                                  • Imputation Overlay               • Raw Data Preserved
```

---

## 3. Operating Modes & Live Fallback Protocol

SkyGuard AI explicitly segregates operating telemetry into two strictly labeled modes:

| Mode | Telemetry Source | Provenance Label | Use Case |
| :--- | :--- | :--- | :--- |
| **LIVE MODE** | Real-time Open-Meteo REST Poller | `LIVE (OPEN-METEO)` | Real-world Indian AWS network monitoring |
| **DEMO REPLAY MODE** | Deterministic Frozen Narrative Dataset (`seed=42`) | `DEMO REPLAY` | Controlled 8–12 min hackathon demonstration |

### Live Fallback Procedure
If the conference venue experiences Wi-Fi loss or upstream rate limits:
1. The dashboard immediately displays: `[LIVE SOURCE UNAVAILABLE]`.
2. Click **"Switch to Demo Replay Mode"** in the top operations bar or network overview banner.
3. The system transitions cleanly without crashing or faking live labels.

---

## 4. Step-by-Step Presenter Script (8–12 Min Narrative)

### Act I: Nominal Network State (Minutes 0:00 – 2:00)
1. **Action:** Open Dashboard (`http://localhost:5173/network`). Click **"Reset Demo"** in the Demo Controller bar.
2. **Presenter Script:**
   > *"Here is the SkyGuard Network Operations Center monitoring 8 Automatic Weather Stations across India (Safdarjung, Lodhi Road, Palam, Mumbai, Chennai, Kolkata, Nagpur, Jodhpur). All stations are reporting nominal temperatures (28–34°C) with healthy sensor scores of 100/100 and clean pipeline latency of under 5 ms."*
3. **Key Visual:** Green status badges, healthy Leaflet GIS map, 0 active anomalies.

### Act II: Isolated Hardware Sensor Spike (Minutes 2:00 – 4:30)
1. **Action:** Select **"Isolated Hardware Spike"** scenario (or click **"Step Cycle"** 2 times).
2. **Presenter Script:**
   > *"At Step 8, Station `42182099999` (New Delhi Safdarjung) suddenly reports 52.5°C—a sudden +18.5°C jump. Watch how SkyGuard responds."*
3. **Action:** Navigate to **Anomaly Investigation Page** (`/anomalies/latest`).
4. **Presenter Script:**
   > *"SkyGuard immediately flags `PROBABLE_SENSOR_ANOMALY`. Why? Look at the Spatial Evidence Panel: neighboring stations (Palam, Lodhi Road, Gurgaon) report 33.2°C. The TreeSHAP explainability plot highlights temperature rate-of-change and spatial divergence as the primary drivers. The sensor health index drops from 100 to 75, triggering a maintenance warning."*
5. **Key Visual:** TreeSHAP waterfall plot, spatial neighborhood divergence table, sensor health degradation chart.

### Act III: Non-Destructive Advisory Imputation (Minutes 4:30 – 6:00)
1. **Action:** Navigate to **Correction / Imputation View** (`/corrections`).
2. **Presenter Script:**
   > *"Critical architectural principle: SkyGuard **never** overwrites raw sensor telemetry. In our audit ledger, the original 52.5°C observation remains immutable. Instead, SkyGuard generates a separate advisory overlay: an Inverse Distance Weighted (IDW) estimate of 33.1°C with a ±0.8°C confidence bound. Downstream consumers can choose to consume raw or validated feeds."*
3. **Key Visual:** Side-by-side comparison of immutable raw value vs recommended advisory value.

### Act IV: Severe Regional Squall Front (Genuine Event Shield) (Minutes 6:00 – 8:30)
1. **Action:** Select **"Regional Squall Front"** scenario and step forward.
2. **Presenter Script:**
   > *"Now, let's test the hardest problem in meteorological quality control: a sudden violent squall or convective thunderstorm. Across Northern India, 6 nearby stations experience a dramatic 12°C temperature drop and 35% humidity spike within 10 minutes.*  
   > *Traditional thresholding algorithms would flag all 6 stations as sensor failures and discard the storm.*  
   > *SkyGuard’s Spatial Consensus Engine detects an 85% spatial agreement across neighbors. It classifies the event as `POSSIBLE_GENUINE_EVENT`, protecting the severe weather alert for civil defense while applying **zero** penalty to station hardware health."*
3. **Key Visual:** Multi-station synchronized telemetry curves, `POSSIBLE_GENUINE_EVENT` classification badge.

### Act V: Live Source Outage vs Sensor Health Decoupling (Minutes 8:30 – 10:00)
1. **Action:** Navigate to **Live Source Health** (`/system`).
2. **Presenter Script:**
   > *"What happens if the telecommunications backhaul or upstream API drops? In SkyGuard, source outage episodes are decoupled from physical sensor health. When an upstream feed disconnects, the Source Health State Machine transitions from `HEALTHY` -> `DEGRADED` -> `DISCONNECTED`, logging an outage incident without corrupting individual station hardware reputations."*
3. **Key Visual:** State Machine transition diagram and outage incident log.

### Act VI: Evidence & Scientific Provenance (Minutes 10:00 – 11:30)
1. **Action:** Click **"EVIDENCE"** in the top navigation bar.
2. **Presenter Script:**
   > *"SkyGuard is built on rigorous scientific integrity. Every number on this screen is backed by a frozen evaluation artifact: an F1 score of 0.963 across 5,760 observations, a verified zero-leakage causal pipeline, and 339 automated passing tests."*
3. **Key Visual:** Evidence & Audit Modal showing benchmark table and reproducibility manifest.

---

## 5. Technical Claims Discipline Table

| Claim | Result | Evidence Type | Authoritative Source | Scope & Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **Hybrid Benchmark F1** | **0.963** | Scientific Benchmark | `evaluation/final_results.json` | Synthetic & scenario benchmark dataset |
| **Sensor Anomaly Precision** | **0.978** | Scientific Benchmark | `docs/FINAL_EVALUATION_REPORT.md` | Extreme spikes & step jumps |
| **Regional Event Recall** | **0.949** | Scientific Benchmark | `docs/FINAL_EVALUATION_REPORT.md` | Coherent multi-station squalls |
| **Live API Processing** | **100% Pass** | Live Validation | `docs/LIVE_VALIDATION_REPORT.md` | Controlled live Open-Meteo cycles |
| **Automated Test Suite** | **339 Passing** | Engineering Verification | `pytest tests/unit tests/integration` | Repository CI/CD environment |
| **Pipeline Latency (P95)** | **3.42 ms** | Performance Benchmark | `evaluation/final_results.json` | Single-node local execution |

---

## 6. Pre-Demo Verification & Health Check SOP

Run the automated one-command health check before taking the stage:
```bash
python demo/scripts/demo_health_check.py
```
**Expected Output:**
```
========================================================================
 SKYGUARD AI - PRE-DEMO COMPREHENSIVE INTEGRITY & HEALTH CHECK 
========================================================================
 [PASS] Python Core Dependencies                      Python 3.13.15
 [PASS] Spatial Topology & Repository                 8 stations active
 [PASS] Real-Time Processing Engine                   Hybrid Decision Engine loaded
 [PASS] Demo Replay Scenarios                         4 scenarios registered
 [PASS] Frozen Scientific Benchmark                   Recall=1.000 verified
 [PASS] ML Baseline Model Weights                     Isolation Forest weights verified
 [PASS] Live Open-Meteo Poller Config                 8 stations configured
 [PASS] Frontend Production Bundle                    dist/index.html verified
 [PASS] Authoritative Technical Documentation         All 4 Phase 13A specs present
========================================================================
 PRE-DEMO HEALTH CHECK: ALL SYSTEMS GO (100% PASS) 
========================================================================
```

---

## 7. Emergency Recovery Procedures

### Scenario A: Backend API Crash / Terminated
```bash
# Restart backend on port 8000
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Scenario B: Database Locked / Contaminated Transient State
Click **"Reset Demo"** in the web UI, or execute:
```bash
python -c "from backend.app.api.v1.deps import get_replay_engine; get_replay_engine().reset()"
```

### Scenario C: Frontend Port Conflict
```bash
cd frontend
npm.cmd run dev -- --port 5173
```
