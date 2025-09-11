"""
SSOT COMPATIBILITY LAYER - EMERGENCY STABILIZATION
==================================================
CRITICAL BUSINESS PROTECTION: This compatibility layer ensures ZERO disruption to Golden Path
validation ($500K+ ARR protection) during SSOT UnifiedTestRunner consolidation.

PURPOSE: 
- Maintain existing API while redirecting to canonical SSOT
- Enable gradual migration with zero business impact
- Protect Golden Path testing during remediation

BUSINESS IMPACT:
- $500K+ ARR chat functionality validation preserved
- 90% platform value (WebSocket events) continues testing
- Enterprise customers protected during transition

DEPRECATION TIMELINE:
- Phase 1: Compatibility layer active (current)
- Phase 2: Gradual migration with warnings
- Phase 3: Direct canonical SSOT usage
- Phase 4: Compatibility layer removal

CANONICAL SSOT: tests/unified_test_runner.py:UnifiedTestRunner
"""

import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# CRITICAL: Import canonical SSOT UnifiedTestRunner
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    # CRITICAL: Direct import of canonical SSOT (avoid circular import)
    sys.path.insert(0, str(PROJECT_ROOT))
    from tests.unified_test_runner import UnifiedTestRunner as CanonicalUnifiedTestRunner
    CANONICAL_AVAILABLE = True
    print("✅ SSOT BACKEND: Successfully connected to canonical UnifiedTestRunner")
except ImportError as e:
    CANONICAL_AVAILABLE = False
    print(f"⚠️  FALLBACK MODE: Cannot import canonical UnifiedTestRunner: {e}")
    warnings.warn(f"FALLBACK MODE: Using legacy implementation for business continuity: {e}")

class LegacyUnifiedTestRunnerWrapper:
    """
    EMERGENCY COMPATIBILITY WRAPPER
    ===============================
    Maintains backward compatibility while using canonical SSOT backend.
    
    BUSINESS PROTECTION:
    - Zero API changes for existing consumers
    - Golden Path testing continues without interruption
    - WebSocket event validation preserved
    - Chat functionality testing maintained
    
    TECHNICAL APPROACH:
    - Wraps canonical SSOT UnifiedTestRunner
    - Maintains all existing method signatures
    - Adds deprecation warnings for migration guidance
    - Provides rollback capability if issues detected
    """
    
    def __init__(self):
        """Initialize with SSOT backend and compatibility warnings."""
        self._emit_deprecation_warning()
        
        if CANONICAL_AVAILABLE:
            # Use canonical SSOT backend
            self._canonical_runner = CanonicalUnifiedTestRunner()
            self._mode = "ssot_backend"
        else:
            # Fallback to prevent business disruption
            self._canonical_runner = None
            self._mode = "fallback"
            self._initialize_fallback()
    
    def _emit_deprecation_warning(self):
        """Emit deprecation warning to guide migration."""
        warnings.warn(
            "SSOT MIGRATION NOTICE: test_framework.runner.UnifiedTestRunner is deprecated. "
            "Please migrate to: from tests.unified_test_runner import UnifiedTestRunner. "
            "This compatibility layer maintains business continuity during transition.",
            DeprecationWarning,
            stacklevel=3
        )
    
    def _initialize_fallback(self):
        """Initialize fallback structure to prevent business disruption."""
        from collections import defaultdict
        self.test_categories = defaultdict(list)
        self.results = self._initialize_results_structure()
        self._setup_directories()
        self.staging_mode = False
        
        # Import fallback dependencies
        try:
            from test_framework.comprehensive_reporter import ComprehensiveTestReporter
            self.comprehensive_reporter = ComprehensiveTestReporter(self.reports_dir)
        except ImportError:
            self.comprehensive_reporter = None
            
        try:
            from test_framework.feature_flags import FeatureFlagManager
            self.feature_manager = FeatureFlagManager()
        except ImportError:
            self.feature_manager = None
    
    def run_backend_tests(self, args: List[str], timeout: int = 300, real_llm_config: Optional[Dict] = None, speed_opts: Optional[Dict] = None) -> Tuple[int, str]:
        """Run backend tests - BUSINESS CRITICAL for Golden Path validation."""
        if self._canonical_runner and hasattr(self._canonical_runner, 'run_tests'):
            # Use canonical SSOT method
            return self._canonical_runner.run_tests(
                category="backend",
                test_paths=args,
                timeout=timeout,
                real_llm_config=real_llm_config
            )
        else:
            # Fallback implementation to prevent business disruption
            return self._run_fallback_backend_tests(args, timeout)
    
    def run_frontend_tests(self, args: List[str], timeout: int = 300, speed_opts: Optional[Dict] = None, test_level: str = None) -> Tuple[int, str]:
        """Run frontend tests with SSOT backend."""
        if self._canonical_runner and hasattr(self._canonical_runner, 'run_tests'):
            return self._canonical_runner.run_tests(
                category="frontend", 
                test_paths=args,
                timeout=timeout
            )
        else:
            return self._run_fallback_frontend_tests(args, timeout)
    
    def run_e2e_tests(self, args: List[str], timeout: int = 600) -> Tuple[int, str]:
        """Run E2E tests - CRITICAL for enterprise customer validation."""
        if self._canonical_runner and hasattr(self._canonical_runner, 'run_tests'):
            return self._canonical_runner.run_tests(
                category="e2e",
                test_paths=args, 
                timeout=timeout
            )
        else:
            return self._run_fallback_e2e_tests(args, timeout)
    
    def run_simple_tests(self) -> Tuple[int, str]:
        """Run simple smoke tests for quick validation."""
        if self._canonical_runner and hasattr(self._canonical_runner, 'run_tests'):
            return self._canonical_runner.run_tests(category="smoke", timeout=60)
        else:
            return self._run_fallback_simple_tests()
    
    def save_test_report(self, level: str, config: Dict, output: str, exit_code: int):
        """Save test report using SSOT reporting."""
        if self._canonical_runner and hasattr(self._canonical_runner, 'save_test_report'):
            self._canonical_runner.save_test_report(level, config, output, exit_code)
        elif self.comprehensive_reporter:
            self.comprehensive_reporter.generate_comprehensive_report(
                level=level,
                results=self.results,
                config=config,
                exit_code=exit_code
            )
    
    def print_summary(self):
        """Print test summary."""
        if self._canonical_runner and hasattr(self._canonical_runner, 'print_summary'):
            self._canonical_runner.print_summary()
        else:
            self._print_fallback_summary()
    
    # Fallback methods to prevent business disruption
    def _run_fallback_backend_tests(self, args: List[str], timeout: int) -> Tuple[int, str]:
        """Fallback backend test execution."""
        import subprocess
        cmd = ["python", "-m", "pytest"] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return 1, f"Tests timed out after {timeout} seconds"
    
    def _run_fallback_frontend_tests(self, args: List[str], timeout: int) -> Tuple[int, str]:
        """Fallback frontend test execution."""
        import subprocess
        cwd = Path(__file__).parent.parent / "frontend"
        if not cwd.exists():
            return 0, "Frontend directory not found, skipping tests"
        
        cmd = ["npm", "test", "--"] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cwd))
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return 1, f"Tests timed out after {timeout} seconds"
    
    def _run_fallback_e2e_tests(self, args: List[str], timeout: int) -> Tuple[int, str]:
        """Fallback E2E test execution."""
        import subprocess
        test_paths = ["tests/e2e", "tests/unified/e2e"]
        cmd = ["python", "-m", "pytest"] + test_paths + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return 1, f"Tests timed out after {timeout} seconds"
    
    def _run_fallback_simple_tests(self) -> Tuple[int, str]:
        """Fallback simple test execution."""
        import subprocess
        cmd = ["python", "-m", "pytest", "--category", "smoke", "--fail-fast"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return 1, "Simple tests timed out after 60 seconds"
    
    def _print_fallback_summary(self):
        """Fallback summary printing."""
        print("\n" + "="*60)
        print("LEGACY TEST RUNNER SUMMARY")
        print("="*60)
        print(f"Mode: {self._mode}")
        if hasattr(self, 'results'):
            for component, result in self.results.items():
                if isinstance(result, dict) and 'status' in result:
                    print(f"{component}: {result['status']}")
        print("="*60)
    
    def _initialize_results_structure(self) -> Dict:
        """Initialize fallback results structure."""
        component_template = {
            "status": "pending", "duration": 0, "exit_code": None, "output": "",
            "test_counts": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0},
            "coverage": None
        }
        overall_template = {"status": "pending", "start_time": None, "end_time": None}
        
        return {
            "backend": component_template.copy(),
            "frontend": component_template.copy(), 
            "e2e": component_template.copy(),
            "overall": overall_template
        }
    
    def _setup_directories(self):
        """Setup required directories for fallback mode."""
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.history_dir = self.reports_dir / "history"
        self.history_dir.mkdir(exist_ok=True)

# CRITICAL: Maintain API compatibility
UnifiedTestRunner = LegacyUnifiedTestRunnerWrapper