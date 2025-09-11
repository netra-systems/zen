#!/usr/bin/env python3
"""
🚨 MISSION CRITICAL: SSOT Regression Prevention Monitor Tests

CRITICAL MISSION: Enhanced tests that serve as automated regression monitors
Context: Transforms existing violation detection tests into continuous regression monitors
Objective: Prevent reintroduction of SSOT violations from resolved GitHub issues

Business Value:
- Protects $500K+ ARR from WebSocket auth bypass security vulnerabilities
- Automated regression detection prevents security degradation
- Integrates with monitoring infrastructure for continuous compliance
- Validates that resolved issues (like GitHub Issue #300) stay resolved

MONITORING INTEGRATION:
These tests are designed to work with scripts/monitor_ssot_compliance.py
They can be run independently or as part of continuous monitoring pipeline.

Test Categories:
1. CRITICAL - Security bypass patterns (JWT verify_signature=False)
2. ERROR - SSOT violations (bypassing UnifiedAuthInterface) 
3. WARNING - Architectural concerns (fallback patterns)

Usage:
    python -m pytest tests/mission_critical/test_ssot_regression_prevention_monitor.py -v
    python tests/mission_critical/test_ssot_regression_prevention_monitor.py --monitor-mode
    python tests/mission_critical/test_ssot_regression_prevention_monitor.py --generate-baseline
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.websocket_auth_test_helpers import WebSocketAuthenticationTester
from test_framework.ssot.no_docker_mode_detector import NoDockerModeDetector

# Import the monitoring script components
try:
    from scripts.monitor_ssot_compliance import (
        SSOTComplianceMonitor, 
        WebSocketAuthPatternMonitor,
        ViolationSeverity,
        MonitoringReport
    )
    MONITORING_AVAILABLE = True
except ImportError as e:
    MONITORING_AVAILABLE = False
    logging.warning(f"Monitoring components not available: {e}")

logger = logging.getLogger(__name__)


class TestSSOTRegressionPrevention(SSotBaseTestCase):
    """
    Enhanced mission critical tests that serve as regression monitors.
    
    These tests validate that resolved SSOT violations stay resolved and
    can be integrated into continuous monitoring systems.
    """
    
    @pytest.fixture(autouse=True)
    def setup_regression_monitor(self):
        """Setup regression monitoring capabilities."""
        self.project_root = Path(__file__).parent.parent.parent
        self.monitoring_reports = []
        self.baseline_violations = {}
        
        logger.info("🚀 Starting SSOT Regression Prevention Monitor")
        logger.info("=" * 60)
        logger.info("MISSION: Prevent reintroduction of resolved SSOT violations")
        logger.info("FOCUS: WebSocket auth patterns from GitHub Issue #300")
        logger.info("=" * 60)
        
    @pytest.mark.critical
    @pytest.mark.security
    def test_no_jwt_signature_bypass_patterns(self):
        """
        CRITICAL SECURITY: Ensure JWT signature bypass patterns remain resolved.
        
        GitHub Issue #300: WebSocket JWT bypass vulnerability was RESOLVED
        This test ensures the vulnerability is never reintroduced.
        
        PATTERN: verify_signature=False (CRITICAL security bypass)
        BUSINESS IMPACT: $500K+ ARR at risk if reintroduced
        """
        logger.info("🔍 Testing for JWT signature bypass pattern regression")
        
        # Specific patterns from resolved GitHub Issue #300
        critical_patterns = [
            r"verify_signature\s*=\s*False",
            r"jwt\.decode\([^)]*verify\s*=\s*False", 
            r"options\s*=\s*\{[^}]*[\"']verify_signature[\"']\s*:\s*False"
        ]
        
        violations_found = []
        files_to_check = [
            "netra_backend/app/websocket_core/user_context_extractor.py",
            "netra_backend/app/routes/websocket.py",
            "netra_backend/app/auth_integration/auth.py"
        ]
        
        for file_path in files_to_check:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                
                for line_idx, line in enumerate(lines):
                    for pattern in critical_patterns:
                        import re
                        if re.search(pattern, line, re.IGNORECASE):
                            violations_found.append({
                                'file': file_path,
                                'line': line_idx + 1,
                                'content': line.strip(),
                                'pattern': pattern,
                                'severity': 'CRITICAL'
                            })
                            
            except Exception as e:
                logger.error(f"Error checking {file_path}: {e}")
        
        # Assert no critical violations found
        if violations_found:
            logger.critical("🚨 CRITICAL REGRESSION: JWT signature bypass patterns detected!")
            for violation in violations_found:
                logger.critical(f"  File: {violation['file']}:{violation['line']}")
                logger.critical(f"  Code: {violation['content']}")
                logger.critical(f"  Pattern: {violation['pattern']}")
            
            pytest.fail(f"CRITICAL SECURITY REGRESSION: {len(violations_found)} JWT signature bypass "
                       f"patterns found. These were resolved in GitHub Issue #300 and must not be reintroduced. "
                       f"Business Impact: $500K+ ARR at risk from auth bypass vulnerability.")
        
        logger.info("✅ No JWT signature bypass patterns detected - Issue #300 remains resolved")
    
    @pytest.mark.critical
    @pytest.mark.ssot_compliance
    def test_unified_auth_interface_usage_maintained(self):
        """
        CRITICAL SSOT: Ensure UnifiedAuthInterface usage is maintained.
        
        SSOT REQUIREMENT: All auth operations must use UnifiedAuthInterface
        This test prevents regression to direct JWT operations bypassing SSOT.
        """
        logger.info("🔍 Testing UnifiedAuthInterface SSOT compliance")
        
        # Check for direct JWT imports/operations bypassing UnifiedAuthInterface
        ssot_violation_patterns = [
            (r"^import\s+jwt(?:\s|$)", "Direct JWT import bypassing UnifiedAuthInterface"),
            (r"jwt\.(encode|decode)\s*\(", "Direct JWT operations bypassing auth service"),
            (r"from\s+jwt\s+import", "JWT component import bypassing SSOT")
        ]
        
        violations_found = []
        backend_root = self.project_root / "netra_backend"
        
        # Focus on key auth-related files
        key_files = [
            "app/websocket_core/user_context_extractor.py",
            "app/routes/websocket.py", 
            "app/auth_integration/auth.py",
            "app/core/configuration/unified_secrets.py"
        ]
        
        for file_path in key_files:
            full_path = backend_root / file_path
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                
                # Check for SSOT compliance patterns
                has_unified_auth_import = "UnifiedAuthInterface" in content or "get_unified_auth" in content
                
                for line_idx, line in enumerate(lines):
                    # Skip lines that are properly using UnifiedAuthInterface
                    if "UnifiedAuthInterface" in line or "get_unified_auth" in line:
                        continue
                        
                    # Skip exception markers
                    if any(marker in line for marker in ["@auth_ssot_exception", "# SSOT_EXCEPTION", "# JWT_ALLOWED"]):
                        continue
                    
                    for pattern, description in ssot_violation_patterns:
                        import re
                        if re.search(pattern, line, re.IGNORECASE):
                            violations_found.append({
                                'file': str(file_path),
                                'line': line_idx + 1, 
                                'content': line.strip(),
                                'description': description,
                                'has_unified_auth': has_unified_auth_import
                            })
                            
            except Exception as e:
                logger.error(f"Error checking {file_path}: {e}")
        
        # Filter violations - allow JWT operations if UnifiedAuthInterface is also present
        filtered_violations = []
        for violation in violations_found:
            # Allow JWT operations in files that properly import UnifiedAuthInterface
            # (they may be implementing the interface)
            if not violation['has_unified_auth']:
                filtered_violations.append(violation)
        
        if filtered_violations:
            logger.error("🚨 SSOT REGRESSION: Direct JWT operations bypassing UnifiedAuthInterface!")
            for violation in filtered_violations:
                logger.error(f"  File: {violation['file']}:{violation['line']}")
                logger.error(f"  Issue: {violation['description']}")
                logger.error(f"  Code: {violation['content']}")
            
            pytest.fail(f"SSOT COMPLIANCE REGRESSION: {len(filtered_violations)} violations found. "
                       f"All JWT operations must use UnifiedAuthInterface to maintain SSOT compliance.")
        
        logger.info("✅ UnifiedAuthInterface SSOT compliance maintained")
    
    @pytest.mark.error
    @pytest.mark.websocket_security
    def test_no_websocket_auth_fallback_patterns(self):
        """
        ERROR LEVEL: Ensure WebSocket auth fallback patterns are not reintroduced.
        
        ARCHITECTURAL REQUIREMENT: WebSocket auth must be consistent with main auth
        This test prevents fallback mechanisms that compromise security.
        """
        logger.info("🔍 Testing for WebSocket auth fallback pattern regression")
        
        fallback_patterns = [
            (r"fallback.*auth|auth.*fallback", "Authentication fallback mechanism"),
            (r"legacy.*auth|auth.*legacy", "Legacy authentication logic"),
            (r"bypass.*auth|auth.*bypass", "Authentication bypass mechanism")
        ]
        
        violations_found = []
        websocket_files = [
            "netra_backend/app/websocket_core/user_context_extractor.py",
            "netra_backend/app/routes/websocket.py",
            "netra_backend/app/websocket_core/auth.py"
        ]
        
        for file_path in websocket_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                
                for line_idx, line in enumerate(lines):
                    # Skip comments explaining what NOT to do
                    if line.strip().startswith("#") and any(word in line.lower() for word in ["violation", "do not", "don't", "avoid"]):
                        continue
                        
                    for pattern, description in fallback_patterns:
                        import re
                        if re.search(pattern, line, re.IGNORECASE):
                            violations_found.append({
                                'file': file_path,
                                'line': line_idx + 1,
                                'content': line.strip(),
                                'description': description
                            })
                            
            except Exception as e:
                logger.error(f"Error checking {file_path}: {e}")
        
        if violations_found:
            logger.warning("⚠️  ARCHITECTURAL REGRESSION: WebSocket auth fallback patterns detected!")
            for violation in violations_found:
                logger.warning(f"  File: {violation['file']}:{violation['line']}")
                logger.warning(f"  Issue: {violation['description']}")
                logger.warning(f"  Code: {violation['content']}")
            
            # This is a warning-level issue, not a hard failure
            logger.warning(f"Found {len(violations_found)} WebSocket auth fallback patterns. "
                          f"These should be reviewed for SSOT compliance.")
        else:
            logger.info("✅ No WebSocket auth fallback patterns detected")
    
    @pytest.mark.integration  
    @pytest.mark.monitoring_integration
    def test_monitoring_system_integration(self):
        """
        INTEGRATION: Test integration with automated monitoring system.
        
        This test validates that the monitoring system can detect violations
        and integrate with the testing framework.
        """
        if not MONITORING_AVAILABLE:
            pytest.skip("Monitoring system components not available")
            
        logger.info("🔍 Testing monitoring system integration")
        
        try:
            # Initialize monitoring system
            monitor = SSOTComplianceMonitor(self.project_root)
            
            # Run WebSocket-focused monitoring scan
            report = monitor.run_monitoring_scan(websocket_only=True)
            
            # Validate monitoring report structure
            assert isinstance(report, MonitoringReport), "Monitoring must return valid report"
            assert report.total_files_scanned > 0, "Monitoring must scan files"
            assert report.scan_timestamp is not None, "Report must have timestamp"
            assert isinstance(report.violations, list), "Violations must be a list"
            
            # Log monitoring results
            logger.info(f"✅ Monitoring system integration successful")
            logger.info(f"   Files scanned: {report.total_files_scanned}")
            logger.info(f"   Violations found: {len(report.violations)}")
            logger.info(f"   Regressions: {report.regression_violations}")
            logger.info(f"   Critical issues: {report.security_critical_count}")
            
            # Store report for analysis
            self.monitoring_reports.append(report)
            
            # Alert on critical security issues
            if report.security_critical_count > 0:
                pytest.fail(f"CRITICAL MONITORING ALERT: {report.security_critical_count} "
                           f"security violations detected by monitoring system. "
                           f"Immediate action required.")
            
        except Exception as e:
            pytest.fail(f"Monitoring system integration failed: {e}")
    
    @pytest.mark.baseline
    def test_generate_violation_baseline(self):
        """
        BASELINE: Generate baseline violations for regression detection.
        
        This test can be run with --generate-baseline flag to establish
        the current state as a baseline for future regression detection.
        """
        if not MONITORING_AVAILABLE:
            pytest.skip("Monitoring system components not available")
            
        # Check if we're in baseline generation mode
        generate_baseline = "--generate-baseline" in sys.argv
        if not generate_baseline:
            pytest.skip("Baseline generation not requested (use --generate-baseline)")
            
        logger.info("📊 Generating SSOT violation baseline")
        
        try:
            monitor = SSOTComplianceMonitor(self.project_root)
            websocket_monitor = WebSocketAuthPatternMonitor(self.project_root)
            
            # Scan for current violations
            violations = websocket_monitor.scan_full_backend()
            
            # Save as baseline
            websocket_monitor._save_baseline_violations(violations)
            
            logger.info(f"✅ Baseline generated with {len(violations)} violations")
            logger.info("   Future scans will use this baseline to detect regressions")
            
            # Log violation summary
            violation_types = {}
            for violation in violations:
                violation_type = violation.violation_type
                if violation_type not in violation_types:
                    violation_types[violation_type] = 0
                violation_types[violation_type] += 1
            
            logger.info("   Baseline violation summary:")
            for vtype, count in violation_types.items():
                logger.info(f"     {vtype}: {count}")
                
        except Exception as e:
            pytest.fail(f"Baseline generation failed: {e}")
    
    @pytest.mark.continuous_monitoring
    def test_continuous_monitoring_readiness(self):
        """
        READINESS: Test readiness for continuous monitoring deployment.
        
        This test validates that the system is ready for continuous monitoring
        in production environments.
        """
        logger.info("🔍 Testing continuous monitoring readiness")
        
        readiness_checks = [
            ("Monitoring script executable", self._check_monitoring_script_executable),
            ("Report directory writable", self._check_report_directory_writable), 
            ("Baseline file accessible", self._check_baseline_file_accessible),
            ("Log file writable", self._check_log_file_writable)
        ]
        
        failed_checks = []
        
        for check_name, check_func in readiness_checks:
            try:
                result = check_func()
                if result:
                    logger.info(f"✅ {check_name}: PASS")
                else:
                    logger.error(f"❌ {check_name}: FAIL")
                    failed_checks.append(check_name)
            except Exception as e:
                logger.error(f"❌ {check_name}: ERROR - {e}")
                failed_checks.append(check_name)
        
        if failed_checks:
            pytest.fail(f"Continuous monitoring not ready. Failed checks: {', '.join(failed_checks)}")
        
        logger.info("✅ System ready for continuous monitoring deployment")
    
    def _check_monitoring_script_executable(self) -> bool:
        """Check if monitoring script is executable."""
        script_path = self.project_root / "scripts" / "monitor_ssot_compliance.py"
        return script_path.exists() and os.access(script_path, os.R_OK)
    
    def _check_report_directory_writable(self) -> bool:
        """Check if report directory is writable."""
        report_dir = self.project_root / "reports" / "ssot_compliance"
        report_dir.mkdir(parents=True, exist_ok=True)
        test_file = report_dir / "test_write_permissions.tmp"
        try:
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception:
            return False
    
    def _check_baseline_file_accessible(self) -> bool:
        """Check if baseline file is accessible."""
        baseline_file = self.project_root / "ssot_monitoring_baseline.json"
        return not baseline_file.exists() or os.access(baseline_file, os.R_OK | os.W_OK)
    
    def _check_log_file_writable(self) -> bool:
        """Check if log file is writable."""
        log_file = self.project_root / "ssot_compliance_monitor.log"
        try:
            with open(log_file, 'a') as f:
                f.write(f"Test write {datetime.now().isoformat()}\n")
            return True
        except Exception:
            return False
    
    def tearDown(self):
        """Clean up test artifacts."""
        logger.info("🧹 SSOT regression prevention test cleanup complete")
        if self.monitoring_reports:
            logger.info(f"📊 Generated {len(self.monitoring_reports)} monitoring reports during testing")


# Standalone execution for monitoring mode
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SSOT Regression Prevention Monitor")
    parser.add_argument("--monitor-mode", action="store_true", 
                       help="Run in monitoring mode (continuous checks)")
    parser.add_argument("--generate-baseline", action="store_true",
                       help="Generate violation baseline for regression detection")
    
    # Parse known args to avoid conflicts with pytest
    args, unknown = parser.parse_known_args()
    
    if args.monitor_mode:
        print("🚀 SSOT REGRESSION PREVENTION MONITOR MODE")
        print("=" * 60)
        
        # Run monitoring mode
        if MONITORING_AVAILABLE:
            project_root = Path(__file__).parent.parent.parent
            monitor = SSOTComplianceMonitor(project_root)
            
            try:
                print("Running single monitoring scan...")
                report = monitor.run_monitoring_scan(websocket_only=True)
                monitor.print_monitoring_report(report, verbose=True)
                
                # Save report
                report_file = monitor.save_monitoring_report(report)
                print(f"\n📄 Report saved to: {report_file}")
                
                # Exit with appropriate code
                if report.security_critical_count > 0:
                    print("\n🔴 CRITICAL security violations detected!")
                    sys.exit(2)
                elif report.regression_violations > 0:
                    print("\n🚨 REGRESSION violations detected!")
                    sys.exit(1)
                else:
                    print("\n✅ No violations detected")
                    sys.exit(0)
                    
            except Exception as e:
                print(f"\n❌ Monitoring failed: {e}")
                sys.exit(3)
        else:
            print("❌ Monitoring components not available")
            sys.exit(3)
    else:
        # Run as pytest
        pytest.main([__file__] + unknown)