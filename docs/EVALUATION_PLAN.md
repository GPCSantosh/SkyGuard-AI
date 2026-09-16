# SkyGuard AI — Evaluation Plan (Synthetic Fault Benchmarking)

## 1. Evaluation Methodology
Because real-world AWS sensor faults are sparse and irregularly labeled, SkyGuard AI adopts a **controlled synthetic injection evaluation methodology**.

1. **Clean Baseline Dataset**: Select high-quality, verified historical AWS series across diverse climate zones in India (arid, coastal, montane, tropical).
2. **Controlled Fault Injection**: Inject parameterized synthetic anomalies into the clean series.
3. **Double-Blind Detection**: Run the complete SkyGuard detection pipeline on the corrupted series without passing fault metadata.
4. **Scoring & Metric Computation**: Compare pipeline detections against the isolated ground-truth labels.

---

## 2. Injected Fault Categories & Parameters

| Fault Category | Injection Method | Target Parameters | Evaluation Focus |
|---|---|---|---|
| **Single Spike** | Add $+k \cdot \sigma$ impulse to $t$ | $T$, $P$, $RH$ | Instantaneous spike recall without false positives on adjacent steps |
| **Small Spike** | Add low magnitude ($+1.5\sigma$) impulse | $T$, $P$, $RH$ | Sensitivity of residual filters |
| **Long Spike / Pulse** | Sustained offset over 3–5 consecutive steps | $T$, $P$, $RH$ | Distinguishing multi-step glitch from weather front |
| **Gradual Drift** | Linear slope $\beta \cdot (t - t_0)$ added over 12–72h | $T$, $P$, $RH$ | Early detection latency before catastrophic drift |
| **Sensor Offset** | Step jump $+C$ maintained indefinitely | $T$, $P$, $RH$ | Offset identification & recalibration flag |
| **Frozen Value** | Replace readings with constant value for $N$ steps | $T$, $P$, $RH$ | Flatline detection during diurnal cycle |
| **Intermittent Freeze** | Alternating valid readings with frozen slices | $T$, $P$, $RH$ | Fragmented pattern detection |
| **Missing Records** | Drop observation packets (burst / random) | All | Detection of missing telemetry windows |
| **Multivariate Inconsistency**| Artificially set $RH=100\%$ while increasing $T$ | $T \times RH$ | Physical constraint violation detection |
| **Genuine Extreme Weather** | Inject valid steep meteorological gradient (squall) | $T, P, RH$ correlated | **FPR Check**: Verify system DOES NOT classify valid event as sensor failure |

---

## 3. Evaluation Metrics

### 3.1. Classification & Detection Metrics
- **Precision**: $\text{TP} / (\text{TP} + \text{FP})$ — minimizing false alarms for AWS maintenance crews.
- **Recall (Sensitivity)**: $\text{TP} / (\text{TP} + \text{FN})$ — ensuring no critical sensor failure goes undetected.
- **$F_1$ Score & $F_2$ Score**: Weighted harmonic mean prioritizing recall in critical operational deployments.
- **False Positive Rate (FPR)**: Rate of false alarms during clean historical periods.
- **False Negative Rate (FNR)**: Missed anomalies.

### 3.2. Operational & Latency Metrics
- **Detection Latency**: Number of observation steps (or minutes) elapsed between fault onset and first detection alert.
- **Processing Latency**: Milliseconds required per observation in the end-to-end QC and ML pipeline.
- **Imputation Error (RMSE / MAE)**: Accuracy of recommended corrected values compared against true clean baseline.

---

## 4. Implemented Evaluation Framework (Phase 3)
Phase 3 establishes an anti-leakage evaluation harness:
- **Chronological Partitioning**: `ChronologicalSplitter` in `ml/evaluation/splitting.py` splits data past $\rightarrow$ future (Train 60%, Val 20%, Test 20%) with zero label or feature contamination.
- **Dual Metric Computation**: `ml/evaluation/metrics.py` calculates both observation-level (Precision, Recall, F1, FPR, FNR, PR-AUC, ROC-AUC) and event-level (Episode Recall, Detection Latency in steps/minutes, False Alarms per station-day).
- **Comprehensive Evaluation**: `ModelEvaluator` in `ml/evaluation/evaluator.py` decomposes evaluation across all 15 taxonomy classes, severity buckets (subtle, moderate, obvious), and dedicated genuine extreme weather false alarm tracking.

---

## 5. Benchmark Execution Commands
To execute the baseline benchmark, ablation study, and stability verification:

```bash
# 1. Main Baseline Experiment (Fixed Threshold, Rolling Z-Score, Isolation Forest)
python -m ml.experiments.runner --dataset data/processed/42182099999_2024_normalized.csv --seed 42

# 2. Feature Set Ablation Study (Set A, Set B, Set C, Set D)
python -c "from ml.experiments.ablation import run_ablation_study; run_ablation_study('data/processed/42182099999_2024_normalized.csv')"

# 3. Multi-Seed Stability Verification (Seeds 42, 123, 2026)
python -c "from ml.experiments.stability import run_multi_seed_stability; run_multi_seed_stability('data/processed/42182099999_2024_normalized.csv')"
```

