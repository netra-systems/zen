# SSOT Test Runner Remediation: Implementation Guide

**MISSION CRITICAL:** Step-by-step implementation guide for safe SSOT test runner remediation  
**Golden Path Protection:** Maintains $500K+ ARR chat functionality throughout process  
**Created:** 2025-01-09  

---

## Quick Start: Phase 1 Implementation

### Immediate Actions Required

1. **Run Baseline Validation**
```bash
# Establish current system state
python tests/mission_critical/test_ssot_test_runner_enforcement.py
python tests/unified_test_runner.py --execution-mode fast_feedback
python docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md  # Review critical requirements
```

2. **Create Enhanced UnifiedTestRunner Features**
```bash
# Back up current UnifiedTestRunner
cp tests/unified_test_runner.py tests/unified_test_runner.py.backup

# Apply Phase 1 enhancements (see detailed implementation below)
```

3. **Implement Critical Infrastructure Wrappers**
```bash
# Start with highest-risk violations
# CI/CD scripts first, then mission-critical test runners
```

---

## Phase 1: Critical Infrastructure (Week 1)

### Step 1.1: Enhance UnifiedTestRunner (Day 1-2)

**File:** `tests/unified_test_runner.py`

**Add Custom Suite Support:**
```python
# Add after existing argument parsing section (around line 200)

parser.add_argument(
    "--custom-suite",
    choices=["critical_agents", "websocket_validation", "audit", "deployment"],
    help="Run predefined custom test suite"
)

parser.add_argument(
    "--legacy-mode", 
    help="Execute in legacy compatibility mode for specific script"
)

def run_custom_suite(suite_name, args):
    """Execute predefined test suites with specialized configuration"""
    logger.info(f"🎯 Running custom suite: {suite_name}")
    
    suites = {
        "critical_agents": {
            "categories": ["agent", "mission_critical"],
            "markers": "critical_agent",
            "real_services": True,
            "sequential": True,
            "memory_limit": "8GB",
            "fast_fail": True
        },
        "websocket_validation": {
            "categories": ["websocket", "integration"],
            "real_services": True,
            "fast_fail": True,
            "markers": "websocket"
        },
        "audit": {
            "categories": ["smoke", "unit", "integration"],
            "coverage": True,
            "html_output": True,
            "real_services": True
        },
        "deployment": {
            "categories": ["smoke", "startup", "api"],
            "real_services": True,
            "fast_fail": True,
            "timeout": 300
        }
    }
    
    if suite_name not in suites:
        raise ValueError(f"Unknown custom suite: {suite_name}")
    
    suite_config = suites[suite_name]
    
    # Apply suite configuration to args
    for key, value in suite_config.items():
        if hasattr(args, key):
            setattr(args, key, value)
    
    logger.info(f"📋 Suite configuration: {suite_config}")
    return suite_config

def handle_legacy_mode(script_name, original_args):
    """Handle legacy script compatibility"""
    logger.info(f"🔄 Legacy compatibility mode: {script_name}")
    
    legacy_configs = {
        "run_critical_agent_tests": {
            "custom_suite": "critical_agents",
            "memory_management": True
        },
        "run_websocket_validation": {
            "custom_suite": "websocket_validation"
        },
        "failure_analysis": {
            "custom_suite": "audit",
            "collect_artifacts": True
        },
        "run_ssot_orchestration_tests": {
            "categories": ["mission_critical"],
            "markers": "ssot"
        },
        "run_isolation_tests": {
            "categories": ["mission_critical"],
            "markers": "isolation"
        }
    }
    
    if script_name not in legacy_configs:
        logger.warning(f"⚠️ Unknown legacy script: {script_name}")
        return {}
    
    config = legacy_configs[script_name]
    logger.info(f"📝 Legacy configuration applied: {config}")
    return config
```

**Add to main execution logic (around line 400):**
```python
# Add after argument parsing, before existing execution logic

if args.custom_suite:
    suite_config = run_custom_suite(args.custom_suite, args)
    logger.info(f"✅ Custom suite '{args.custom_suite}' configured")

if args.legacy_mode:
    legacy_config = handle_legacy_mode(args.legacy_mode, sys.argv[1:])
    
    # Apply legacy configuration
    for key, value in legacy_config.items():
        if hasattr(args, key):
            setattr(args, key, value)
    
    # Show deprecation warning
    logger.warning("⚠️ DEPRECATION WARNING:")
    logger.warning(f"Legacy mode '{args.legacy_mode}' is deprecated.")
    logger.warning("Use: python tests/unified_test_runner.py --custom-suite <suite>")
    logger.warning("Or use direct arguments for full control.")
```

### Step 1.2: Create CI/CD Wrappers (Day 3)

**File:** `.github/scripts/failure_analysis_wrapper.py`
```python
#!/usr/bin/env python3
"""
SSOT Compatibility Wrapper for failure_analysis.py

DEPRECATED: Use 'python tests/unified_test_runner.py --custom-suite audit' directly
"""

import sys
import warnings
import subprocess
from pathlib import Path

def main():
    warnings.warn(
        "failure_analysis.py test execution is deprecated. "
        "Use: python tests/unified_test_runner.py --custom-suite audit",
        DeprecationWarning,
        stacklevel=2
    )
    
    project_root = Path(__file__).parent.parent.parent
    
    # Convert arguments for audit suite
    audit_args = ["--custom-suite", "audit"]
    
    # Preserve key arguments
    for arg in sys.argv[1:]:
        if arg.startswith("--") and arg in ["--verbose", "--coverage", "--real-services"]:
            audit_args.append(arg)
    
    cmd = [
        sys.executable, 
        str(project_root / "tests" / "unified_test_runner.py")
    ] + audit_args
    
    print(f"🔄 SSOT: Executing via UnifiedTestRunner: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
```

**Update original:** `.github/scripts/failure_analysis.py`
```python
# Add at the end of the file, before if __name__ == "__main__":

def run_tests_via_unified_runner(test_args):
    """SSOT: Route all test execution through UnifiedTestRunner"""
    import warnings
    import subprocess
    
    warnings.warn(
        "Direct pytest execution deprecated. Use: python tests/unified_test_runner.py --custom-suite audit",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Convert to UnifiedTestRunner call
    cmd = ["python", "tests/unified_test_runner.py", "--custom-suite", "audit"]
    cmd.extend(test_args)
    
    return subprocess.run(cmd, capture_output=True, text=True)

# Replace any direct pytest.main() calls with:
# result = run_tests_via_unified_runner(pytest_args)
```

### Step 1.3: Mission Critical Test Wrappers (Day 4)

**File:** `tests/mission_critical/run_isolation_tests_wrapper.py`
```python
#!/usr/bin/env python3
"""
SSOT Wrapper for Isolation Tests

Maintains backwards compatibility while using UnifiedTestRunner
"""

import sys
import subprocess
import warnings
from pathlib import Path

def main():
    warnings.warn(
        "run_isolation_tests.py is deprecated. "
        "Use: python tests/unified_test_runner.py --categories mission_critical --markers isolation",
        DeprecationWarning
    )
    
    project_root = Path(__file__).parent.parent.parent
    
    cmd = [
        sys.executable,
        str(project_root / "tests" / "unified_test_runner.py"),
        "--categories", "mission_critical", 
        "--markers", "isolation",
        "--real-services",
        "--fast-fail"
    ]
    
    # Preserve original arguments
    cmd.extend(sys.argv[1:])
    
    print(f"🔄 SSOT: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
```

### Step 1.4: Validation (Day 5)

**Test all Phase 1 changes:**
```bash
# Test CI/CD wrapper functionality
python .github/scripts/failure_analysis_wrapper.py --verbose

# Test mission critical wrapper
python tests/mission_critical/run_isolation_tests_wrapper.py --dry-run

# Test enhanced UnifiedTestRunner
python tests/unified_test_runner.py --custom-suite critical_agents --dry-run
python tests/unified_test_runner.py --custom-suite websocket_validation --dry-run

# Validate Golden Path still works
python tests/unified_test_runner.py --execution-mode fast_feedback

# Run compliance check
python tests/mission_critical/test_ssot_test_runner_enforcement.py
```

---

## Phase 2: High-Risk Components (Week 2)

### Step 2.1: Feature Flag Implementation

**File:** `shared/feature_flags.py` (create if doesn't exist)
```python
"""
Feature Flags for SSOT Test Runner Migration
"""

from shared.isolated_environment import get_env

class TestRunnerFeatureFlags:
    """Feature flags for test runner migration"""
    
    @staticmethod
    def enable_ssot_test_runners() -> bool:
        """Check if SSOT test runners should be used"""
        return get_env("ENABLE_SSOT_TEST_RUNNERS", "false").lower() == "true"
    
    @staticmethod
    def enable_legacy_fallback() -> bool:
        """Check if legacy fallback is enabled"""
        return get_env("ENABLE_LEGACY_TEST_FALLBACK", "true").lower() == "true"
```

### Step 2.2: E2E Test Migration

**File:** `tests/e2e/run_chat_ui_tests.py` (modify existing)
```python
# Add at the top after imports
from shared.feature_flags import TestRunnerFeatureFlags

def execute_tests(test_args):
    """Execute tests with feature flag support"""
    
    if TestRunnerFeatureFlags.enable_ssot_test_runners():
        return execute_via_unified_runner(test_args)
    elif TestRunnerFeatureFlags.enable_legacy_fallback():
        print("⚠️ Using legacy execution method")
        return execute_legacy_method(test_args)
    else:
        raise RuntimeError("No test execution method available")

def execute_via_unified_runner(test_args):
    """Execute via SSOT UnifiedTestRunner"""
    import subprocess
    
    cmd = [
        "python", "tests/unified_test_runner.py",
        "--categories", "e2e", "frontend",
        "--real-services",
        "--cypress-headed" if "--headed" in test_args else ""
    ]
    
    # Filter and convert arguments
    unified_args = convert_e2e_args(test_args)
    cmd.extend(unified_args)
    
    return subprocess.run(cmd)

def execute_legacy_method(test_args):
    """Legacy execution method (original implementation)"""
    # Keep original implementation as fallback
    pass

# Replace main execution with:
if __name__ == "__main__":
    import sys
    result = execute_tests(sys.argv[1:])
    sys.exit(result.returncode)
```

### Step 2.3: Performance Test Migration

**File:** `tests/performance/run_performance_tests.py` (modify existing)
```python
# Similar pattern to E2E tests
from shared.feature_flags import TestRunnerFeatureFlags

def execute_performance_tests(test_args):
    """Execute performance tests with SSOT routing"""
    
    if TestRunnerFeatureFlags.enable_ssot_test_runners():
        return execute_via_unified_runner(test_args)
    else:
        return execute_legacy_performance_tests(test_args)

def execute_via_unified_runner(test_args):
    """Route to UnifiedTestRunner with performance configuration"""
    import subprocess
    
    cmd = [
        "python", "tests/unified_test_runner.py",
        "--categories", "performance",
        "--real-services",
        "--profile",  # Enable performance profiling
        "--window-size", "30"  # Larger window for performance tests
    ]
    
    return subprocess.run(cmd + test_args)
```

---

## Phase 3: Medium-Risk Scripts (Week 3)

### Step 3.1: Deployment Script Modification

**File:** `scripts/deploy_to_gcp.py` (modify existing test portions only)

**Find test execution sections and replace:**
```python
# Original: Direct pytest execution
# subprocess.run(["pytest", "tests/smoke/"])

# New: SSOT execution
def run_deployment_tests():
    """Run deployment validation tests via SSOT"""
    import subprocess
    
    cmd = [
        "python", "tests/unified_test_runner.py",
        "--custom-suite", "deployment",
        "--env", "staging"  # or appropriate environment
    ]
    
    result = subprocess.run(cmd)
    if result.returncode != 0:
        logger.error("❌ Deployment tests failed")
        return False
    
    logger.info("✅ Deployment tests passed")
    return True
```

### Step 3.2: Database Integration Scripts

**File:** `scripts/run_database_integration_tests.py` (modify existing)
```python
# Add SSOT routing
def main():
    """Main execution with SSOT routing"""
    import subprocess
    import sys
    
    print("🔄 Routing to SSOT UnifiedTestRunner...")
    
    cmd = [
        "python", "tests/unified_test_runner.py",
        "--categories", "database", "integration",
        "--real-services",
        "--markers", "database"
    ]
    
    # Preserve original arguments
    cmd.extend(sys.argv[1:])
    
    result = subprocess.run(cmd)
    sys.exit(result.returncode)
```

---

## Validation Commands

### Daily Validation
```bash
# Check compliance status
python tests/mission_critical/test_ssot_test_runner_enforcement.py

# Validate Golden Path
python tests/unified_test_runner.py --execution-mode fast_feedback

# Test key workflows
python tests/unified_test_runner.py --custom-suite critical_agents --dry-run
python tests/unified_test_runner.py --custom-suite websocket_validation --dry-run
```

### Weekly Validation
```bash
# Full system validation
python tests/unified_test_runner.py --execution-mode nightly --real-services

# Performance validation
python tests/unified_test_runner.py --categories performance --profile

# Coverage validation
python tests/unified_test_runner.py --categories unit integration --coverage
```

### Pre-Production Validation
```bash
# Complete validation suite
python tests/unified_test_runner.py --custom-suite audit
python tests/unified_test_runner.py --execution-mode hybrid
python scripts/check_architecture_compliance.py
```

---

## Rollback Procedures

### Emergency Rollback
```bash
# Immediate restoration
git revert <commit-hash-range>

# Restore original files
cp tests/unified_test_runner.py.backup tests/unified_test_runner.py

# Validate system
python tests/unified_test_runner.py --execution-mode fast_feedback
```

### Selective Rollback
```bash
# Disable feature flags
export ENABLE_SSOT_TEST_RUNNERS=false
export ENABLE_LEGACY_TEST_FALLBACK=true

# Test specific components
python tests/e2e/run_chat_ui_tests.py  # Should use legacy method
```

---

## Success Metrics

### Technical Metrics
- [ ] **Zero violations:** `python tests/mission_critical/test_ssot_test_runner_enforcement.py` passes
- [ ] **Functionality preserved:** All wrapper scripts work identically
- [ ] **Performance maintained:** No more than 5% execution time increase

### Business Metrics  
- [ ] **Golden Path protected:** Chat functionality fully operational
- [ ] **Development velocity:** No impact on deployment frequency
- [ ] **CI/CD reliability:** No increase in pipeline failures

### Monitoring
```bash
# Set up daily monitoring
echo "0 9 * * * cd /path/to/project && python tests/mission_critical/test_ssot_test_runner_enforcement.py" | crontab -

# Weekly Golden Path validation
echo "0 9 * * 1 cd /path/to/project && python tests/unified_test_runner.py --execution-mode fast_feedback" | crontab -
```

---

## Next Steps

1. **Review and approve** this implementation guide
2. **Start Phase 1** with enhanced UnifiedTestRunner features  
3. **Validate each phase** before proceeding to next
4. **Monitor compliance** throughout implementation
5. **Document learnings** in SPEC/learnings/ as issues arise

**Critical Success Factor:** Maintain Golden Path functionality throughout all phases. Any threat to chat functionality triggers immediate rollback and re-planning.

---

*Implementation Guide - Netra Apex SSOT Remediation System - 2025-01-09*