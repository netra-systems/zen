"""Redis SSOT Import Pattern Tests

MISSION: Validate Redis import pattern compliance to protect $500K+ ARR chat functionality.

This module contains comprehensive tests for Redis SSOT import pattern migration:

1. test_redis_import_pattern_compliance.py - Static code analysis for import patterns
2. test_import_pattern_migration_e2e.py - End-to-end migration functionality validation  
3. test_cross_service_import_consistency.py - Cross-service import consistency validation

CRITICAL PROTECTIONS:
- Golden Path chat functionality preservation during migration
- User isolation maintenance across Redis operations
- Service boundary respect with shared Redis infrastructure
- Connection pool conflict prevention

These tests ensure safe migration of Redis imports to SSOT pattern without breaking
the core business value delivery through chat functionality.
"""