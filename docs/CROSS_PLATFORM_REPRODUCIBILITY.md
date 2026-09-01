# Cross-platform reproducibility

TrustData supports Python 3.12 on Windows, macOS, and Linux. Reproducibility means that the same committed input snapshot, configuration, dependency versions, and random seeds produce the same canonical input rows and evaluation membership on every supported operating system.

## Determinism contract

- Canonical CSV files always use UTF-8 and LF line endings.
- Observed inputs and generated benchmark tables use stable record ordering.
- Catalog selection, attack selection, score samples, and Top-K metrics use explicit deterministic tie-breakers.
- Contributor split generation first canonicalizes records by `record_id`.
- Manifest paths always use `/`, including manifests generated on Windows.
- The dependency lock is universal and Python is restricted to 3.12.

Runtime metadata such as start time, finish time, elapsed seconds, operating-system description, and audit event time is expected to differ between runs. These fields must not be used as cross-platform metric-equality evidence.

## Setup

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts\prepare_observed_data.py
.\.venv\Scripts\python scripts\run_trustdata.py
.\.venv\Scripts\python scripts\verify_run_manifest.py
.\.venv\Scripts\python -m pytest
```

macOS or Linux:

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python scripts/prepare_observed_data.py
./.venv/bin/python scripts/run_trustdata.py
./.venv/bin/python scripts/verify_run_manifest.py
./.venv/bin/python -m pytest
```

## Comparing runs

Compare canonical inputs and metric outputs rather than the entire run directory. The minimum comparison set is:

- `data/processed/observed_entities.csv`
- `data/processed/observed_reviews.csv`
- `outputs/runs/latest/classification_metrics.csv`
- `outputs/runs/latest/ranking_metrics.csv`
- `outputs/runs/latest/split_sensitivity_metrics.csv`
- `outputs/runs/latest/split_sensitivity_summary.csv`

Do not compare `run_manifest.json` or `audit_trail.csv` byte-for-byte because they intentionally contain runtime timestamps and environment evidence.
