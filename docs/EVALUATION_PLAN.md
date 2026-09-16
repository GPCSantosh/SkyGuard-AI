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

## 4. Benchmark Execution Command (Planned)
```bash
python scripts/run_synthetic_evaluation.py --config configs/evaluation.yaml --dataset data/raw/historical_sample.csv
```
*(Implementation reserved for future phases)*
