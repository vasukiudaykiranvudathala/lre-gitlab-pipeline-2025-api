# lre-gitlab-pipeline-2025-api

# LoadRunner Enterprise (LRE) Performance Test – CI/CD Integration

This project automates performance test execution on **LoadRunner Enterprise (LRE)** via a Python script triggered through a **GitLab CI/CD pipeline** on a Windows runner. (change runner based on the needed windows/ Linux)

---

## Overview

The `run-lre-test.py` script authenticates with the LRE REST API, starts a performance test run, monitors it in real time, and automatically stops the run if the transaction failure rate exceeds 5%. On completion, it downloads and extracts the raw results as pipeline artifacts.

---

## Prerequisites

- Python 3.9+ installed on the GitLab runner (expected at `C:\Python39`)
- The `requests` library available in the Python environment
- A GitLab runner tagged `windows` with a 3-hour timeout
- A valid LRE API token with access to the target domain and project

---

## Environment Variables

All configuration is passed via environment variables (set in GitLab CI/CD Settings → Variables):

| Variable | Description |
|---|---|
| `lre_test` | Numeric ID of the LRE test to run |
| `lre_test_instance` | Numeric ID of the test instance (must not be `AUTO`) |
| `lre_timeslot_duration_hours` | Timeslot duration – hours component |
| `lre_timeslot_duration_minutes` | Timeslot duration – minutes component |
| `LRE_API_TOKEN` | API token used to authenticate with LRE |
| `lRE_URL` | Base URL of the LRE server (e.g. `https://lre.example.com`) |
| `DOMAIN` | LRE domain name |
| `PROJECT_NAME` | LRE project name |

> **Note:** `lre_test_instance` cannot be set to `AUTO`. The script will exit with an error if it is.

---

## How It Works

1. **Authentication** – Opens a session and authenticates against the LRE REST API using the provided token.
2. **Start Test Run** – Posts a run request with the configured test ID, instance ID, and timeslot duration. Post-run action is set to `Collate Results`.
3. **Poll Status** – Checks run status every 30 seconds until the run reaches `FINISHED`, `FAILED`, or `STOPPED`.
4. **Failure Rate Check** – While the run is in `RUNNING` state, fetches extended metrics and calculates the transaction failure percentage. If it reaches or exceeds **5%**, the run is stopped immediately.
5. **Download Artifacts** – Fetches the `RawResults` ZIP from the LRE API, extracts it, and copies the contents to an `Artifacts/RawResults/` directory in the workspace.

---

## GitLab CI/CD Pipeline

The pipeline stage is defined as follows:

```yaml
stages:
  - performancetest

test-loadrunner:
  stage: performancetest
  tags:
    - windows
  timeout: 3h
  when: manual
  allow_failure: false
```

The job is **manual** — it must be triggered explicitly from the GitLab UI. It runs on a `windows`-tagged runner and does not allow failure by default.

### Artifacts

The job saves the following artifacts for **1 week**, regardless of pass/fail outcome:

| Path | Description |
|---|---|
| `Artifacts/Report.html` | Top-level HTML report |
| `Artifacts/Report/` | Full report directory |

The artifact URL is printed at the end of the job:

```
https://gitlab.com/-/<project>/<repo>/-/jobs/$CI_JOB_ID/artifacts/Artifacts/Report.html
```

---

## Running Locally

To run the script outside of CI, set the required environment variables in your shell and execute:

```bash
python scripts/CI_CD.py
```

Make sure all environment variables listed above are exported in your session before running.

---

## Notes

- The failure threshold is hardcoded at **5%**. Adjust the condition in `run-lre-test.py` if a different threshold is needed.
- The script polls every **30 seconds**. For long-running tests, this interval can be increased to reduce API load.
- Raw results are extracted to the system temp directory before being copied to the `Artifacts/` folder.
