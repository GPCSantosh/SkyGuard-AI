# SkyGuard AI — Engineering Rules & Operational Standards

## 1. Prime Directive
SkyGuard AI is an intelligent data-quality and anomaly-detection system for Automatic Weather Stations. Reliability, reproducibility, and non-destructive data handling are mandatory.

## 2. Core Operational Rules
1. **Always Read Docs First**: Before designing or implementing any component, read the corresponding document in `docs/` (`PROJECT_SPEC.md`, `ARCHITECTURE.md`, `DATA_SPEC.md`, `ML_SPEC.md`, `API_SPEC.md`, `UI_DESIGN_SYSTEM.md`, `TEST_PLAN.md`, `EVALUATION_PLAN.md`, `DECISIONS.md`).
2. **Never Silently Overwrite Raw Data**: Raw observations are immutable and must be preserved permanently.
3. **No Uncalibrated Probabilities**: ML anomaly scores must not be misrepresented as calibrated probabilities without formal calibration.
4. **Physical Sanity Over Statistical Outliers**: Ensure meteorological plausibility checks (e.g. physical boundary limits, dew-point consistency) precede or corroborate ML flags.
5. **No Hard-Coded Business Logic**: Thresholds, observation cadences, model hyper-parameters, and connection strings must live in configuration files (`configs/`) or environment variables.
6. **Mandatory Test Verification**: Execute tests (`pytest`) before declaring any task complete. Never claim passing tests without real execution logs.
7. **Zero Secret Leakage**: Do not commit credentials, `.env` files, or private tokens.
8. **Small, Atomic Commits / Edits**: Keep changes focused and self-contained. Do not perform sweeping refactors of working unrelated code.
