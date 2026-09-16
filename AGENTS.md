# Project-Level Engineering Rules & Agent Guidelines: SkyGuard AI

## 1. Prime Directive
SkyGuard AI is a mission-critical meteorological data quality and anomaly detection platform for Automatic Weather Stations (AWS). All engineering practices must prioritize data integrity, system reliability, clarity, and architectural consistency.

**CRITICAL INSTRUCTION FOR ALL AI AGENTS & DEVELOPERS:**
> **Before implementing any phase, feature, or refactor, you MUST read the relevant documentation in [`docs/`](file:///d:/Projects/sih_project/docs/).**
> Never assume requirements or invent schemas. Adhere strictly to the established system architecture.

---

## 2. Mandatory Data Principles
1. **Raw observations are immutable**: Never overwrite, mutate, or delete original incoming sensor data.
2. **Separation of Concerns**: Validated, imputed, corrected, or model-derived values must be stored separately with explicit derivation metadata (`is_synthetic`, `correction_method`, `model_version`).
3. **Suspicious $\neq$ Faulty**: An observation flagging a statistical anomaly must be checked against spatial neighbors and meteorological context before root-cause determination.
4. **Extreme $\neq$ Anomalous**: Severe physical weather events (e.g., squalls, heatwaves, cyclones) produce extreme readings that are genuine. The system must support `POSSIBLE_GENUINE_EVENT` and `UNCERTAIN` classifications.
5. **No Probabilities without Calibration**: ML anomaly scores must not be represented as calibrated probabilities unless formal probabilistic calibration is explicitly implemented.
6. **Ground-Truth Isolation**: Synthetic evaluation ground-truth labels must strictly remain isolated from model inference inputs.
7. **Spatial Proximity**: Geographic calculations must use geodesic distance (latitude, longitude, elevation) and spatial topography—never simple state or administrative boundaries.

---

## 3. Development & Coding Standards

### Inspection & Scope
- **Inspect Before Modifying**: Read existing code, types, and configurations before writing new files or making changes.
- **Small, Focused Changes**: Implement one well-defined component or feature at a time.
- **No Unrelated Refactoring**: Do not reorganize or reformat unrelated modules when fixing bugs or adding targeted features.
- **Explicit Error Handling**: Catch specific exceptions. Never swallow exceptions silently with bare `except: pass`.

### Type Safety & Validation
- **Python Backend**: All functions and methods must have strict Python type hints. All inbound and outbound payloads must validate through Pydantic v2 schemas.
- **TypeScript Frontend**: Strict mode enabled. No `any` types allowed in core domain models.
- **Configuration Over Hard-coding**: Never hard-code thresholds, sampling rates, API endpoints, or model paths in application code. All parameters must be sourced from configuration files (`configs/`) or environment variables via `pydantic-settings`.

### Verification & Testing Integrity
- **Mandatory Verification**: Never claim a feature, test, or build works without actually executing the test suite or verification command.
- **No Invented Test Results**: Output logs and test outcomes must represent real execution results.
- **Regression Prevention**: Every bug fix must include a test reproducing the original issue.
- **New Features Require Tests**: Unit tests must accompany all schema additions, connectors, validators, and transformers.

### Security Standards
- **Zero Secrets in Code**: API keys, database credentials, and secrets must never be committed to Git.
- **Environment Separation**: Use `.env` (git-ignored) and provide placeholders in `.env.example`.
- **Sanitized Logging**: Ensure passwords, tokens, and sensitive headers are stripped before logging.
- **Safe Error Responses**: Production API responses must never leak internal stack traces or database connection details.

---

## 4. Phase Execution Protocol
When tasked with executing a project phase:
1. Review `docs/DECISIONS.md` and the relevant domain spec (`docs/DATA_SPEC.md`, `docs/ML_SPEC.md`, `docs/API_SPEC.md`, etc.).
2. Formulate an implementation plan and verify against architectural boundaries.
3. Implement code with comprehensive type safety and error handling.
4. Execute automated tests (`pytest`) and verify clean passes.
5. Update documentation and walkthrough logs to maintain operational traceability.
