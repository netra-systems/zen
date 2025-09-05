# CRITICAL: ClickHouse Driver Dependency Mismatch Fix

## Root Cause Identified
The staging deployment failure is caused by a **dependency mismatch**:
- **Code imports:** `from clickhouse_driver import Client`
- **Requirements has:** `clickhouse-connect>=0.8.18`
- These are **DIFFERENT PACKAGES**!

## The Problem
1. `clickhouse-driver` - The package the code actually uses (NOT installed)
2. `clickhouse-connect` - A different ClickHouse client library (installed but not used)

## Immediate Fix Required
Add the missing dependency to requirements.txt:
```
clickhouse-driver>=0.2.9
```

## Code Usage Evidence
Multiple files import from `clickhouse_driver`:
- `netra_backend/app/db/clickhouse_table_initializer.py`
- `netra_backend/app/db/clickhouse_initializer.py`
- `netra_backend/app/db/clickhouse_schema.py`
- `netra_backend/app/db/clickhouse_trace_writer.py`
- Plus 23 other files

## Decision Required
Option A: Add `clickhouse-driver` to requirements.txt (Quick fix)
Option B: Refactor all code to use `clickhouse-connect` instead (Better long-term)

## Recommended Action (Option A - Quick Fix)
1. Add `clickhouse-driver>=0.2.9` to requirements.txt
2. Keep `clickhouse-connect` for now (may be used elsewhere)
3. Redeploy staging
4. Later: Consolidate to single ClickHouse client library

This explains why the error "No module named 'clickhouse_driver'" occurs in staging!