# NETRA APEX CLEAN SLATE PLAN
## Executive Summary
Complete reset and cleanup of Netra Apex project to establish a pristine baseline for future development.

## Phase 1: Assessment & Backup (30 min)

### 1.1 Current State Audit
- [ ] Git status review - document all uncommitted changes
- [ ] Database schema inventory (ClickHouse + PostgreSQL)
- [ ] Configuration files audit (.env, secrets, settings)
- [ ] Legacy code identification (search for _old, _backup, _deprecated)
- [ ] Test artifacts and temporary files inventory

### 1.2 Critical Backup
- [ ] Export production/staging configurations if needed
- [ ] Backup any custom test data worth preserving
- [ ] Document current working features before changes
- [ ] Create git branch `pre-clean-slate-backup`

## Phase 2: Database Clean Slate (45 min)

### 2.1 PostgreSQL Reset
```bash
# Drop all tables and recreate
python -c "from app.db.postgres import drop_all_tables; drop_all_tables()"
alembic downgrade base
alembic upgrade head
```

### 2.2 ClickHouse Reset
```bash
# Drop and recreate ClickHouse tables
python -c "from app.db.clickhouse import reset_clickhouse_schema; reset_clickhouse_schema()"
```

### 2.3 Seed Data Creation
- Minimal user accounts (admin, test users)
- Sample corpus entries
- Basic configuration entries
- Test conversation data

## Phase 3: Code Cleanup (2 hours)

### 3.1 Legacy Code Removal
**Targets for removal:**
- Files with suffixes: _old, _backup, _deprecated, _temp, _test_fixes
- Duplicate implementations (check LLM_MASTER_INDEX.md)
- Commented-out code blocks
- Unused imports and dead code

### 3.2 Architecture Compliance
```bash
# Check and fix architecture violations
python scripts/check_architecture_compliance.py

# Files to split if >300 lines:
# - Identify and modularize any violating files
# - Ensure all functions ≤8 lines
```

### 3.3 Type Safety Verification
- Ensure single sources of truth for all types
- Remove duplicate type definitions
- Validate Pydantic models consistency
- Check TypeScript types alignment

## Phase 4: Configuration Cleanup (30 min)

### 4.1 Environment Variables
- Audit .env.example vs actual .env
- Remove deprecated variables
- Document all required variables
- Ensure proper secret isolation

### 4.2 Configuration Files
- Clean config/*.yaml files
- Update app/config.py with current settings
- Remove hardcoded values
- Validate all paths and URLs

## Phase 5: Test Environment Reset (30 min)

### 5.1 Clear Test Artifacts
```bash
# Remove all test artifacts
rm -rf test_reports/
rm -f failing_tests.log
rm -rf .coverage
rm -rf htmlcov/
rm -rf .pytest_cache/
```

### 5.2 Test Database Reset
- Create fresh test database
- Run test migrations
- Create minimal test fixtures

## Phase 6: Validation (1 hour)

### 6.1 Run Test Suites
```bash
# Smoke test first
python test_runner.py --level smoke

# Then integration
python test_runner.py --level integration --no-coverage --fast-fail

# Finally comprehensive
python test_runner.py --level comprehensive
```

### 6.2 Manual Validation
- [ ] Backend starts without errors
- [ ] Frontend builds and runs
- [ ] WebSocket connections work
- [ ] Database connections verified
- [ ] Auth flow functional

## Phase 7: Documentation Update (30 min)

### 7.1 Update Core Docs
- Update CLAUDE.md with clean state notes
- Refresh LLM_MASTER_INDEX.md
- Update README with current setup steps
- Document any removed features

### 7.2 Update Specs
- Update learnings.xml with cleanup insights
- Ensure all XML specs reflect current state
- Document architectural decisions

## Execution Checklist

### Pre-execution
- [ ] Notify team of clean slate operation
- [ ] Ensure no critical operations running
- [ ] Create full backup branch
- [ ] Document current git hash

### During Execution
- [ ] Follow phases in order
- [ ] Test after each major phase
- [ ] Document any issues encountered
- [ ] Keep audit trail of removed items

### Post-execution
- [ ] Run full test suite
- [ ] Verify all services start
- [ ] Check monitoring/logging
- [ ] Team verification of functionality
- [ ] Commit clean state with detailed message

## Rollback Plan
If issues arise:
1. `git checkout pre-clean-slate-backup`
2. Restore database backups
3. Revert configuration changes
4. Document failure points for retry

## Success Criteria
- ✅ All tests passing
- ✅ No legacy code remaining
- ✅ All files ≤300 lines, functions ≤8 lines
- ✅ Single sources of truth enforced
- ✅ Databases fresh with seed data
- ✅ Documentation current
- ✅ Team can develop without issues

## Time Estimate
Total: 4-5 hours
- Phase 1: 30 minutes
- Phase 2: 45 minutes  
- Phase 3: 2 hours
- Phase 4: 30 minutes
- Phase 5: 30 minutes
- Phase 6: 1 hour
- Phase 7: 30 minutes

## Notes
- Best executed during low-activity period
- Requires coordination if multiple developers active
- Consider staging environment test first
- Document all decisions for future reference