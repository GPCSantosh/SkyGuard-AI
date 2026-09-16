# SkyGuard AI — Explainable AI & Anomaly Investigation Specification (Phase 6A)

## 1. Executive Summary & Purpose
When the SkyGuard Hybrid Decision Engine produces an operational decision (`NORMAL`, `POSSIBLE_GENUINE_EVENT`, `PROBABLE_SENSOR_ANOMALY`, `PROBABLE_DATA_QUALITY_ISSUE`, `UNCERTAIN`), operators and meteorological engineers must understand precisely **why** the decision was reached.

The Explainability layer synthesizes:
1. **TreeSHAP Feature Contributions**: Local feature attributions from the unsupervised Isolation Forest model.
2. **Strictly Causal Neighbor Comparisons**: Median departure, spatial consensus, and temporal alignment across active regional AWS stations.
3. **Episode Timeline Reconstruction**: Baseline $\rightarrow$ onset $\rightarrow$ peak $\rightarrow$ recovery dynamics.
4. **Deterministic Reason Code Mapping**: Operational translation connecting Phase 5 reason codes with domain physics.
5. **Separated Evidence Hierarchy**: Clear 4-tier separation avoiding confusion between raw sensor telemetry, statistical model scores, and operational interpretations.

```
                                  Observation Telemetry
                                            │
                                            ▼
                           ┌──────────────────────────────────┐
                           │   Hybrid Decision Engine         │
                           │   (Data Quality, ML, Temporal,   │
                           │    Spatial, Multivariate Rules)  │
                           └─────────────────┬────────────────┘
                                             │
                                             ▼
                                      HybridDecision
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │
                       ▼                                           ▼
          ┌──────────────────────────┐               ┌──────────────────────────┐
          │  TreeSHAP Explainer      │               │  Causal Neighbor         │
          │  (Isolation Forest Attrib│               │  Comparator              │
          └────────────┬─────────────┘               └─────────────┬────────────┘
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────┐
                              │  Explanation Synthesizer    │
                              │  & Evidence Hierarchy       │
                              └──────────────┬──────────────┘
                                             │
                                             ▼
                                     ExplanationSummary
```

---

## 2. Evidence Hierarchy Taxonomy

To eliminate ambiguity, SkyGuard maintains a strict **4-tier Evidence Hierarchy**:

| Tier | Category | Contents & Data Sources |
|---|---|---|
| **Tier 1** | **Direct Evidence** | Measured sensor readings, timestamps, raw contemporaneous neighbor readings, station identifiers. |
| **Tier 2** | **Model Evidence** | Raw model score, continuous normalized anomaly score $[0, 1]$, calibrated threshold, and ranked TreeSHAP feature attributions. |
| **Tier 3** | **Contextual Evidence** | Spatial consensus ratios, active neighbor counts, rate-of-change ($\Delta X / \text{min}$), consecutive unchanged counts, flatline durations, and thermodynamic consistency. |
| **Tier 4** | **Operational Interpretation** | Standard operational classification: `nominal observation`, `possible regional event`, `probable sensor anomaly`, `probable data quality issue`, or `uncertain`. |

---

## 3. TreeSHAP on Isolation Forest

### 3.1. Mathematical Foundation
In scikit-learn's `IsolationForest`, anomalies are isolated near the root of random trees, resulting in a shorter average path length $h(x)$.
SHAP `TreeExplainer` computes local feature contributions $\phi_i(x)$ to the expected path length:
$$E[h(x)] = \phi_0 + \sum_{i=1}^M \phi_i(x)$$

When an observation is an anomaly, its path length is substantially shorter than expected ($h(x) \ll E[h]$). Therefore:
- A **negative** contribution to path length $\phi_i(x) < 0$ means the feature accelerates isolation, **increasing the anomaly score**.
- We define the **Anomaly Contribution**:
  $$\text{Contribution}_i(x) = -\phi_i(x)$$
- Direction is classified as:
  - `increases_anomaly` if $\text{Contribution}_i > 10^{-4}$
  - `decreases_anomaly` if $\text{Contribution}_i < -10^{-4}$
  - `neutral` otherwise.

### 3.2. Structured Feature Contribution Format
Every explained feature contribution contains:
```json
{
  "feature_name": "temperature_rate_of_change",
  "feature_value": 1.8,
  "contribution": 0.21,
  "direction": "increases_anomaly",
  "rank": 1
}
```

### 3.3. Faithful Baseline Fallback
For non-tree baseline models (such as `RollingZScoreDetector` or `FixedThresholdDetector`), or when TreeSHAP is unavailable, the system uses a transparent fallback calculating normalized parameter deviations rather than fabricating unverified SHAP numbers. The method is explicitly declared in `audit_metadata.explanation_method` (`TREE_SHAP` vs `FEATURE_DEVIATION_FALLBACK`).

---

## 4. Reason Code Mapping & Human-Readable Synthesis

| Reason Code | Domain Meaning | Explanation Synthesis Signature |
|---|---|---|
| `LOCAL_SPATIAL_ISOLATION` | Single-station anomaly while network is stable | Highlights local departure from neighbor median and absence of regional corroboration. |
| `REGIONAL_SPATIAL_AGREEMENT` | Network-wide atmospheric front or squall | Highlights multi-station consensus; uses scientific language: *"evidence is consistent with a regional event."* |
| `PERSISTENT_VALUE` | Sensor stuck / zero variance flatline | Identifies consecutive unchanged count and duration in minutes. |
| `MULTIVARIATE_DEVIATION` | August-Roche-Magnus thermodynamic breach | Identifies joint contradiction between $T$, $RH$, and $T_d$. |
| `DATA_GAP` | Telemetry link packet interruption | Identifies gap duration in minutes and recommends checking telemetry/logger queue. |
| `OUT_OF_RANGE_PHYSICAL` | Planetary bounds breach | Cites thermodynamic surface limits on Earth and recommends immediate electrical check. |
| `INSUFFICIENT_SPATIAL_CONTEXT` | Isolated station without active neighbors | Explicitly identifies sparse spatial context backing an `UNCERTAIN` decision. |

---

## 5. Anomaly Episode Timeline Reconstruction

Given a chronological history around an anomaly event, `AnomalyEpisodeReconstructor` tracks:
- **Preceding Normal Baseline**: Observations leading up to onset.
- **Onset Timestamp**: Earliest continuous timestamp crossing anomalous threshold.
- **Peak Timestamp**: Point of maximum anomaly score or largest physical deviation.
- **Recovery Timestamp**: Point where station returns to normal baseline.
- **Duration**: Total active elapsed minutes $(t_{\text{recovery}} - t_{\text{onset}})$.
- **Neighbor Context**: Mean, min, and max readings of adjacent AWS stations across the episode window.

---

## 6. Strictly Causal Neighbor Comparison

`NeighborComparator` evaluates spatial consistency under strict causal ordering:
- Only neighbor observations at timestamps $t_{\text{neighbor}} \le t_{\text{target}}$ within the synchronization window (e.g. 15 minutes) are considered.
- Computes:
  - `target_value`
  - `neighbor_values` mapping
  - `neighbor_median`
  - `target_deviation` $= X_{\text{target}} - \text{median}(X_{\text{neighbors}})$
  - `agreeing_neighbor_count` within meteorological tolerance (e.g. $\pm 2.0^\circ\text{C}$).

---

## 7. Auditability & Reproducibility

Every `ExplanationSummary` contains an immutable `AuditMetadata` block:
```json
{
  "model_version": "isolation_forest_v1",
  "feature_version": "v1.0.0",
  "decision_engine_version": "hybrid_v1.0.0",
  "explanation_engine_version": "xai_v1.0.0",
  "explanation_method": "TREE_SHAP",
  "input_station_id": "AWS_001",
  "input_timestamp": "2026-09-17T12:00:00Z",
  "generated_at": "2026-09-17T00:26:00Z"
}
```
All summary generation is deterministic: identical models, features, evidence, and configuration will yield identical text summaries and rankings.

---

## 8. Semantic Quality Evaluation

`ExplanationSemanticEvaluator` automatically audits generated explanations across synthetic anomaly classes:
- **Spike**: Confirms presence of rate-of-change, deviation, or spike keywords.
- **Frozen Sensor**: Confirms persistence, flatline, unchanged, or zero variance keywords.
- **Drift**: Confirms drift, offset, departure, or residual keywords.
- **Regional Event**: Confirms regional corroboration, multi-station consensus, and cautious phrasing.
- **Data Gap**: Confirms missingness, packet gap, or telemetry communication keywords.

---

## 9. Scientific Language Standards

SkyGuard enforces rigorous scientific communication rules:
- **No Causal Overreach**: We never write *"SHAP proves the sensor is faulty."* Instead, we state: *"SHAP identifies the model features that contributed most to the anomaly score."*
- **No Certainty Overreach**: We never state *"event is definitely genuine."* We write: *"evidence is consistent with a regional event."*
- **Explainable Uncertainty**: `UNCERTAIN` decisions must never be an unexplained fallback; the exact conflicting or sparse subsystem evidence is explicitly declared.
