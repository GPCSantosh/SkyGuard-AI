# SkyGuard AI — Machine Learning Specification

## 1. Machine Learning Strategy & Philosophy
SkyGuard AI uses a **hybrid intelligence architecture**:
$$\text{Quality Decision} = \text{Meteorological Physics Rules} \oplus \text{Unsupervised ML Models} \oplus \text{Spatial Consistency Context}$$

Pure machine learning alone can fail on meteorological edge cases, and deterministic rules alone cannot capture subtle multivariate sensor drifts. Combining them yields a resilient, explainable system.

---

## 2. Feature Engineering Pipeline (Planned Architecture)

### 2.1. Temporal Features (Sliding Windows)
- **Rate of Change (First Difference)**: $\Delta X_t = X_t - X_{t-1}$
- **Rolling Statistics**: Rolling Mean ($\mu_w$), Rolling Std ($\sigma_w$), Rolling Min/Max over configurable windows ($W \in \{15\text{min}, 1\text{hr}, 6\text{hr}, 24\text{hr}\}$).
- **Z-score Residuals**: $Z_t = \frac{X_t - \mu_w}{\sigma_w + \epsilon}$
- **Diurnal Signal Decomposition**: Residual after subtracting expected sinusoidal/seasonal daily cycle.
- **Autocorrelation & Run-Length Variance**: Count of consecutive unchanged values (for frozen sensor detection).

### 2.2. Spatial Neighbor Features
- **k-Nearest Neighbor Median Delta**: $\delta_{\text{spatial}} = X_{i, t} - \text{median}(\{X_{j, t} \mid j \in \text{KNN}(i)\})$
- **Inverse Distance Weighted (IDW) Expected Value**: Estimated baseline from neighboring active stations weighted by $\frac{1}{d_{ij}^2}$.

### 2.3. Multivariate Relationship Features
- **Vapor Pressure & Dew Point Deficit**: Consistency between Temperature ($T$), Pressure ($P$), and Relative Humidity ($RH$) based on the Magnus-Tetens formula.
- **Barometric Gradient vs. Temperature Inversion Index**.

---

## 3. Anomaly Detection Models (Future Pipeline)

### 3.1. Stage 1: Unsupervised Anomaly Scoring
- **Isolation Forest**: Multi-dimensional tree isolation on temporal residual and multivariate feature vectors.
- **Local Outlier Factor (LOF)**: Density-based local outlier detection on spatial-temporal feature space.
- **Robust Statistical Estimators**: Median Absolute Deviation (MAD) on high-frequency residuals for spike detection.
- *(Future Exploration: Autoencoders / Temporal Convolutional Networks for sequence reconstruction loss).*

### 3.2. Stage 2: Root-Cause Classification
- Decision tree / rule-augmented classifier mapping detected anomalies, feature contribution vectors, and spatial agreement flags to the 15-category taxonomy.

### 3.3. Stage 3: Explainability (SHAP / Feature Contributions)
- TreeSHAP integration to compute local feature attributions:
  - e.g., *"Observation flagged as SPIKE primarily due to 5-minute temperature rate of change (+6.2°C/5min, SHAP value: +0.48) with zero spatial neighbor corroboration (SHAP value: +0.32)."*

---

## 4. Synthetic Anomaly Injection & Evaluation Engine (Planned)
To benchmark and validate model performance without relying solely on rare natural failures, SkyGuard AI includes a synthetic fault generator capable of injecting controlled anomalies into historical series:

```yaml
synthetic_fault_types:
  - name: "spike"
    magnitude_range: [3.0, 15.0]
    duration_steps: [1, 3]
  - name: "drift"
    slope_per_hour: [0.1, 1.5]
    duration_hours: [6, 72]
  - name: "frozen_value"
    duration_steps: [6, 48]
  - name: "step_offset"
    offset_magnitude: [2.0, 8.0]
  - name: "missing_burst"
    dropped_steps: [3, 24]
```

- **Ground Truth Isolation**: Injected fault metadata (`fault_type`, `injected_delta`, `start_time`, `end_time`) is stored in an independent evaluation label registry and never passed into model training or inference feature sets.

---

## 5. Model Versioning & Lifecycle
- Model persistence via `joblib` in `models/registry/`.
- Strict artifact naming convention: `skyguard_{model_type}_{parameter}_v{semver}_{timestamp}.joblib`.
- Accompanying JSON manifest containing:
  - Model UUID & semantic version
  - Training dataset hash & date range
  - Exact feature list & transformation pipeline parameters
  - Benchmark performance metrics (Precision, Recall, F1 on synthetic evaluation sets)
  - Target station IDs or universal network applicability
