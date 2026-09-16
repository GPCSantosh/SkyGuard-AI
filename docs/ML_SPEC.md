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

## 3. Anomaly Detection Models (Phase 3 Implemented Baselines)

### 3.1. Implemented Baseline Models
- **FixedThresholdDetector** (`ml/models/baselines.py`): Deterministic physical domain bounds check across primary parameters (Temperature, Dewpoint, Pressure, Wind Speed).
- **RollingZScoreDetector** (`ml/models/baselines.py`): Dynamic temporal window standard score residual detector with min-periods and variance floor safeguards.
- **IsolationForestDetector** (`ml/models/isolation_forest.py`): Multi-dimensional scikit-learn isolation forest wrapped in `BaseAnomalyModel` with sanitized input feature vectors, continuous normalized anomaly scores in $[0, 1]$, and validation quantile threshold calibration.

### 3.2. Future Pipeline Stages (Phase 4 & 5)
- **Stage 2: Spatial Topographic Consensus Engine (Phase 4)**: Cross-AWS neighbor correlation and elevation-adjusted IDW verification to separate genuine severe weather from hardware failures.
- **Stage 3: Hybrid Root-Cause Decision Engine (Phase 5)**: Rule-augmented classifier mapping multi-model anomaly signals to the 15-category taxonomy.
- **Stage 4: Explainability (Phase 5)**: TreeSHAP local feature attributions and sensor health indexing.

---

## 4. Synthetic Anomaly Injection & Evaluation Framework
Implemented in `ml/synthetic/` and `ml/evaluation/`:
- **15-Class Anomaly Injector**: Controlled synthetic mutations with subtle, moderate, and obvious severity profiles.
- **Strict Chronological Splitting**: Non-overlapping Past $\rightarrow$ Future Train/Val/Test partitions with zero future leakage.
- **Ground-Truth Isolation**: Synthetic labels (`fault_type`, `injected_delta`, `severity`, `is_synthetic`) are strictly isolated from feature inputs and used only by `ModelEvaluator`.

---

## 5. Model Versioning & Lifecycle
- Model weights saved to `models/registry/<model_id>_weights.joblib`.
- Metadata manifests saved to `models/registry/<model_id>_metadata.json` containing:
  - Model UUID, model type, creation timestamp
  - Exact feature list, hyperparameter dictionary
  - Calibrated anomaly threshold and training score percentiles

