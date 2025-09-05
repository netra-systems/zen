# Team 2: Manager Class Consolidation

## COPY THIS ENTIRE PROMPT:

You are a System Architecture Expert implementing Manager class consolidation to eliminate SSOT violations.

🚨 **ULTRA CRITICAL FIRST ACTION** - READ RECENT ISSUES:
Before ANY work, you MUST read and internalize the "Recent issues to be extra aware of" section from CLAUDE.md:
1. Race conditions in async/websockets - Plan ahead for concurrency
2. Solve 95% of cases first - Make breadth ironclad before edge cases  
3. Limit volume of code - Delete ugly tests rather than add complex code
4. This is a multi-user system - Always consider concurrent users

## MANDATORY READING BEFORE STARTING:
1. **CLAUDE.md** (section 3.6 on MRO Analysis, mega_class_exceptions)
2. **SSOT_ANTI_PATTERNS_ANALYSIS.md** (Anti-Pattern #2: Manager Proliferation)
3. **SPEC/mega_class_exceptions.xml** (approved SSOT exceptions)
4. **SPEC/learnings/ssot_consolidation_20250825.xml**
5. **docs/shared_library_pattern.md** (shared vs service-specific)
6. **USER_CONTEXT_ARCHITECTURE.md** (factory patterns)

## YOUR SPECIFIC MISSION:

### Current Anti-Pattern (20+ Manager classes):
```python
# VIOLATION - Duplicate manager implementations
class ServiceAConfigManager:
    def get_database_url(self): ...

class ServiceBConfigManager:
    def get_database_url(self): ...  # Duplicate logic

class ServiceCDatabaseManager:
    def connect(self): ...  # Yet another pattern
```

### Target SSOT Pattern:
```python
# CORRECT - Consolidated managers with clear boundaries
class UnifiedConfigurationManager:  # MEGA CLASS EXCEPTION (2000 lines)
    """SSOT for ALL configuration operations"""
    
class UnifiedStateManager:  # Legitimate service boundary
    """SSOT for state management across services"""
    
# Shared utilities (not managers)
class DatabaseConnectionPool:  # Utility, not manager
    """Shared database connection logic"""
```

## PHASE 1: MRO ANALYSIS (Hours 0-8)

### Generate Comprehensive MRO Report:
```bash
# Run MRO analysis script
python scripts/generate_registry_mro_report.py --all-managers > mro_report.md

# Manual analysis for managers not caught by script
grep -r "class.*Manager" . --include="*.py" | head -50
```

### Document Current Manager Topology:
```markdown
# Manager MRO Analysis Report
## Current Hierarchy (BEFORE)

### Configuration Managers (7 implementations)
- UnifiedConfigurationManager (MEGA CLASS - KEEP)
  - ServiceAConfigManager (DUPLICATE - DELETE)
  - ServiceBConfigManager (DUPLICATE - DELETE)
  
### State Managers (5 implementations)
- UnifiedStateManager (KEEP)
  - LegacyStateManager (DELETE)
  
### Database Managers (8 implementations)
- [Document all with inheritance chains]
```

## PHASE 2: CONSOLIDATION PLAN (Hours 8-12)

### Manager Categories & Decisions:

#### Category 1: KEEP (Legitimate SSOT)
- **UnifiedConfigurationManager** - MEGA CLASS exception
- **UnifiedStateManager** - Cross-service state
- **UnifiedDockerManager** - Docker operations
- **WebSocketManager** - WebSocket SSOT

#### Category 2: CONSOLIDATE (Duplicates)
- Config managers → UnifiedConfigurationManager
- State managers → UnifiedStateManager
- Database managers → Shared utility

#### Category 3: DELETE (Pure Duplicates)
- Any manager with <100 lines of unique logic
- Test-only managers (use production SSOT)
- Legacy managers with "backup" in name

#### Category 4: CONVERT (Not Really Managers)
- Rename to utilities/helpers
- Move to shared/ if cross-service
- Keep in service if service-specific

## PHASE 3: IMPLEMENTATION (Hours 12-20)

### Step 1: Create Consolidation Branches
```bash
git checkout -b manager-consolidation-base
git checkout -b consolidate-config-managers
git checkout -b consolidate-state-managers
git checkout -b consolidate-database-managers
```

### Step 2: Consolidation Process Per Manager Type

#### Configuration Manager Consolidation:
```python
# UnifiedConfigurationManager becomes SSOT
class UnifiedConfigurationManager:
    """MEGA CLASS EXCEPTION - Up to 2000 lines
    Consolidates:
    - DashboardConfigManager
    - DataSubAgentConfigurationManager
    - IsolationDashboardConfigManager
    - LLMManagerConfig
    """
    
    def __init__(self, environment: Environment):
        self.env = IsolatedEnvironment()
        self._configs = {}
        self._load_all_configs()
    
    # Migrate unique methods from each manager
    def get_dashboard_config(self): ...  # From DashboardConfigManager
    def get_llm_config(self): ...  # From LLMManagerConfig
    def get_data_agent_config(self): ...  # From DataSubAgentConfigurationManager
```

#### State Manager Consolidation:
```python
class UnifiedStateManager:
    """SSOT for all state management
    Thread-safe, supports concurrent access
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._state_store = {}
        self._user_contexts = {}
    
    @contextmanager
    def user_context(self, user_id: str):
        """Factory pattern for user isolation"""
        with self._lock:
            if user_id not in self._user_contexts:
                self._user_contexts[user_id] = UserContext()
            yield self._user_contexts[user_id]
```

### Step 3: Migration Strategy

#### For Each Manager to Consolidate:
1. **Extract Unique Logic**:
   ```python
   # Document unique methods
   # ServiceAConfigManager unique methods:
   # - get_service_a_specific_config()
   # - validate_service_a_requirements()
   ```

2. **Add to Unified Manager**:
   ```python
   class UnifiedConfigurationManager:
       # Add service-specific section
       def get_service_a_config(self):
           """Migrated from ServiceAConfigManager"""
           return self._configs.get('service_a', {})
   ```

3. **Update Imports**:
   ```python
   # Before
   from services.service_a.config import ServiceAConfigManager
   
   # After  
   from netra_backend.app.core.managers import UnifiedConfigurationManager
   ```

4. **Delete Original**:
   ```bash
   # After verification
   git rm services/service_a/config.py
   ```

## CRITICAL REQUIREMENTS:

### 1. Preserve User Isolation
```python
# Managers MUST support factory patterns
class UnifiedManager:
    def create_for_user(self, user_context: UserContext):
        """Factory method for user isolation"""
        return UserScopedManager(self, user_context)
```

### 2. Thread Safety
```python
# All shared managers MUST be thread-safe
class UnifiedStateManager:
    def __init__(self):
        self._lock = threading.RLock()
    
    def update_state(self, key, value):
        with self._lock:
            self._state[key] = value
```

### 3. Backward Compatibility
```python
# Provide compatibility shims during migration
class ServiceAConfigManager:
    """DEPRECATED - Use UnifiedConfigurationManager
    Compatibility shim for gradual migration
    """
    def __init__(self):
        logger.warning("ServiceAConfigManager is deprecated")
        self._unified = UnifiedConfigurationManager()
    
    def __getattr__(self, name):
        return getattr(self._unified, name)
```

### 4. WebSocket Event Preservation
- Ensure WebSocketManager remains functional
- Test all 5 critical events after consolidation
- No changes to event emission patterns

## VALIDATION PROCESS:

### Pre-Consolidation Metrics:
```python
# Capture before metrics
metrics = {
    "manager_count": len(find_all_managers()),
    "total_loc": count_manager_lines(),
    "duplicate_methods": find_duplicate_methods(),
    "memory_usage": measure_manager_memory()
}
```

### Post-Consolidation Validation:
- [ ] Manager count reduced by 50%+ 
- [ ] No functionality regression
- [ ] All tests passing
- [ ] WebSocket events flowing
- [ ] Memory usage reduced
- [ ] No circular imports

### Integration Testing:
```bash
# Test with real services after each consolidation
python tests/unified_test_runner.py --real-services

# Specific manager tests
python tests/mission_critical/test_manager_consolidation.py
```

## ROLLBACK PLAN:

### Incremental Rollback:
1. Each manager consolidation is atomic
2. Git tags at each successful consolidation
3. Compatibility shims allow gradual migration
4. Feature flags for new vs old managers

### Emergency Rollback:
```bash
# If critical failure
git checkout manager-consolidation-base
git branch -D consolidate-config-managers  # Delete failed branch

# Restart with lessons learned
```

## SUCCESS METRICS:

### Quantitative:
- **<10** total Manager classes (from 20+)
- **0** duplicate get_database_url implementations
- **50%+** reduction in manager code
- **30%+** memory reduction

### Qualitative:
- Clear SSOT for each domain
- No ambiguity about which manager to use
- Simplified import structure
- Better test coverage

## COMMON PITFALLS:

1. **Over-Consolidation**: Don't merge legitimate service boundaries
2. **Breaking Isolation**: Preserve user context isolation
3. **Silent Breakage**: Test thoroughly after each consolidation
4. **Import Cycles**: Watch for circular dependencies
5. **Thread Safety**: Don't introduce race conditions

## DELIVERABLES:

1. **MRO Analysis Report**: Complete manager hierarchy
2. **Consolidation Plan**: Which managers merge where
3. **Migration Scripts**: Automated import updates
4. **Compatibility Shims**: For gradual migration
5. **Test Suite**: Manager-specific tests
6. **Performance Report**: Before/after metrics

## TEAM COORDINATION:

### Dependencies on Other Teams:
- **Team 1**: Environment configs use managers
- **Team 3**: Registry may use state managers
- **Team 4**: Tests need manager updates

### Provide to Other Teams:
- List of consolidated managers
- New import paths
- Migration timeline
- Breaking changes list

**YOU HAVE 20 HOURS TO COMPLETE THIS MISSION. Remember: Manager proliferation is a cancer that spreads through the codebase. Your consolidation work is critical for system stability. ULTRA THINK DEEPLY ALWAYS.**