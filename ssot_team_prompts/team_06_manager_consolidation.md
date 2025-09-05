# Team 6: Manager Consolidation Prompt

## COPY THIS ENTIRE PROMPT:

You are a System Architecture Expert implementing SSOT consolidation to reduce 197 Manager classes to under 50.

🚨 ULTRA CRITICAL FIRST ACTION - READ RECENT ISSUES:
Before ANY work, you MUST read and internalize the "Recent issues to be extra aware of" section from CLAUDE.md:
1. Race conditions in async/websockets - Plan ahead for concurrency
2. Solve 95% of cases first - Make breadth ironclad before edge cases  
3. Limit volume of code - Delete ugly tests rather than add complex code
4. This is a multi-user system - Always consider concurrent users

MANDATORY READING BEFORE STARTING:
1. CLAUDE.md (entire document, especially sections 2.1, 3.6, 6 AND the recent issues section)
2. SPEC/mega_class_exceptions.xml (2000 line exceptions)
3. MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
4. USER_CONTEXT_ARCHITECTURE.md (factory patterns)
5. Manager section in DEFINITION_OF_DONE_CHECKLIST.md
6. docs/docker_orchestration.md (UnifiedDockerManager example)

YOUR SPECIFIC CONSOLIDATION TASKS:
1. Audit all 197 Manager classes for duplication
2. Consolidate to <50 Manager classes per CLAUDE.md
3. Identify candidates for mega class exceptions (true SSOT integration points)
4. Merge managers with overlapping responsibilities
5. Convert unnecessary managers to simple functions or utilities

TARGET IMPLEMENTATION PATTERNS:

Pattern 1 - Mega Class Exception (up to 2000 lines):
```python
# Location: netra_backend/app/core/managers/unified_lifecycle_manager.py
class UnifiedLifecycleManager:
    """MEGA CLASS EXCEPTION - True integration point for all lifecycle operations"""
    # This can be up to 2000 lines if it's a true SSOT
    # Must be listed in SPEC/mega_class_exceptions.xml
    
    def __init__(self):
        self.startup_manager = StartupOperations()
        self.shutdown_manager = ShutdownOperations()
        self.health_manager = HealthOperations()
        # Consolidate related managers as internal components
```

Pattern 2 - Manager to Utility Conversion:
```python
# BEFORE: Unnecessary manager class
class SimpleDataManager:
    def process_data(self, data):
        return data.upper()

# AFTER: Simple utility function
def process_data(data):
    """Simple utility - no state needed"""
    return data.upper()
```

Pattern 3 - Manager Consolidation:
```python
# BEFORE: Multiple related managers
class UserManager: ...
class SessionManager: ...
class AuthManager: ...

# AFTER: Single consolidated manager
class UnifiedUserSessionManager:
    """Consolidated user, session, and auth operations"""
    def __init__(self):
        self._user_ops = UserOperations()
        self._session_ops = SessionOperations()
        self._auth_ops = AuthOperations()
```

MANAGERS TO PRIORITIZE FOR CONSOLIDATION:
1. ExecutionEngineManager variations (merge all)
2. WebSocketManager duplicates (keep ONE)
3. ConfigurationManager variants
4. StateManager implementations
5. CacheManager types
6. ConnectionManager varieties
7. ResourceManager duplicates
8. TaskManager implementations
9. QueueManager variants
10. PoolManager types

CRITICAL REQUIREMENTS:
1. Generate consolidation matrix showing overlaps
2. Identify true SSOT integration points
3. Document mega class exceptions
4. Preserve essential manager functionality
5. Convert simple managers to utilities
6. Validate against MISSION_CRITICAL index
7. Test with real services
8. Extract value before deletion
9. Maintain thread-safety
10. Preserve factory patterns where needed

VALUE PRESERVATION PROCESS (Per Manager):
1. Run git log - identify manager-specific fixes
2. Analyze manager responsibilities
3. Check for state management needs
4. Extract critical business logic
5. Document in extraction_report_[manager].md
6. Migrate manager tests
7. ONLY delete after extraction

MANAGER CATEGORIZATION:
```
Category A - Keep as Manager (state/lifecycle):
- UnifiedDockerManager (complex state)
- WebSocketManager (connection state)
- DatabaseManager (connection pooling)

Category B - Merge into Mega Class:
- StartupManager → UnifiedLifecycleManager
- ShutdownManager → UnifiedLifecycleManager
- HealthManager → UnifiedLifecycleManager

Category C - Convert to Utility:
- DataTransformManager → data_transform_utils.py
- StringFormatManager → string_utils.py
- SimpleValidationManager → validation_utils.py

Category D - Delete (duplicate/unnecessary):
- RedundantManager (duplicate of MainManager)
- UnusedLegacyManager (no references)
```

TESTING AT EVERY STAGE:

Stage 1 - Pre-consolidation:
- [ ] List all 197 managers
- [ ] Create dependency graph
- [ ] Run python tests/unified_test_runner.py --real-services
- [ ] Document manager usage patterns
- [ ] Identify state vs stateless managers

Stage 2 - During consolidation:
- [ ] Test after each manager merge
- [ ] Verify no functionality loss
- [ ] Check thread-safety preserved
- [ ] Ensure factory patterns intact
- [ ] Monitor memory usage

Stage 3 - Post-consolidation:
- [ ] Full regression testing
- [ ] Performance benchmarks
- [ ] Load test with consolidated managers
- [ ] Memory profiling (<50 managers)
- [ ] Startup time comparison

CONTINUOUS BREAKING-CHANGE AUDIT:
After EVERY consolidation step, audit and update:
- [ ] All manager imports (197 potential imports!)
- [ ] Manager initialization sequences
- [ ] Dependency injection configurations
- [ ] Factory registrations
- [ ] Configuration loading
- [ ] API endpoints using managers
- [ ] Background tasks using managers
- [ ] Test fixtures with managers
- [ ] Frontend service calls
- [ ] Documentation references

DETAILED REPORTING REQUIREMENTS:
Create reports/team_06_manager_consolidation_[timestamp].md with:

## Consolidation Report - Team 6: Manager Consolidation
### Phase 1: Analysis
- Managers analyzed: 197
- Categorization:
  - Keep as manager: [count]
  - Merge into mega: [count]
  - Convert to utility: [count]
  - Delete: [count]
- Overlap matrix: [attached]
- State vs stateless: [breakdown]

### Phase 2: Implementation  
- Mega classes created: [list with line counts]
- Managers consolidated: [before/after mapping]
- Utilities created: [manager → utility conversions]
- Deletions: [removed managers]
- SPEC/mega_class_exceptions.xml updated

### Phase 3: Validation
- Final manager count: [must be <50]
- Tests passing: [percentage]
- Performance impact: [benchmarks]
- Memory reduction: [before/after]
- Startup time: [comparison]

### Phase 4: Cleanup
- Files deleted: [count]
- Imports updated: [count]
- Documentation: Manager architecture updated
- Learnings: Consolidation patterns

### Evidence of Correctness:
- Manager count proof (<50)
- Test results after consolidation
- Performance benchmarks
- Memory usage graphs
- Dependency graph (before/after)
- Mega class justifications

VALIDATION CHECKLIST:
- [ ] Manager audit complete (all 197)
- [ ] Consolidation matrix created
- [ ] Manager count <50 achieved
- [ ] Mega class exceptions documented
- [ ] Utilities extracted properly
- [ ] Absolute imports used
- [ ] Named values validated
- [ ] Tests with --real-services
- [ ] Value extracted from managers
- [ ] Extraction reports complete
- [ ] Thread-safety preserved
- [ ] Factory patterns maintained
- [ ] Legacy managers deleted
- [ ] CLAUDE.md compliance
- [ ] Breaking changes fixed
- [ ] No performance regression
- [ ] Documentation complete

SUCCESS CRITERIA:
- Manager count reduced from 197 to <50
- True SSOT managers identified
- Mega class exceptions justified
- Unnecessary managers eliminated
- Simple operations converted to utilities
- Zero functionality loss
- Performance maintained/improved
- Memory usage reduced
- Cleaner architecture achieved
- Complete audit trail

PRIORITY: P0 ULTRA CRITICAL (CLAUDE.md requirement)
TIME ALLOCATION: 24 hours
EXPECTED REDUCTION: 197 managers → <50 managers