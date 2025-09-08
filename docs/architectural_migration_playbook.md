# Architectural Migration Playbook

**Purpose:** Prevent incomplete architectural transitions that cause runtime failures  
**Root Cause Addressed:** WHY #5 from Five Whys Analysis - Lack of systematic approach to architectural migrations  
**Business Impact:** Prevents $500K+ ARR loss from broken chat functionality due to incomplete migrations  

---

## 📋 Executive Summary

This playbook addresses the root cause identified in the WebSocket bridge Five Whys analysis: **incomplete architectural migrations break critical business functionality**. The WebSocket bridge failure occurred because the migration from singleton to factory pattern was partial, leaving integration points broken.

**Key Principles:**
- **Contract-Driven Migrations:** Define and validate contracts before, during, and after migrations
- **Complete Consumer Analysis:** Identify ALL touchpoints of components being migrated
- **Phase-Based Validation:** Validate each migration phase to prevent runtime failures
- **Business Value Preservation:** Ensure migrations maintain or improve business value delivery

---

## 🎯 When to Use This Playbook

### Required for ALL Migrations Involving:
1. **Singleton → Factory Pattern Changes**
2. **Dependency Injection Pattern Updates** 
3. **Cross-Service Integration Changes**
4. **WebSocket/Event System Modifications**
5. **Agent Execution Pattern Updates**

### Risk Assessment Triggers:
- Migration affects >3 files
- Changes involve app.state components
- Impacts WebSocket events (90% of business value)
- Modifies dependency injection patterns
- Updates SSOT patterns

---

## 📊 Migration Risk Matrix

| Risk Level | Characteristics | Required Actions |
|------------|-----------------|------------------|
| **🚨 CRITICAL** | WebSocket events, Agent execution, Auth flows | Full playbook + Extended validation |
| **🔴 HIGH** | Cross-service dependencies, Factory patterns | Full playbook required |
| **🟡 MEDIUM** | Single service, Limited consumers | Core playbook steps |
| **🟢 LOW** | Internal refactoring, No external dependencies | Basic validation only |

---

## 🏗️ Migration Phases

### Phase 1: Pre-Migration Analysis
**Duration:** 2-4 hours  
**Purpose:** Understand complete scope and prevent incomplete migrations

#### 1.1 Component Dependency Analysis
```bash
# Generate component dependency map
python scripts/analyze_component_dependencies.py --component "ComponentName" --output "dependency_map.json"

# Example for WebSocket bridge migration:
python scripts/analyze_component_dependencies.py --component "AgentWebSocketBridge" --include-consumers
```

**Required Outputs:**
- [ ] Complete list of all component consumers
- [ ] Dependency graph showing integration points
- [ ] Risk assessment for each consumer
- [ ] Business impact analysis

#### 1.2 Contract Definition
Create explicit contracts for components being migrated:

```python
# Example: WebSocket bridge contract
@dataclass
class WebSocketBridgeContract:
    required_methods: List[str]
    initialization_dependencies: List[str]
    consumer_expectations: Dict[str, str]
    business_value_requirements: List[str]
```

**Template Location:** `/templates/migration_contract_template.py`

#### 1.3 Consumer Impact Assessment
For each identified consumer:
- [ ] Document current usage patterns
- [ ] Identify required changes
- [ ] Assess migration complexity
- [ ] Define validation criteria

### Phase 2: Migration Design
**Duration:** 1-2 hours  
**Purpose:** Design complete migration approach

#### 2.1 Migration Strategy Selection

**Factory Pattern Migration (Recommended for Singleton → Factory):**
```python
# Step 1: Create factory alongside singleton (parallel)
# Step 2: Update startup to configure factory
# Step 3: Update consumers one-by-one with validation
# Step 4: Remove singleton after all consumers migrated
```

**Big Bang Migration (Use only for low-risk changes):**
```python
# Step 1: Update all components simultaneously
# Step 2: Comprehensive testing
# Note: Higher risk, not recommended for critical business components
```

#### 2.2 Validation Strategy Design
- [ ] Define contract validation tests
- [ ] Create consumer integration tests  
- [ ] Plan rollback procedures
- [ ] Design monitoring/alerting for migration

### Phase 3: Implementation
**Duration:** Varies by complexity  
**Purpose:** Execute migration with validation at each step

#### 3.1 Parallel Implementation Pattern (Recommended)
```python
# Keep existing singleton working while building new factory
class LegacyComponent:
    # Keep existing functionality
    pass

class NewFactoryBasedComponent:
    # New factory-based implementation
    pass

# Startup can choose between them based on configuration
```

#### 3.2 Consumer Update Strategy
**One Consumer at a Time:**
1. Update single consumer to use new pattern
2. Run integration tests for that consumer
3. Validate business functionality preserved
4. Move to next consumer

**Benefits:**
- Isolated failure impact
- Easy rollback per consumer
- Incremental validation

#### 3.3 Validation Checkpoints
At each step:
```bash
# Run contract validation
python -c "from netra_backend.app.core.app_state_contracts import validate_app_state_contracts; print(validate_app_state_contracts(app.state))"

# Run consumer integration tests
python tests/integration/test_component_consumer_integration.py

# Run business value tests (WebSocket events, etc.)
python tests/mission_critical/test_websocket_agent_events_suite.py
```

### Phase 4: Validation & Rollout
**Duration:** 2-4 hours  
**Purpose:** Comprehensive validation before declaring migration complete

#### 4.1 Contract Compliance Testing
```bash
# Validate all contracts pass
python tests/integration/test_migration_contract_compliance.py

# Generate compliance report
python scripts/generate_migration_compliance_report.py --migration "ComponentName"
```

#### 4.2 Business Value Preservation Testing
Critical for WebSocket/Agent migrations:
```bash
# Test complete user flow
python tests/e2e/test_complete_user_agent_flow.py --with-websocket-events

# Validate all 5 critical WebSocket events
python tests/mission_critical/test_websocket_agent_events_suite.py
```

#### 4.3 Performance & Load Testing
```bash
# Ensure migration doesn't degrade performance
python tests/performance/test_migration_performance_impact.py
```

### Phase 5: Cleanup & Documentation
**Duration:** 1 hour  
**Purpose:** Remove legacy components and document changes

#### 5.1 Legacy Component Removal
Only after ALL validation passes:
- [ ] Remove legacy singleton implementations
- [ ] Clean up unused imports
- [ ] Update documentation

#### 5.2 Migration Documentation
- [ ] Update ADRs (Architecture Decision Records)
- [ ] Update component documentation
- [ ] Document lessons learned
- [ ] Update troubleshooting guides

---

## 🔧 Migration Tools & Templates

### Required Scripts
Location: `/scripts/migration/`

1. **`analyze_component_dependencies.py`** - Dependency analysis
2. **`generate_migration_plan.py`** - Auto-generate migration steps
3. **`validate_migration_contracts.py`** - Contract validation
4. **`rollback_migration.py`** - Emergency rollback procedures

### Required Templates
Location: `/templates/migration/`

1. **`migration_contract_template.py`** - Component contract definition
2. **`consumer_integration_test_template.py`** - Consumer validation tests
3. **`migration_adr_template.md`** - Architecture Decision Record template
4. **`migration_checklist_template.md`** - Phase checklist template

---

## ✅ Migration Checklist Template

### Pre-Migration (Required)
- [ ] **Dependency Analysis Complete:** All consumers identified and documented
- [ ] **Contracts Defined:** Component contracts explicitly defined and validated
- [ ] **Business Impact Assessed:** Revenue/user impact understood and accepted
- [ ] **Rollback Plan Created:** Emergency rollback procedures documented
- [ ] **Timeline Approved:** Migration timeline fits business requirements

### During Migration (Required)  
- [ ] **Phase Validation:** Each phase validated before proceeding to next
- [ ] **Consumer Integration Tests:** Each consumer validated individually
- [ ] **Contract Compliance:** Contracts validated at each step
- [ ] **Business Value Preserved:** Critical functionality (WebSocket events) working
- [ ] **Performance Maintained:** No degradation in system performance

### Post-Migration (Required)
- [ ] **Complete Validation:** All integration tests passing
- [ ] **Legacy Cleanup:** Old implementations removed and cleaned up
- [ ] **Documentation Updated:** ADRs, docs, and troubleshooting guides current
- [ ] **Monitoring Configured:** Alerts and monitoring for new patterns
- [ ] **Team Training:** Team understands new patterns and troubleshooting

---

## 🚨 Failure Response Procedures

### If Migration Validation Fails

#### Immediate Actions (< 5 minutes):
1. **Stop Migration:** Do not proceed to next phase
2. **Assess Impact:** Determine if rollback needed immediately
3. **Notify Stakeholders:** Alert team to migration issues

#### Investigation Phase (< 30 minutes):
1. **Analyze Failure:** Use validation reports to understand root cause
2. **Check Business Impact:** Verify WebSocket events, user flows still working
3. **Decide Path:** Fix-forward vs rollback

#### Resolution Phase:
**Fix-Forward (Preferred):**
- Fix identified issues
- Re-run validation
- Proceed with migration

**Rollback (If fix complex):**
- Use rollback scripts
- Restore previous state
- Schedule migration retry

### Emergency Rollback Procedures
```bash
# Emergency rollback for critical failures
python scripts/migration/emergency_rollback.py --component "ComponentName" --to-state "pre-migration"

# Validate rollback successful
python tests/integration/test_post_rollback_validation.py
```

---

## 📚 Common Migration Patterns

### Singleton to Factory Pattern
**Use Case:** WebSocket bridge, Agent registry, Tool dispatcher

**Pattern:**
```python
# Step 1: Create factory alongside singleton
class ComponentFactory:
    def __init__(self, dependencies):
        self._dependencies = dependencies
    
    def create_component(self, user_context):
        return Component(user_context, self._dependencies)

# Step 2: Update startup to configure factory
def configure_startup(app):
    factory = ComponentFactory(dependencies=app.state.dependencies)
    app.state.component_factory = factory
    
    # Keep singleton for legacy consumers
    app.state.legacy_component = Component.create_singleton()

# Step 3: Update consumers one-by-one
async def updated_consumer():
    factory = get_component_factory()
    component = factory.create_component(user_context)
    # Use component...

# Step 4: Remove singleton after all consumers updated
```

### Cross-Service Integration Updates
**Use Case:** Auth service integration, Database connection updates

**Pattern:**
```python
# Step 1: Create abstraction layer
class ServiceIntegrationAdapter:
    def __init__(self, old_service, new_service):
        self._old_service = old_service
        self._new_service = new_service
        self._use_new = False  # Feature flag
    
    async def perform_operation(self, params):
        if self._use_new:
            return await self._new_service.operation(params)
        else:
            return await self._old_service.operation(params)

# Step 2: Gradually enable new service per consumer
# Step 3: Remove old service after full migration
```

---

## 🎯 Success Criteria

### Migration Considered Successful When:
1. **All Contracts Valid:** App state contracts pass validation
2. **All Consumers Working:** Integration tests pass for all consumers
3. **Business Value Preserved:** Critical functionality (WebSocket events) working
4. **Performance Maintained:** No significant performance degradation
5. **Legacy Removed:** Old implementations cleaned up
6. **Documentation Current:** All docs reflect new architecture

### Key Metrics to Track:
- **Contract Validation Pass Rate:** Should be 100%
- **Integration Test Pass Rate:** Should be 100%  
- **WebSocket Event Delivery Rate:** Should maintain 100% (for WebSocket migrations)
- **Migration Duration:** Track to improve future migrations
- **Rollback Rate:** Should be <10% for well-planned migrations

---

## 📖 Learning from Past Migrations

### WebSocket Bridge Migration (2025-09-07)
**What Went Wrong:**
- Incomplete consumer analysis missed supervisor factory
- No contract validation during migration
- No integration tests for complete startup flow

**What We Fixed:**
- Created comprehensive dependency analysis
- Implemented contract-driven validation
- Added integration tests covering complete flow

**Lessons Learned:**
- WebSocket events are critical business value - test extensively
- Startup sequence validation prevents runtime failures
- Contract-driven development catches integration issues early

### Key Success Factors:
1. **Complete Consumer Analysis:** Don't miss any integration points
2. **Business Value Focus:** Preserve chat functionality above all
3. **Phase-by-Phase Validation:** Catch issues early
4. **Contract-Driven Development:** Explicit contracts prevent mismatches
5. **Real Integration Tests:** No mocks for critical business paths

---

**Remember: The goal of architectural migration is to improve system quality while preserving business value. When in doubt, prioritize business value preservation over architectural purity.**