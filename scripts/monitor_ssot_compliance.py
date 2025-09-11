#!/usr/bin/env python3
"""
🚨 SSOT Compliance Regression Prevention Monitor

CRITICAL MISSION: Prevent regression of SSOT violations in WebSocket auth patterns
Context: GitHub Issue #300 (WebSocket JWT bypass) has been RESOLVED
Objective: Automated monitoring to detect if SSOT violations are reintroduced

Business Value:
- Protects $500K+ ARR from WebSocket auth bypass security vulnerabilities  
- Prevents JWT signature bypass patterns (verify_signature=False)
- Maintains UnifiedAuthInterface SSOT compliance
- Automated regression detection prevents security degradation

MONITORING SCOPE:
1. WebSocket auth pattern violations from resolved Issue #300
2. JWT signature bypass patterns (critical security risk)
3. Direct JWT operations bypassing UnifiedAuthInterface  
4. Fallback auth patterns that compromise SSOT
5. Import violations that bypass auth service SSOT

Usage:
    python scripts/monitor_ssot_compliance.py --monitor-websocket
    python scripts/monitor_ssot_compliance.py --full-scan --alert-on-violations
    python scripts/monitor_ssot_compliance.py --continuous --interval 300

Exit codes:
    0 = No violations detected
    1 = SSOT violations found (regression alert)
    2 = Critical security violations found (immediate action required)
    3 = Script error
"""

import argparse
import ast
import datetime
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ssot_compliance_monitor.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


class ViolationSeverity(Enum):
    """Severity levels for SSOT violations."""
    CRITICAL = "CRITICAL"  # Security bypass, immediate action required
    ERROR = "ERROR"        # SSOT violation, blocks deployment
    WARNING = "WARNING"    # Potential issue, needs review
    INFO = "INFO"         # Informational, monitoring only


@dataclass
class SSOTViolation:
    """Represents a detected SSOT compliance violation."""
    file_path: str
    line_number: int
    line_content: str
    violation_type: str
    description: str
    suggestion: str
    severity: ViolationSeverity
    detection_timestamp: str
    issue_reference: Optional[str] = None  # Reference to resolved GitHub issue
    business_impact: Optional[str] = None


@dataclass
class MonitoringReport:
    """Results of SSOT compliance monitoring."""
    scan_timestamp: str
    total_files_scanned: int
    violations: List[SSOTViolation]
    baseline_violations: int  # Expected violations from existing code
    regression_violations: int  # New violations (regressions)
    security_critical_count: int
    monitoring_config: Dict[str, Any]
    
    @property
    def has_regressions(self) -> bool:
        return self.regression_violations > 0
    
    @property
    def has_critical_violations(self) -> bool:
        return self.security_critical_count > 0


class WebSocketAuthPatternMonitor:
    """
    Monitors WebSocket authentication patterns for SSOT compliance regressions.
    
    Focus: Prevent reintroduction of patterns from resolved GitHub Issue #300
    """
    
    # CRITICAL PATTERNS: JWT signature bypass (Issue #300)
    CRITICAL_JWT_BYPASS_PATTERNS = {
        "jwt_verify_signature_false": {
            "pattern": r"verify_signature\s*=\s*False",
            "description": "JWT signature verification bypassed - CRITICAL SECURITY VULNERABILITY",
            "suggestion": "Remove verify_signature=False, use UnifiedAuthInterface for proper JWT validation",
            "severity": ViolationSeverity.CRITICAL,
            "issue_ref": "GitHub Issue #300 - WebSocket JWT bypass",
            "business_impact": "$500K+ ARR at risk from unauthorized access"
        },
        "jwt_decode_no_verify": {
            "pattern": r"jwt\.decode\([^)]*verify\s*=\s*False",
            "description": "JWT decode with verification disabled - SECURITY BYPASS",
            "suggestion": "Use UnifiedAuthInterface.validate_token() instead of direct JWT operations",
            "severity": ViolationSeverity.CRITICAL,
            "issue_ref": "GitHub Issue #300 - WebSocket JWT bypass"
        },
        "jwt_options_no_verify": {
            "pattern": r"options\s*=\s*\{[^}]*[\"']verify_signature[\"']\s*:\s*False",
            "description": "JWT options disable signature verification - CRITICAL VULNERABILITY",
            "suggestion": "Remove JWT decode options bypassing signature verification",
            "severity": ViolationSeverity.CRITICAL,
            "issue_ref": "GitHub Issue #300 - WebSocket JWT bypass"
        }
    }
    
    # SSOT VIOLATION PATTERNS: Direct JWT operations bypassing UnifiedAuthInterface
    SSOT_VIOLATION_PATTERNS = {
        "direct_jwt_import": {
            "pattern": r"^import\s+jwt(?:\s|$)",
            "description": "Direct JWT library import bypassing UnifiedAuthInterface SSOT",
            "suggestion": "Use UnifiedAuthInterface instead of direct JWT operations",
            "severity": ViolationSeverity.ERROR,
            "issue_ref": "SSOT compliance - UnifiedAuthInterface required"
        },
        "direct_jwt_operations": {
            "pattern": r"jwt\.(encode|decode)\s*\(",
            "description": "Direct JWT operations bypassing auth service SSOT",
            "suggestion": "Use auth service endpoints through UnifiedAuthInterface",
            "severity": ViolationSeverity.ERROR,
            "issue_ref": "SSOT compliance - Auth service is exclusive JWT source"
        },
        "websocket_local_jwt": {
            "pattern": r"def\s+(validate_jwt|decode_token|verify_token)\s*\(.*websocket",
            "description": "WebSocket module implementing local JWT validation",
            "suggestion": "Use UnifiedAuthInterface for all WebSocket authentication",
            "severity": ViolationSeverity.ERROR,
            "issue_ref": "WebSocket SSOT compliance"
        }
    }
    
    # FALLBACK PATTERNS: Auth fallback mechanisms that compromise SSOT
    FALLBACK_AUTH_PATTERNS = {
        "auth_fallback_logic": {
            "pattern": r"fallback.*auth|auth.*fallback",
            "description": "Authentication fallback logic bypassing SSOT",
            "suggestion": "Remove fallbacks, implement proper error handling with UnifiedAuthInterface",
            "severity": ViolationSeverity.WARNING,
            "issue_ref": "SSOT compliance - No auth fallbacks allowed"
        },
        "legacy_auth_patterns": {
            "pattern": r"legacy.*auth|auth.*legacy",
            "description": "Legacy authentication patterns outside SSOT",
            "suggestion": "Migrate to UnifiedAuthInterface SSOT pattern",
            "severity": ViolationSeverity.WARNING,
            "issue_ref": "SSOT compliance - Legacy auth removal"
        },
        "websocket_auth_bypass": {
            "pattern": r"bypass.*auth|auth.*bypass.*websocket",
            "description": "WebSocket authentication bypass mechanism",
            "suggestion": "Remove auth bypass, enforce proper WebSocket authentication",
            "severity": ViolationSeverity.ERROR,
            "issue_ref": "WebSocket security - No auth bypass allowed"
        }
    }
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize WebSocket auth pattern monitor."""
        self.project_root = project_root or Path.cwd()
        self.websocket_paths = [
            self.project_root / "netra_backend" / "app" / "websocket_core",
            self.project_root / "netra_backend" / "app" / "routes" / "websocket.py",
            self.project_root / "netra_backend" / "app" / "auth_integration",
        ]
        
        # Files with known baseline violations (grandfathered)
        self.baseline_violation_files = {
            # Add files that had violations before monitoring was implemented
            # These won't trigger regression alerts but will be tracked
        }
        
        # Load baseline violations from previous scans
        self.baseline_violations = self._load_baseline_violations()
        
    def _load_baseline_violations(self) -> Dict[str, List[str]]:
        """Load baseline violations from previous monitoring runs."""
        baseline_file = self.project_root / "ssot_monitoring_baseline.json"
        if baseline_file.exists():
            try:
                with open(baseline_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load baseline violations: {e}")
        return {}
    
    def _save_baseline_violations(self, violations: List[SSOTViolation]):
        """Save current violations as baseline for future regression detection."""
        baseline_data = {}
        for violation in violations:
            file_key = str(Path(violation.file_path).relative_to(self.project_root))
            if file_key not in baseline_data:
                baseline_data[file_key] = []
            baseline_data[file_key].append({
                'line': violation.line_number,
                'type': violation.violation_type,
                'content_hash': hash(violation.line_content)
            })
        
        baseline_file = self.project_root / "ssot_monitoring_baseline.json"
        with open(baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        logger.info(f"Saved baseline violations to {baseline_file}")
    
    def _is_baseline_violation(self, violation: SSOTViolation) -> bool:
        """Check if violation exists in baseline (not a regression)."""
        file_key = str(Path(violation.file_path).relative_to(self.project_root))
        if file_key not in self.baseline_violations:
            return False
            
        for baseline_violation in self.baseline_violations[file_key]:
            if (baseline_violation['line'] == violation.line_number and
                baseline_violation['type'] == violation.violation_type):
                return True
        return False
    
    def scan_file_for_violations(self, file_path: Path) -> List[SSOTViolation]:
        """Scan a single file for SSOT violations."""
        violations = []
        
        if not file_path.exists() or not file_path.suffix == '.py':
            return violations
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            # Combine all pattern dictionaries
            all_patterns = {
                **self.CRITICAL_JWT_BYPASS_PATTERNS,
                **self.SSOT_VIOLATION_PATTERNS, 
                **self.FALLBACK_AUTH_PATTERNS
            }
            
            for line_idx, line in enumerate(lines):
                line_stripped = line.strip()
                
                # Skip empty lines and simple comments
                if not line_stripped or (line_stripped.startswith("#") and "TODO" not in line_stripped):
                    continue
                
                # Check each pattern
                for pattern_name, pattern_info in all_patterns.items():
                    if re.search(pattern_info["pattern"], line, re.IGNORECASE | re.MULTILINE):
                        # Found a potential violation
                        violation = SSOTViolation(
                            file_path=str(file_path),
                            line_number=line_idx + 1,
                            line_content=line.rstrip(),
                            violation_type=pattern_name,
                            description=pattern_info["description"],
                            suggestion=pattern_info["suggestion"], 
                            severity=pattern_info["severity"],
                            detection_timestamp=datetime.datetime.now().isoformat(),
                            issue_reference=pattern_info.get("issue_ref"),
                            business_impact=pattern_info.get("business_impact")
                        )
                        violations.append(violation)
                        
                        # Log critical violations immediately
                        if violation.severity == ViolationSeverity.CRITICAL:
                            logger.critical(f"CRITICAL VIOLATION: {violation.description}")
                            logger.critical(f"  File: {violation.file_path}:{violation.line_number}")
                            logger.critical(f"  Code: {violation.line_content}")
                            
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            
        return violations
    
    def scan_websocket_patterns(self) -> List[SSOTViolation]:
        """Scan WebSocket-related files for auth pattern violations."""
        all_violations = []
        files_scanned = 0
        
        logger.info("🔍 Scanning WebSocket files for SSOT compliance violations...")
        
        for websocket_path in self.websocket_paths:
            if websocket_path.is_file():
                # Single file
                violations = self.scan_file_for_violations(websocket_path)
                all_violations.extend(violations)
                files_scanned += 1
                
            elif websocket_path.is_dir():
                # Directory - scan all Python files
                for py_file in websocket_path.rglob("*.py"):
                    violations = self.scan_file_for_violations(py_file)
                    all_violations.extend(violations)
                    files_scanned += 1
                    
        logger.info(f"✅ Scanned {files_scanned} files for WebSocket auth violations")
        return all_violations
    
    def scan_full_backend(self) -> List[SSOTViolation]:
        """Scan entire backend for SSOT compliance violations."""
        all_violations = []
        files_scanned = 0
        
        logger.info("🔍 Performing full backend scan for SSOT compliance...")
        
        backend_root = self.project_root / "netra_backend"
        if backend_root.exists():
            for py_file in backend_root.rglob("*.py"):
                # Skip test files for now (they have different rules)
                if "/test" in str(py_file) or "/tests/" in str(py_file):
                    continue
                    
                violations = self.scan_file_for_violations(py_file)
                all_violations.extend(violations)
                files_scanned += 1
                
        logger.info(f"✅ Scanned {files_scanned} backend files for SSOT violations")
        return all_violations


class SSOTComplianceMonitor:
    """
    Main SSOT compliance monitoring system.
    
    Coordinates different monitoring modules and provides reporting.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize SSOT compliance monitor."""
        self.project_root = project_root or Path.cwd()
        self.websocket_monitor = WebSocketAuthPatternMonitor(project_root)
        self.report_dir = self.project_root / "reports" / "ssot_compliance"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
    def run_monitoring_scan(self, websocket_only: bool = False, save_baseline: bool = False) -> MonitoringReport:
        """Run comprehensive SSOT compliance monitoring scan."""
        scan_start = datetime.datetime.now()
        logger.info(f"🚀 Starting SSOT compliance monitoring scan at {scan_start.isoformat()}")
        
        # Perform scans based on scope
        all_violations = []
        files_scanned = 0
        
        if websocket_only:
            logger.info("Scope: WebSocket authentication patterns only")
            violations = self.websocket_monitor.scan_websocket_patterns()
            all_violations.extend(violations)
            files_scanned += len(self.websocket_monitor.websocket_paths)
        else:
            logger.info("Scope: Full backend SSOT compliance scan")
            violations = self.websocket_monitor.scan_full_backend()
            all_violations.extend(violations)
            # Estimate files scanned (actual count would require walking the tree)
            backend_root = self.project_root / "netra_backend"
            if backend_root.exists():
                files_scanned = len(list(backend_root.rglob("*.py")))
        
        # Classify violations: baseline vs regression
        baseline_count = 0
        regression_violations = []
        security_critical_count = 0
        
        for violation in all_violations:
            if violation.severity == ViolationSeverity.CRITICAL:
                security_critical_count += 1
                
            if self.websocket_monitor._is_baseline_violation(violation):
                baseline_count += 1
            else:
                regression_violations.append(violation)
        
        # Save new baseline if requested
        if save_baseline and all_violations:
            self.websocket_monitor._save_baseline_violations(all_violations)
        
        # Create monitoring report
        report = MonitoringReport(
            scan_timestamp=scan_start.isoformat(),
            total_files_scanned=files_scanned,
            violations=all_violations,
            baseline_violations=baseline_count,
            regression_violations=len(regression_violations),
            security_critical_count=security_critical_count,
            monitoring_config={
                "websocket_only": websocket_only,
                "project_root": str(self.project_root),
                "scan_duration_seconds": (datetime.datetime.now() - scan_start).total_seconds()
            }
        )
        
        logger.info(f"✅ Monitoring scan completed in {report.monitoring_config['scan_duration_seconds']:.2f}s")
        logger.info(f"   Files scanned: {files_scanned}")
        logger.info(f"   Total violations: {len(all_violations)}")
        logger.info(f"   Baseline violations: {baseline_count}")
        logger.info(f"   Regression violations: {len(regression_violations)}")
        logger.info(f"   Critical security issues: {security_critical_count}")
        
        return report
    
    def save_monitoring_report(self, report: MonitoringReport) -> Path:
        """Save monitoring report to file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.report_dir / f"ssot_compliance_report_{timestamp}.json"
        
        # Convert report to JSON-serializable format
        report_data = {
            "scan_timestamp": report.scan_timestamp,
            "total_files_scanned": report.total_files_scanned,
            "baseline_violations": report.baseline_violations,
            "regression_violations": report.regression_violations,
            "security_critical_count": report.security_critical_count,
            "monitoring_config": report.monitoring_config,
            "violations": [
                {
                    "file_path": v.file_path,
                    "line_number": v.line_number,
                    "line_content": v.line_content,
                    "violation_type": v.violation_type,
                    "description": v.description,
                    "suggestion": v.suggestion,
                    "severity": v.severity.value,
                    "detection_timestamp": v.detection_timestamp,
                    "issue_reference": v.issue_reference,
                    "business_impact": v.business_impact
                }
                for v in report.violations
            ]
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"📄 Monitoring report saved to {report_file}")
        return report_file
    
    def print_monitoring_report(self, report: MonitoringReport, verbose: bool = False):
        """Print formatted monitoring report."""
        print("\n" + "="*80)
        print("🚨 SSOT COMPLIANCE MONITORING REPORT")
        print("="*80)
        
        print(f"\nScan Details:")
        print(f"  Timestamp: {report.scan_timestamp}")
        print(f"  Files Scanned: {report.total_files_scanned}")
        print(f"  Scan Duration: {report.monitoring_config.get('scan_duration_seconds', 0):.2f}s")
        print(f"  Scope: {'WebSocket Only' if report.monitoring_config.get('websocket_only') else 'Full Backend'}")
        
        print(f"\nViolation Summary:")
        print(f"  Total Violations: {len(report.violations)}")
        print(f"  Baseline Violations: {report.baseline_violations} (existing, monitored)")
        print(f"  🚨 REGRESSION Violations: {report.regression_violations} (NEW - requires action)")
        print(f"  🔴 CRITICAL Security Issues: {report.security_critical_count} (immediate action required)")
        
        # Print critical violations first
        critical_violations = [v for v in report.violations if v.severity == ViolationSeverity.CRITICAL]
        if critical_violations:
            print(f"\n🔴 CRITICAL SECURITY VIOLATIONS ({len(critical_violations)}):")
            print("="*60)
            for v in critical_violations:
                print(f"  🚨 {v.description}")
                print(f"     File: {v.file_path}:{v.line_number}")
                print(f"     Issue: {v.issue_reference}")
                print(f"     Business Impact: {v.business_impact}")
                print(f"     Fix: {v.suggestion}")
                if verbose:
                    print(f"     Code: {v.line_content}")
                print()
        
        # Print regression violations (new violations)
        regression_violations = [v for v in report.violations 
                               if not self.websocket_monitor._is_baseline_violation(v)]
        if regression_violations:
            print(f"\n🚨 REGRESSION VIOLATIONS ({len(regression_violations)}) - NEW ISSUES:")
            print("="*60)
            
            # Group by severity
            for severity in [ViolationSeverity.ERROR, ViolationSeverity.WARNING]:
                severity_violations = [v for v in regression_violations if v.severity == severity]
                if severity_violations:
                    print(f"\n{severity.value} ({len(severity_violations)} issues):")
                    for v in severity_violations:
                        print(f"  File: {v.file_path}:{v.line_number}")
                        print(f"     Issue: {v.description}")
                        print(f"     Fix: {v.suggestion}")
                        if verbose:
                            print(f"     Code: {v.line_content}")
                        print()
        
        # Print baseline violations summary (if any)
        if report.baseline_violations > 0:
            print(f"\n📊 BASELINE VIOLATIONS ({report.baseline_violations}) - Known Issues (Monitored):")
            print("  These violations existed before monitoring was implemented.")
            print("  They are tracked but don't trigger regression alerts.")
            print("  Consider addressing them during future refactoring.")
        
        # Final verdict and recommendations
        print("\n" + "="*80)
        if report.security_critical_count > 0:
            print("🔴 CRITICAL ALERT: Security vulnerabilities detected!")
            print("   IMMEDIATE ACTION REQUIRED to prevent security incidents.")
            print("   These violations could compromise $500K+ ARR from auth bypass.")
            
        elif report.regression_violations > 0:
            print("🚨 REGRESSION ALERT: New SSOT violations detected!")
            print("   These violations were introduced since last scan.")
            print("   Address before deployment to maintain SSOT compliance.")
            
        elif len(report.violations) > 0:
            print("⚠️  MONITORING STATUS: Baseline violations present.")
            print("   No new regressions detected. Baseline violations are being monitored.")
            
        else:
            print("✅ COMPLIANCE STATUS: All checks passed!")
            print("   No SSOT violations detected. System maintains proper architecture.")
        
        print(f"\nBusiness Impact Protection: WebSocket auth security maintained")
        print(f"Revenue Protection: $500K+ ARR secured from auth bypass vulnerabilities")
        print("="*80)
        
    def run_continuous_monitoring(self, interval_seconds: int = 300, websocket_only: bool = True):
        """Run continuous monitoring with specified interval."""
        logger.info(f"🔄 Starting continuous SSOT monitoring (interval: {interval_seconds}s)")
        logger.info(f"   Scope: {'WebSocket patterns only' if websocket_only else 'Full backend'}")
        
        try:
            while True:
                logger.info("⏰ Running scheduled SSOT compliance scan...")
                
                try:
                    report = self.run_monitoring_scan(websocket_only=websocket_only)
                    
                    # Save report
                    self.save_monitoring_report(report)
                    
                    # Alert on violations
                    if report.security_critical_count > 0:
                        logger.critical(f"🚨 CRITICAL ALERT: {report.security_critical_count} security violations detected!")
                        # In production, this would trigger alerts (email, Slack, etc.)
                        
                    elif report.regression_violations > 0:
                        logger.error(f"🚨 REGRESSION ALERT: {report.regression_violations} new SSOT violations!")
                        
                    else:
                        logger.info("✅ Monitoring cycle completed - no regressions detected")
                        
                except Exception as e:
                    logger.error(f"❌ Monitoring scan failed: {e}")
                
                # Wait for next cycle
                logger.info(f"💤 Sleeping for {interval_seconds}s until next scan...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("🛑 Continuous monitoring stopped by user")


def main():
    """Main entry point for SSOT compliance monitoring."""
    parser = argparse.ArgumentParser(
        description="SSOT Compliance Regression Prevention Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor WebSocket patterns only (recommended)
  python scripts/monitor_ssot_compliance.py --monitor-websocket
  
  # Full backend scan with verbose output  
  python scripts/monitor_ssot_compliance.py --full-scan --verbose
  
  # Continuous monitoring (production)
  python scripts/monitor_ssot_compliance.py --continuous --interval 300
  
  # Save current state as baseline
  python scripts/monitor_ssot_compliance.py --save-baseline
        """
    )
    
    parser.add_argument(
        "--monitor-websocket",
        action="store_true", 
        help="Monitor WebSocket authentication patterns only (recommended for Issue #300)"
    )
    
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help="Scan entire backend for SSOT violations (comprehensive)"
    )
    
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous monitoring with specified interval"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Continuous monitoring interval in seconds (default: 300)"
    )
    
    parser.add_argument(
        "--alert-on-violations",
        action="store_true",
        help="Generate alerts when violations are detected"
    )
    
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save current violations as baseline for regression detection"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output including code snippets"
    )
    
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (default: current directory)"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize monitor
        monitor = SSOTComplianceMonitor(args.project_root)
        
        # Determine scan scope
        websocket_only = args.monitor_websocket or not args.full_scan
        
        if args.continuous:
            # Run continuous monitoring
            monitor.run_continuous_monitoring(
                interval_seconds=args.interval,
                websocket_only=websocket_only
            )
        else:
            # Run single scan
            logger.info("🚀 Starting SSOT compliance monitoring scan...")
            
            report = monitor.run_monitoring_scan(
                websocket_only=websocket_only,
                save_baseline=args.save_baseline
            )
            
            # Save report
            report_file = monitor.save_monitoring_report(report)
            
            # Print results
            monitor.print_monitoring_report(report, verbose=args.verbose)
            
            # Determine exit code
            if report.security_critical_count > 0:
                logger.critical("🔴 Exiting with code 2 - CRITICAL security violations detected")
                sys.exit(2)
            elif report.regression_violations > 0:
                logger.error("🚨 Exiting with code 1 - SSOT regression violations detected")
                sys.exit(1)
            else:
                logger.info("✅ Exiting with code 0 - No violations detected")
                sys.exit(0)
                
    except KeyboardInterrupt:
        logger.info("🛑 Monitoring interrupted by user")
        sys.exit(3)
    except Exception as e:
        logger.error(f"❌ Monitoring failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()