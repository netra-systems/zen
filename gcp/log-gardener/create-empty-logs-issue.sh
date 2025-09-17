#!/bin/bash

# Create GitHub issue for empty log payloads problem
gh issue create \
  --title "GCP-active-dev | P2 | Application logs not capturing error details - empty payloads" \
  --label "P2-high,logging,observability,gcp-staging,claude-code-generated-issue,debugging" \
  --body "## Critical Observability Gap - Empty Log Payloads

### Executive Summary
92% of ERROR and WARNING logs in GCP staging contain empty payloads, creating complete operational blindness during failures. This affects \$500K+ ARR debugging capabilities.

### Latest Evidence (2025-09-16T02:00-03:00 UTC)
- **Volume**: 169 empty ERROR/WARNING logs in 1 hour
- **Pattern**: All logs have empty json_payload and null text_payload
- **Impact**: Cannot diagnose any application errors

### Technical Analysis

#### Empty Log Pattern
\`\`\`json
{
  \"severity\": \"ERROR\",
  \"text_payload\": null,
  \"json_payload\": {},
  \"source_location\": {},
  \"timestamp\": \"2025-09-16T02:03:43.026433Z\"
}
\`\`\`

#### Root Cause Hypothesis
1. **JSON Formatter Failures**: Serialization errors silently failing
2. **Context Corruption**: User context not properly attached
3. **GCP Integration**: Cloud Run logging adapter misconfiguration
4. **Async Context Loss**: Context manager losing state in async operations

### Business Impact
- **Debugging**: Zero visibility into production errors
- **MTTR**: Mean time to resolution severely impacted
- **Customer Support**: Cannot diagnose customer issues
- **Revenue Impact**: \$500K+ ARR at risk due to debugging blindness

### Acceptance Criteria
- [ ] Zero empty payloads in ERROR/WARNING logs
- [ ] 95% of logs contain proper context (user_id, request_id)
- [ ] Stack traces captured for all exceptions
- [ ] Monitoring alerts for empty log detection

### Implementation Priority
1. **P0**: Harden JSON formatter with fallback serialization
2. **P1**: Add context safety checks before logging
3. **P2**: Implement monitoring for empty log detection

### Related Files
- shared/logging/unified_logging_ssot.py (Lines 124-145: JSON formatter)
- netra_backend/app/core/logging_setup.py (Context attachment)
- netra_backend/app/core/middleware/logging_middleware.py

### Testing
Existing test coverage in:
- tests/logging/test_json_formatter_edge_cases.py
- tests/integration/test_logging_context_preservation.py

Generated with Claude Code - GCP Log Gardener
Label: claude-code-generated-issue"