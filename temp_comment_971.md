## FAILING TEST GARDENER UPDATE - 2025-09-14

**New deprecation warnings detected by failing test gardener process:**

### Recent Deprecation Warnings Confirmed

**1. Logging Import Deprecation (ACTIVE)**
```
shared.logging.unified_logger_factory is deprecated. Use 'from shared.logging.unified_logging_ssot import get_logger' instead.
```

**2. WebSocket Import Deprecation (ACTIVE)**
```
Importing WebSocketManager from 'netra_backend.app.websocket_core' is deprecated. Use canonical path 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager' instead.
```

**3. Pydantic Configuration Deprecation (ACTIVE)**
```
Support for class-based config is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0.
```

**4. Pydantic JSON Encoders Deprecation (ACTIVE)**
```
json_encoders is deprecated. See https://docs.pydantic.dev/2.11/concepts/serialization/#custom-serializers for alternatives.
```

### Business Impact Assessment
- **Priority**: P3 (Future compatibility issues, nice-to-have improvements)
- **Risk Level**: Technical debt accumulation
- **Future Impact**: Potential breaking changes when dependencies are updated
- **Development**: Code maintainability concerns

### Failing Test Gardener Context
- **Category**: failing-test-new-P3-deprecation-warnings
- **Status**: WARNING
- **Detection**: Critical test suite execution
- **Frequency**: Multiple deprecation warnings across test runs

### Relationship to Existing Work
This update confirms that the deprecation patterns identified in this issue (#416) are still active and require systematic remediation as originally planned in the migration phases.

**Related Active Issues:**
- #826: DateTime deprecation warnings (P2)
- #839: Deprecated imports (P2, actively-being-worked-on)
- #980: SSOT deprecated import warnings (P2)

### Recommended Action
Continue with the planned migration phases outlined in the original issue, with emphasis on:
1. **Phase 1**: Logging system migration (shared.logging patterns)
2. **Phase 2**: WebSocket import migration (SSOT registry compliance)
3. **Phase 5**: Pydantic configuration migration (ConfigDict adoption)

---
Generated with Claude Code

Co-Authored-By: Claude