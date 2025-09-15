# WebSocket Manager SSOT Migration - Test Command Reference

**Created:** 2025-09-14
**Purpose:** Practical command reference for executing WebSocket Manager SSOT Phase 2 migration tests
**Usage:** Copy-paste commands for each migration phase

## Quick Reference Commands

### Pre-Migration Validation (MANDATORY)
```bash
# Phase 1: Baseline Validation
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_import_baseline.py -v
python -m pytest tests/integration/test_websocket_manager_user_isolation_baseline.py -v --real-services
python -m pytest tests/e2e/staging/test_golden_path_websocket_baseline.py -v

# Mission Critical Gate (MUST PASS)
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_websocket_event_structure_golden_path.py
```

### During Migration Validation
```bash
# After Each Migration Batch
python tests/mission_critical/test_websocket_agent_events_suite.py
python -m pytest tests/integration/test_websocket_manager_factory_migration.py -v --real-services
python -m pytest tests/e2e/staging/test_websocket_migration_impact_staging.py -v

# Rollback Capability Test (If Needed)
python -m pytest tests/e2e/staging/test_migration_rollback_capability.py -v
```

### Post-Migration Validation (MANDATORY)
```bash
# Phase 3: SSOT Compliance Validation
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_ssot_compliance.py -v
python -m pytest tests/integration/test_websocket_manager_enterprise_security.py -v --real-services
python -m pytest tests/e2e/staging/test_golden_path_ssot_validation_staging.py -v

# Final Mission Critical Validation
python tests/mission_critical/test_websocket_agent_events_suite.py
```

---

## Detailed Test Execution Guide

### Phase 1: Pre-Migration Baseline Establishment

#### Baseline Documentation Tests
```bash
# Document current import fragmentation
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_import_baseline.py::TestWebSocketManagerImportBaseline::test_document_current_import_paths -v

# Identify critical Golden Path dependencies
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_import_baseline.py::TestWebSocketManagerImportBaseline::test_identify_critical_import_dependencies -v

# Validate current WebSocket event delivery patterns
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_import_baseline.py::TestWebSocketManagerImportBaseline::test_validate_current_websocket_event_delivery -v
```

#### User Isolation Baseline Tests
```bash
# Test current user context isolation
python -m pytest tests/integration/test_websocket_manager_user_isolation_baseline.py::TestWebSocketManagerUserIsolationBaseline::test_current_user_context_isolation -v --real-services

# Document current factory behavior
python -m pytest tests/integration/test_websocket_manager_user_isolation_baseline.py::TestWebSocketManagerUserIsolationBaseline::test_current_websocket_factory_behavior -v --real-services
```

#### Golden Path Baseline in Staging
```bash
# Complete Golden Path baseline validation
python -m pytest tests/e2e/staging/test_golden_path_websocket_baseline.py::TestGoldenPathWebSocketBaseline::test_complete_golden_path_baseline -v

# Concurrent user baseline testing
python -m pytest tests/e2e/staging/test_golden_path_websocket_baseline.py::TestGoldenPathWebSocketBaseline::test_concurrent_user_baseline -v
```

#### Mission Critical Baseline (MUST PASS)
```bash
# Core WebSocket events validation
python tests/mission_critical/test_websocket_agent_events_suite.py

# Golden Path event structure
python tests/mission_critical/test_websocket_event_structure_golden_path.py

# SSOT multiple managers violation detection
python tests/mission_critical/test_websocket_ssot_multiple_managers_violation_detection.py
```

---

### Phase 2: Migration Execution Validation

#### Import Migration Validation
```bash
# Canonical import path validation
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_import_migration.py::TestWebSocketManagerImportMigration::test_canonical_import_path_validation -v

# Compatibility layer testing
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_import_migration.py::TestWebSocketManagerImportMigration::test_import_compatibility_during_migration -v

# Batch migration validation
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_import_migration.py::TestWebSocketManagerImportMigration::test_batch_migration_validation -v
```

#### Factory Pattern Migration Tests
```bash
# Factory consistency during migration
python -m pytest tests/integration/test_websocket_manager_factory_migration.py::TestWebSocketManagerFactoryMigration::test_factory_consistency_during_migration -v --real-services

# User context preservation
python -m pytest tests/integration/test_websocket_manager_factory_migration.py::TestWebSocketManagerFactoryMigration::test_user_context_preservation_during_migration -v --real-services
```

#### Staging Environment Impact Tests
```bash
# Golden Path during migration
python -m pytest tests/e2e/staging/test_websocket_migration_impact_staging.py::TestWebSocketMigrationImpactStaging::test_golden_path_during_migration -v

# Migration rollback capability
python -m pytest tests/e2e/staging/test_websocket_migration_impact_staging.py::TestWebSocketMigrationImpactStaging::test_migration_rollback_capability -v
```

#### Per-Batch Validation Commands
```bash
# After each migration batch (run all)
python tests/mission_critical/test_websocket_agent_events_suite.py && \
python -m pytest tests/integration/test_websocket_manager_factory_migration.py -v --real-services && \
python -m pytest tests/e2e/staging/test_websocket_migration_impact_staging.py::TestWebSocketMigrationImpactStaging::test_golden_path_during_migration -v
```

---

### Phase 3: Post-Migration SSOT Validation

#### SSOT Compliance Verification
```bash
# Single import path compliance
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_ssot_compliance.py::TestWebSocketManagerSSOTCompliance::test_single_import_path_compliance -v

# No import fragmentation
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_ssot_compliance.py::TestWebSocketManagerSSOTCompliance::test_no_import_fragmentation -v
```

#### Enterprise Security Validation
```bash
# HIPAA compliance isolation
python -m pytest tests/integration/test_websocket_manager_enterprise_security.py::TestWebSocketManagerEnterpriseSecurity::test_hipaa_compliance_isolation -v --real-services

# SOC2 compliance boundaries
python -m pytest tests/integration/test_websocket_manager_enterprise_security.py::TestWebSocketManagerEnterpriseSecurity::test_soc2_compliance_boundaries -v --real-services

# Concurrent enterprise users
python -m pytest tests/integration/test_websocket_manager_enterprise_security.py::TestWebSocketManagerEnterpriseSecurity::test_concurrent_enterprise_users -v --real-services
```

#### Complete Golden Path SSOT Validation
```bash
# Complete Golden Path with SSOT
python -m pytest tests/e2e/staging/test_golden_path_ssot_validation_staging.py::TestGoldenPathSSOTValidationStaging::test_complete_golden_path_ssot_validation -v

# Performance improvement validation
python -m pytest tests/e2e/staging/test_golden_path_ssot_validation_staging.py::TestGoldenPathSSOTValidationStaging::test_websocket_performance_improvement -v

# High concurrency SSOT validation
python -m pytest tests/e2e/staging/test_golden_path_ssot_validation_staging.py::TestGoldenPathSSOTValidationStaging::test_high_concurrency_ssot_validation -v

# Business value validation
python -m pytest tests/e2e/staging/test_golden_path_ssot_validation_staging.py::TestGoldenPathSSOTValidationStaging::test_business_value_validation -v
```

#### Final Mission Critical Validation
```bash
# Complete mission critical suite
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_websocket_event_structure_golden_path.py
python tests/mission_critical/test_websocket_ssot_multiple_managers_violation_detection.py
```

---

## Emergency and Rollback Commands

### Emergency Validation (Any Time)
```bash
# Quick Golden Path health check
python tests/mission_critical/test_websocket_agent_events_suite.py

# Staging environment validation
python -m pytest tests/e2e/staging/test_golden_path_websocket_baseline.py::TestGoldenPathWebSocketBaseline::test_complete_golden_path_baseline -v
```

### Rollback Validation Commands
```bash
# Test rollback capability
python -m pytest tests/e2e/staging/test_websocket_migration_impact_staging.py::TestWebSocketMigrationImpactStaging::test_migration_rollback_capability -v

# Validate baseline restoration
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_import_baseline.py -v
python -m pytest tests/integration/test_websocket_manager_user_isolation_baseline.py -v --real-services
```

### Performance Monitoring Commands
```bash
# Performance baseline comparison
python -m pytest tests/e2e/staging/test_golden_path_ssot_validation_staging.py::TestGoldenPathSSOTValidationStaging::test_websocket_performance_improvement -v

# Memory and resource monitoring
python -m pytest tests/integration/test_websocket_manager_enterprise_security.py::TestWebSocketManagerEnterpriseSecurity::test_concurrent_enterprise_users -v --real-services
```

---

## Continuous Integration Commands

### Pre-Commit Validation
```bash
# Quick validation before migration changes
python tests/mission_critical/test_websocket_agent_events_suite.py && \
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_import_baseline.py::TestWebSocketManagerImportBaseline::test_validate_current_websocket_event_delivery -v
```

### Post-Commit Validation
```bash
# Full validation after migration commits
python tests/mission_critical/test_websocket_agent_events_suite.py && \
python -m pytest tests/integration/test_websocket_manager_factory_migration.py -v --real-services && \
python -m pytest tests/e2e/staging/test_websocket_migration_impact_staging.py::TestWebSocketMigrationImpactStaging::test_golden_path_during_migration -v
```

### Deployment Gate Commands
```bash
# Pre-deployment validation (ALL MUST PASS)
python tests/mission_critical/test_websocket_agent_events_suite.py && \
python -m pytest tests/unit/websocket_ssot/test_websocket_manager_ssot_compliance.py -v && \
python -m pytest tests/integration/test_websocket_manager_enterprise_security.py -v --real-services && \
python -m pytest tests/e2e/staging/test_golden_path_ssot_validation_staging.py::TestGoldenPathSSOTValidationStaging::test_complete_golden_path_ssot_validation -v
```

---

## Test Environment Setup

### Prerequisites
```bash
# Ensure staging environment access
export TEST_ENV=staging

# Verify staging connectivity
curl -s https://backend.staging.netrasystems.ai/health

# Check auth service availability
curl -s https://auth.staging.netrasystems.ai/health
```

### Test Configuration
```bash
# Set test environment variables
export WEBSOCKET_URL="wss://backend.staging.netrasystems.ai/ws"
export AUTH_URL="https://auth.staging.netrasystems.ai"
export REAL_SERVICES=true
export NO_DOCKER=true
```

### Debug Mode Commands
```bash
# Run with verbose debugging
python -m pytest tests/e2e/staging/test_golden_path_websocket_baseline.py -v -s --tb=long

# Run with performance profiling
python -m pytest tests/e2e/staging/test_golden_path_ssot_validation_staging.py::TestGoldenPathSSOTValidationStaging::test_websocket_performance_improvement -v -s --durations=10
```

---

## Success Validation Checklist

### Phase 1 Complete (Baseline)
- [ ] All baseline tests pass with 100% success rate
- [ ] Golden Path validated in staging environment
- [ ] Performance baseline documented and saved
- [ ] Mission critical tests operational and consistent

### Phase 2 Complete (Migration)
- [ ] All migration validation tests pass
- [ ] Factory patterns working consistently
- [ ] Golden Path functional during migration process
- [ ] Rollback capability tested and verified

### Phase 3 Complete (SSOT)
- [ ] 100% SSOT compliance achieved and validated
- [ ] Enterprise security boundaries confirmed working
- [ ] Golden Path performance maintained or improved
- [ ] Business value delivery validated in staging

### Final Deployment Gate
- [ ] Mission critical tests pass consistently
- [ ] All 5 WebSocket events delivered correctly
- [ ] Multi-user isolation working perfectly
- [ ] Staging environment completely functional

This command reference provides the practical execution framework for safely migrating the WebSocket Manager to SSOT patterns while protecting the critical $500K+ ARR Golden Path functionality.