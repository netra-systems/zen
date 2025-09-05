# Team 4: Test SSOT Migration & Production Method Enforcement

## COPY THIS ENTIRE PROMPT:

You are a Test Architecture Expert eliminating test code that recreates production logic instead of using SSOT methods.

🚨 **ULTRA CRITICAL FIRST ACTION** - READ THIS FROM CLAUDE.md:
**"Update tests to SSOT methods. NEVER re-create legacy code to pass old tests!"**

This is your PRIME DIRECTIVE. Tests that duplicate production logic are worse than no tests at all.

## MANDATORY READING BEFORE STARTING:
1. **CLAUDE.md** (Rule #45 on test SSOT)
2. **SSOT_ANTI_PATTERNS_ANALYSIS.md** (Anti-Pattern #4: Test Isolation)
3. **SPEC/learnings/ssot_violations_remediation.xml** (test mock boundaries)
4. **TEST_ARCHITECTURE_VISUAL_OVERVIEW.md** (test layers)
5. **DEFINITION_OF_DONE_CHECKLIST.md** (test requirements)
6. **tests/unified_test_runner.py** (test infrastructure)

## YOUR SPECIFIC MISSION:

### Current Anti-Pattern (Tests Recreating Logic):
```python
# VIOLATION - Test reimplements production validation
class TestConfigValidation:
    def validate_jwt_secret(self, secret):
        # This duplicates production logic!
        return len(secret) > 32 and secret != "default"
    
    def test_jwt_validation(self):
        # Using test's own validation, not production
        assert self.validate_jwt_secret("test_secret_123...")
```

### Target SSOT Pattern:
```python
# CORRECT - Test uses production SSOT
from netra_backend.app.core.managers import UnifiedConfigurationManager

class TestConfigValidation:
    def test_jwt_validation(self):
        # Use ACTUAL production validation
        config_manager = UnifiedConfigurationManager()
        result = config_manager.validate_jwt_secret("test_secret_123...")
        assert result.is_valid
```

## PHASE 1: AUDIT TEST VIOLATIONS (Hours 0-10)

### Find Tests Recreating Production Logic:

#### Pattern 1: Validation Logic Duplication
```bash
# Find test files with validation methods
grep -r "def validate" tests/ --include="*.py" | grep -v import
grep -r "def check_" tests/ --include="*.py" | grep -v import
```

#### Pattern 2: Business Logic Recreation
```bash
# Find tests implementing business rules
grep -r "class.*Manager" tests/ --include="*.py"
grep -r "class.*Service" tests/ --include="*.py"
grep -r "class.*Handler" tests/ --include="*.py"
```

#### Pattern 3: Configuration Logic Duplication
```bash
# Find tests with hardcoded config logic
grep -r "DATABASE_URL.*=" tests/ --include="*.py"
grep -r "JWT_SECRET.*=" tests/ --include="*.py"
grep -r "os\.environ\[" tests/ --include="*.py"
```

### Document Violations by Category:

```markdown
# Test SSOT Violations Audit

## Category 1: Validation Logic (HIGH PRIORITY)
- tests/unit/test_config_validation.py - Recreates JWT validation
- tests/unit/test_database_url.py - Duplicates URL validation
- tests/integration/test_auth.py - Reimplements OAuth validation

## Category 2: Business Logic (MEDIUM PRIORITY)
- tests/agents/test_triage.py - Recreates triage decision logic
- tests/services/test_billing.py - Duplicates pricing calculations

## Category 3: Mock Boundaries (LOW PRIORITY)
- Legitimate mocks that should remain
- External service mocks (OK to keep)
```

## PHASE 2: MIGRATION STRATEGY (Hours 10-20)

### Step 1: Identify Production SSOT Methods

For each violation, find the production SSOT:
```python
# Violation: Test recreates JWT validation
# Find production SSOT:
production_module = "netra_backend.app.core.security"
production_method = "validate_jwt_secret"
```

### Step 2: Create Migration Map

```python
# migration_map.py
TEST_TO_PRODUCTION_SSOT = {
    "tests/unit/test_config.py::validate_jwt": 
        "netra_backend.app.core.managers.UnifiedConfigurationManager.validate_jwt_secret",
    
    "tests/unit/test_database.py::build_database_url":
        "netra_backend.app.db.database_manager.get_database_url",
    
    "tests/agents/test_triage.py::triage_logic":
        "netra_backend.app.agents.triage.UnifiedTriageAgent.process",
}
```

### Step 3: Implement Test Helpers

```python
# tests/helpers/ssot_helpers.py
"""
Helper functions that call production SSOT methods.
Tests should use these instead of reimplementing logic.
"""

from netra_backend.app.core.managers import UnifiedConfigurationManager
from netra_backend.app.agents.supervisor import MasterAgentRegistry
from shared.isolated_environment import IsolatedEnvironment

class SSOTTestHelper:
    """Centralized access to production SSOT methods"""
    
    def __init__(self):
        self.config_manager = UnifiedConfigurationManager()
        self.registry = MasterAgentRegistry()
        self.env = IsolatedEnvironment()
    
    def validate_config(self, key: str, value: str) -> bool:
        """Use production config validation"""
        return self.config_manager.validate_config(key, value)
    
    def create_agent(self, agent_type: str, context):
        """Use production agent creation"""
        return self.registry.create_agent_for_user(
            agent_type, 
            context.user_id,
            context
        )
    
    def get_env_var(self, key: str, required: bool = False):
        """Use production environment access"""
        return self.env.get_env(key, required=required)
```

### Step 4: Migrate Tests

#### Before (VIOLATION):
```python
class TestDatabaseConnection:
    def build_database_url(self, host, port, db):
        # Recreating production logic!
        return f"postgresql://{host}:{port}/{db}"
    
    def test_database_url(self):
        url = self.build_database_url("localhost", 5432, "test")
        assert url == "postgresql://localhost:5432/test"
```

#### After (CORRECT):
```python
from tests.helpers.ssot_helpers import SSOTTestHelper
from netra_backend.app.db.database_manager import DatabaseManager

class TestDatabaseConnection:
    def setup_method(self):
        self.helper = SSOTTestHelper()
        self.db_manager = DatabaseManager()
    
    def test_database_url(self):
        # Use production method
        url = self.db_manager.build_database_url("localhost", 5432, "test")
        assert url == "postgresql://localhost:5432/test"
```

## CRITICAL REQUIREMENTS:

### 1. Mock Boundaries (IMPORTANT)
```python
# LEGITIMATE MOCKS (ALLOWED):
# - External services (OpenAI, databases)
# - Network calls
# - File system for unit tests
# - Time/randomness for determinism

# ILLEGITIMATE MOCKS (FORBIDDEN):
# - Business logic
# - Validation rules  
# - Configuration logic
# - Agent behavior
```

### 2. Test Fixtures Using SSOT
```python
@pytest.fixture
def config_manager():
    """Provide production config manager"""
    return UnifiedConfigurationManager()

@pytest.fixture
def agent_registry():
    """Provide production registry"""
    return MasterAgentRegistry()

# Tests use production fixtures
def test_agent_creation(agent_registry):
    agent = agent_registry.create_agent("triage", context)
    assert agent is not None
```

### 3. Real Service Testing
```python
# When possible, test with real services
@pytest.mark.real_services
def test_full_agent_flow():
    """Test with real LLM, database, redis"""
    # No mocks - actual services
    result = execute_agent_with_real_services()
    assert result.success
```

## VALIDATION PROCESS:

### Pre-Migration Check:
```bash
# Count current violations
python scripts/detect_test_ssot_violations.py --report

# Example output:
# Found 127 test methods recreating production logic
# - 45 validation recreations
# - 62 business logic duplications
# - 20 configuration reimplementations
```

### Post-Migration Validation:
```bash
# Verify all tests use SSOT
python scripts/validate_test_ssot_compliance.py

# Run all tests with production methods
python tests/unified_test_runner.py --real-services

# Check for regressions
python tests/unified_test_runner.py --compare-before-after
```

## ROLLBACK PLAN:

### Safe Migration:
1. **Don't delete old tests immediately**
2. **Run both old and new tests in parallel**
3. **Compare results for discrepancies**
4. **Only delete after verification**

### Rollback Procedure:
```bash
# If tests fail after migration
git stash  # Save current work
git checkout HEAD~1  # Previous commit
python tests/unified_test_runner.py  # Verify tests pass

# Fix issues and retry
git stash pop
# Address specific failures
```

## SUCCESS METRICS:

### Quantitative:
- **0** tests recreating production validation
- **0** tests with duplicate business logic
- **100%** test compliance with SSOT
- **No** decrease in test coverage

### Qualitative:
- Tests fail when production logic changes (good!)
- No false positives from divergent logic
- Clearer test intent
- Easier maintenance

## COMMON PITFALLS:

1. **Over-Mocking**: Don't mock production SSOT methods
2. **Test-Only Logic**: Delete it, don't migrate it
3. **Legacy Test Protection**: Don't preserve bad tests
4. **Performance**: Production methods may be slower
5. **Circular Dependencies**: Watch imports

## SPECIAL CASES:

### Case 1: Performance-Critical Tests
```python
# If production method is too slow for unit tests
@pytest.mark.unit
def test_validation_fast():
    # Use simplified production method
    validator = ProductionValidator(fast_mode=True)
    assert validator.check(data)
```

### Case 2: Isolation Requirements
```python
# When test needs complete isolation
def test_with_isolation():
    with IsolatedTestContext() as ctx:
        # Still use production methods
        manager = UnifiedConfigurationManager(context=ctx)
        result = manager.validate(data)
```

## DELIVERABLES:

1. **Violation Audit Report**: All tests recreating logic
2. **Migration Map**: Test-to-production method mapping
3. **SSOT Test Helpers**: Centralized test utilities
4. **Migration Scripts**: Automated test updates
5. **Compliance Report**: Before/after metrics
6. **Test Documentation**: Updated test guidelines

## COORDINATION:

### Dependencies on Other Teams:
- **Team 1**: Tests need IsolatedEnvironment
- **Team 2**: Tests use consolidated managers
- **Team 3**: Tests interact with unified registry

### Provide to Other Teams:
- List of production methods tests rely on
- Test fixture updates
- Breaking test changes

**YOU HAVE 20 HOURS TO COMPLETE THIS MISSION. Remember: Tests that lie are worse than no tests. Every test that recreates production logic is a ticking time bomb. Eliminate them all. ULTRA THINK DEEPLY ALWAYS.**