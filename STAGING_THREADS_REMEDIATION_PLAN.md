# Staging Threads 500 Error - Remediation Plan

## Executive Summary
Staging environment experiencing 500 errors on GET /api/threads due to JSONB query failures. Root cause identified as NULL/malformed metadata in existing threads. Fix implemented with fallback mechanism. This plan outlines immediate actions and long-term improvements.

## Current Status
- ✅ **Root Cause Identified**: JSONB query fails on NULL metadata
- ✅ **Fix Implemented**: Fallback mechanism added
- ✅ **Tests Created**: 9 comprehensive test cases
- ✅ **Learnings Documented**: Saved to SPEC files
- ⏳ **Deployment Pending**: Ready for staging deployment

## Immediate Actions (Priority 1 - Do Now)

### 1. Deploy Fix to Staging (30 mins)
```bash
# Step 1: Commit changes
git add -A
git commit -m "fix(threads): add robust JSONB query handling with fallback

- Implement fallback mechanism for NULL/malformed metadata
- Add environment-aware error logging
- Normalize user_id consistently across operations
- Add comprehensive test coverage

Fixes staging /api/threads 500 error"

# Step 2: Push to branch
git push origin critical-remediation-20250823

# Step 3: Deploy to staging
python scripts/deploy_to_gcp.py --project netra-staging --build-local
```

### 2. Monitor Staging Logs (15 mins)
```bash
# Watch for fallback usage (indicates data issues)
gcloud logging read "resource.type=cloud_run_revision AND 
  resource.labels.service_name=netra-backend-staging AND
  textPayload:\"Fallback query\"" --limit=50

# Check for critical errors
gcloud logging read "resource.type=cloud_run_revision AND
  resource.labels.service_name=netra-backend-staging AND
  severity>=ERROR AND
  textPayload:\"Unable to retrieve threads\"" --limit=50
```

### 3. Verify Fix (15 mins)
```bash
# Test with real JWT token
curl -X GET "https://api.staging.netrasystems.ai/api/threads?limit=20&offset=0" \
  -H "Authorization: Bearer ${JWT_TOKEN}"

# Run staging validation script
python scripts/test_staging_threads_fix.py
```

## Data Cleanup (Priority 2 - Within 24 hours)

### 1. Audit Existing Threads
```sql
-- Connect to staging database
-- Count threads with NULL metadata
SELECT COUNT(*) as null_metadata_count 
FROM threads 
WHERE metadata_ IS NULL;

-- Count threads with missing user_id
SELECT COUNT(*) as missing_user_id 
FROM threads 
WHERE metadata_ IS NOT NULL 
  AND (metadata_->>'user_id' IS NULL OR metadata_->>'user_id' = '');

-- Find malformed metadata
SELECT id, metadata_ 
FROM threads 
WHERE metadata_ IS NOT NULL 
  AND jsonb_typeof(metadata_) != 'object'
LIMIT 10;
```

### 2. Fix Legacy Data
```sql
-- Backup first!
CREATE TABLE threads_backup_20250904 AS SELECT * FROM threads;

-- Fix NULL metadata
UPDATE threads 
SET metadata_ = '{"status": "legacy", "fixed_at": "2025-09-04"}'::jsonb
WHERE metadata_ IS NULL;

-- Add user_id from messages if missing
UPDATE threads t
SET metadata_ = jsonb_set(
  COALESCE(metadata_, '{}')::jsonb,
  '{user_id}',
  to_jsonb(m.user_id)
)
FROM (
  SELECT DISTINCT thread_id, metadata_->>'user_id' as user_id 
  FROM messages 
  WHERE metadata_->>'user_id' IS NOT NULL
) m
WHERE t.id = m.thread_id
  AND (t.metadata_->>'user_id' IS NULL OR t.metadata_->>'user_id' = '');
```

## Infrastructure Improvements (Priority 3 - Within 1 week)

### 1. Add Database Index
```sql
-- Improve query performance
CREATE INDEX CONCURRENTLY idx_threads_user_id 
ON threads ((metadata_->>'user_id'))
WHERE metadata_ IS NOT NULL;

-- Analyze performance impact
EXPLAIN ANALYZE 
SELECT * FROM threads 
WHERE metadata_->>'user_id' = 'test-user-id';
```

### 2. Add Database Constraints
```sql
-- Ensure metadata is never NULL for new threads
ALTER TABLE threads 
ALTER COLUMN metadata_ SET DEFAULT '{}'::jsonb;

-- Add check constraint (optional, test first)
ALTER TABLE threads 
ADD CONSTRAINT check_metadata_not_null 
CHECK (metadata_ IS NOT NULL);
```

### 3. Add Monitoring Alerts
```yaml
# monitoring/alerts.yaml
alerts:
  - name: threads-fallback-query-usage
    description: Alert when fallback query is used frequently
    query: |
      resource.type="cloud_run_revision"
      resource.labels.service_name="netra-backend-staging"
      textPayload:"Attempting fallback query"
    threshold: 10
    window: 5m
    
  - name: threads-query-failures
    description: Alert on thread query failures
    query: |
      resource.type="cloud_run_revision"
      resource.labels.service_name="netra-backend-staging"
      textPayload:"Unable to retrieve threads"
    threshold: 1
    window: 1m
```

## Long-term Improvements (Priority 4 - Q1 2025)

### 1. Migrate to Dedicated User-Thread Mapping
```python
# Consider separate table for cleaner queries
class UserThread(Base):
    __tablename__ = "user_threads"
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    thread_id = Column(String, ForeignKey("threads.id"), primary_key=True)
    created_at = Column(DateTime, default=func.now())
    
    # Indexes automatically created on primary keys
```

### 2. Implement Caching Layer
```python
# Redis caching for user threads
async def get_user_threads_cached(user_id: str):
    cache_key = f"user_threads:{user_id}"
    
    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Fallback to database
    threads = await get_user_threads_from_db(user_id)
    
    # Cache for 5 minutes
    await redis.setex(cache_key, 300, json.dumps(threads))
    return threads
```

### 3. Add Comprehensive Testing
```python
# Property-based testing for edge cases
from hypothesis import given, strategies as st

@given(
    user_id=st.one_of(
        st.uuids(),
        st.integers(),
        st.text(),
        st.none()
    )
)
def test_thread_query_handles_any_user_id_format(user_id):
    """Test that any user_id format is handled gracefully"""
    # Test implementation
```

## Success Metrics

### Immediate (Day 1)
- [ ] Zero 500 errors on /api/threads endpoint
- [ ] All authenticated users can list threads
- [ ] Fallback query usage < 10% of requests

### Short-term (Week 1)
- [ ] All NULL metadata fixed in database
- [ ] Index created and query performance improved
- [ ] Monitoring alerts configured

### Long-term (Month 1)
- [ ] Fallback query usage < 1% of requests
- [ ] Average response time < 100ms
- [ ] Zero data-related incidents

## Rollback Plan

If issues persist after deployment:

```bash
# 1. Quick rollback
git revert HEAD
git push origin critical-remediation-20250823

# 2. Redeploy previous version
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# 3. Restore database if data was modified
-- Only if data migration was performed
DROP TABLE threads;
ALTER TABLE threads_backup_20250904 RENAME TO threads;
```

## Communication Plan

### Stakeholder Updates
1. **Engineering Team**: Slack notification when deployed
2. **Product Team**: Update on fix status and impact
3. **Support Team**: Instructions for user issues

### Status Updates
- [ ] Pre-deployment: Notify of maintenance window
- [ ] Post-deployment: Confirm successful fix
- [ ] 24 hours later: Report on stability

## Checklist

### Before Deployment
- [x] Code reviewed and tested
- [x] Tests passing (9/9)
- [x] Learnings documented
- [x] Rollback plan ready
- [ ] Staging backup created

### During Deployment
- [ ] Monitor deployment logs
- [ ] Run smoke tests immediately
- [ ] Check error rates

### After Deployment
- [ ] Verify no 500 errors
- [ ] Monitor fallback usage
- [ ] Update team on status
- [ ] Schedule data cleanup
- [ ] Plan long-term improvements

## Contact Points

- **Technical Lead**: Review before deployment
- **DevOps**: Assist with deployment and monitoring
- **Database Admin**: Help with data cleanup queries
- **Product Manager**: Approve deployment window

---

## Appendix: File Changes

### Modified Files
1. `netra_backend/app/services/database/thread_repository.py` - Core fix
2. `netra_backend/app/routes/utils/thread_error_handling.py` - Better logging
3. `SPEC/learnings/index.xml` - Learnings documentation

### New Files
1. `tests/mission_critical/test_threads_500_error_fix.py` - Test coverage
2. `SPEC/learnings/threads_500_error_jsonb_query_20250904.xml` - Detailed learning
3. `STAGING_THREADS_500_ERROR_FIVE_WHYS.md` - Root cause analysis
4. `THREAD_PERSISTENCE_ANALYSIS.md` - Data flow documentation
5. `STAGING_THREADS_FIX_SUMMARY.md` - Fix summary
6. `STAGING_THREADS_REMEDIATION_PLAN.md` - This document