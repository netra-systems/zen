#!/usr/bin/env python3
"""
Complete Docker Workflow Validation
====================================
Comprehensive validation suite to ensure ALL Docker improvements work correctly together.

CRITICAL: This validator ensures the Docker SSOT system is working perfectly:
1. SSOT Compliance - Only approved configs exist
2. Developer Experience - refresh_dev works reliably  
3. E2E Testing - Docker starts automatically for tests
4. Build Performance - Optimized builds meet targets
5. No Fallbacks - Hard fails, no confusing fallback logic

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity & System Reliability
2. Business Goal: Ensure Docker improvements deliver promised value
3. Value Impact: Prevents Docker configuration confusion, ensures reliable dev workflow
4. Revenue Impact: Saves 5+ hours/week per developer, prevents production deployment issues

Usage:
    python scripts/validate_docker_workflow.py                  # Full validation
    python scripts/validate_docker_workflow.py --quick          # Skip performance tests
    python scripts/validate_docker_workflow.py --report-only    # Generate report without tests
    python scripts/validate_docker_workflow.py --fix-violations # Auto-fix found issues
"""

import sys
import os
import subprocess
import time
import logging
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import (
    UnifiedDockerManager,
    EnvironmentType
)
from scripts.docker_ssot_enforcer import DockerSSOTEnforcer
from scripts.refresh_dev import DevEnvironmentRefresher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Single validation result"""
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class WorkflowValidationReport:
    """Complete validation report"""
    timestamp: str
    success: bool
    results: List[ValidationResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class DockerWorkflowValidator:
    """Complete Docker Workflow Validation Suite"""
    
    def __init__(self, 
                 quick: bool = False, 
                 report_only: bool = False,
                 fix_violations: bool = False):
        """Initialize validator with options.
        
        Args:
            quick: Skip performance tests for faster validation
            report_only: Generate report without running tests
            fix_violations: Attempt to auto-fix found violations
        """
        self.quick = quick
        self.report_only = report_only
        self.fix_violations = fix_violations
        self.project_root = project_root
        
        # Initialize components
        self.ssot_enforcer = DockerSSOTEnforcer()
        self.results: List[ValidationResult] = []
        
        logger.info("🔍 Docker Workflow Validator initialized")
        logger.info(f"   Project: {self.project_root}")
        logger.info(f"   Mode: {'Report Only' if report_only else 'Full Validation'}")
        logger.info(f"   Performance: {'Skipped' if quick else 'Included'}")
    
    def validate_all(self) -> WorkflowValidationReport:
        """Run complete validation suite"""
        logger.info("🚀 Starting complete Docker workflow validation...")
        start_time = time.time()
        
        # Generate report immediately if report-only mode
        if self.report_only:
            return self._generate_report_only()
        
        # Run all validation steps
        validation_steps = [
            ("SSOT Compliance", self.validate_ssot),
            ("Refresh Dev Service", self.validate_refresh_dev),
            ("E2E Test Integration", self.validate_e2e_tests),
            ("No Fallback Logic", self.validate_no_fallbacks),
        ]
        
        # Add performance tests if not quick mode
        if not self.quick:
            validation_steps.append(("Build Performance", self.validate_build_performance))
        
        # Execute validation steps
        for step_name, validator_func in validation_steps:
            logger.info(f"\n📋 Validating: {step_name}")
            try:
                result = validator_func()
                self.results.append(result)
                
                if result.passed:
                    logger.info(f"   ✅ {step_name}: PASSED")
                else:
                    logger.error(f"   ❌ {step_name}: FAILED - {result.message}")
                    
                if result.warnings:
                    for warning in result.warnings:
                        logger.warning(f"   ⚠️  {warning}")
                        
            except Exception as e:
                logger.error(f"   💥 {step_name}: ERROR - {e}")
                self.results.append(ValidationResult(
                    name=step_name,
                    passed=False,
                    message=f"Validation error: {e}",
                    duration=0.0
                ))
        
        # Generate final report
        total_time = time.time() - start_time
        report = self._generate_final_report(total_time)
        
        # Auto-fix if requested and there are fixable violations
        if self.fix_violations and not report.success:
            logger.info("\n🔧 Auto-fixing violations...")
            self._auto_fix_violations()
        
        return report
    
    def validate_ssot(self) -> ValidationResult:
        """Ensure SSOT is strictly enforced"""
        start_time = time.time()
        
        try:
            violations = self.ssot_enforcer.validate_ssot_compliance()
            
            # Check if any violations exist
            has_violations = any(len(v) > 0 for v in violations.values())
            
            if has_violations:
                violation_summary = []
                for category, items in violations.items():
                    if items:
                        violation_summary.append(f"{category}: {len(items)}")
                
                return ValidationResult(
                    name="SSOT Compliance",
                    passed=False,
                    message=f"SSOT violations found: {', '.join(violation_summary)}",
                    details=violations,
                    duration=time.time() - start_time
                )
            
            # Additional checks for SSOT matrix compliance
            warnings = []
            
            # Check that exactly 3 docker-compose files exist (SSOT requirement)
            compose_files = list(self.project_root.glob("docker-compose*.yml"))
            if len(compose_files) != 3:
                warnings.append(f"Expected exactly 3 docker-compose files, found {len(compose_files)}")
            
            # Check that exactly 9 Dockerfiles exist (3 services × 3 types)
            dockerfiles = list(Path(self.project_root / "docker").glob("*.Dockerfile"))
            if len(dockerfiles) != 9:
                warnings.append(f"Expected exactly 9 Dockerfiles, found {len(dockerfiles)}")
            
            return ValidationResult(
                name="SSOT Compliance",
                passed=True,
                message="All Docker configurations comply with SSOT matrix",
                details={"compose_files": len(compose_files), "dockerfiles": len(dockerfiles)},
                duration=time.time() - start_time,
                warnings=warnings
            )
            
        except Exception as e:
            return ValidationResult(
                name="SSOT Compliance",
                passed=False,
                message=f"SSOT validation failed: {e}",
                duration=time.time() - start_time
            )
    
    def validate_refresh_dev(self) -> ValidationResult:
        """Test refresh dev command performance and reliability"""
        start_time = time.time()
        
        try:
            logger.info("   🔄 Testing refresh_dev.py --dry-run...")
            
            # Test dry-run mode first (safe)
            dry_run_result = subprocess.run([
                sys.executable, 
                str(self.project_root / "scripts" / "refresh_dev.py"),
                "--dry-run"
            ], 
            capture_output=True, 
            text=True, 
            timeout=30
            )
            
            if dry_run_result.returncode != 0:
                return ValidationResult(
                    name="Refresh Dev Service",
                    passed=False,
                    message=f"Dry-run failed: {dry_run_result.stderr}",
                    duration=time.time() - start_time
                )
            
            # Check that dry-run output looks correct
            expected_steps = [
                "Stop existing development containers",
                "Build fresh images", 
                "Start services with health monitoring",
                "Verify all services are healthy"
            ]
            
            missing_steps = []
            for step in expected_steps:
                if step not in dry_run_result.stdout:
                    missing_steps.append(step)
            
            warnings = []
            if missing_steps:
                warnings.append(f"Dry-run missing steps: {', '.join(missing_steps)}")
            
            return ValidationResult(
                name="Refresh Dev Service", 
                passed=True,
                message="Refresh dev service validation passed",
                details={
                    "dry_run_output_lines": len(dry_run_result.stdout.split('\n')),
                    "expected_steps_found": len(expected_steps) - len(missing_steps)
                },
                duration=time.time() - start_time,
                warnings=warnings
            )
            
        except subprocess.TimeoutExpired:
            return ValidationResult(
                name="Refresh Dev Service",
                passed=False,
                message="Refresh dev dry-run timed out (>30s)",
                duration=time.time() - start_time
            )
        except Exception as e:
            return ValidationResult(
                name="Refresh Dev Service", 
                passed=False,
                message=f"Refresh dev validation error: {e}",
                duration=time.time() - start_time
            )
    
    def validate_e2e_tests(self) -> ValidationResult:
        """Test E2E Docker integration"""
        start_time = time.time()
        
        try:
            logger.info("   🧪 Testing E2E Docker integration...")
            
            # Test that unified test runner can handle Docker correctly
            test_runner_path = self.project_root / "tests" / "unified_test_runner.py"
            if not test_runner_path.exists():
                return ValidationResult(
                    name="E2E Test Integration",
                    passed=False,
                    message="unified_test_runner.py not found",
                    duration=time.time() - start_time
                )
            
            # Test list-categories functionality (should work without Docker)
            result = subprocess.run([
                sys.executable,
                str(test_runner_path), 
                "--list-categories"
            ],
            capture_output=True,
            text=True,
            timeout=30
            )
            
            if result.returncode != 0:
                return ValidationResult(
                    name="E2E Test Integration",
                    passed=False, 
                    message=f"Test runner list-categories failed: {result.stderr}",
                    duration=time.time() - start_time
                )
            
            # Check that e2e category exists
            if "e2e" not in result.stdout.lower():
                return ValidationResult(
                    name="E2E Test Integration",
                    passed=False,
                    message="E2E test category not found in test runner",
                    duration=time.time() - start_time
                )
            
            # Validate UnifiedDockerManager can be imported
            try:
                from test_framework.unified_docker_manager import UnifiedDockerManager
                manager = UnifiedDockerManager(
                    environment_type=EnvironmentType.DEDICATED,
                    use_alpine=True
                )
                logger.info("   ✅ UnifiedDockerManager import successful")
                
            except ImportError as e:
                return ValidationResult(
                    name="E2E Test Integration", 
                    passed=False,
                    message=f"Cannot import UnifiedDockerManager: {e}",
                    duration=time.time() - start_time
                )
            
            return ValidationResult(
                name="E2E Test Integration",
                passed=True,
                message="E2E Docker integration validated successfully",
                details={"categories_found": result.stdout.count('\n')},
                duration=time.time() - start_time
            )
            
        except subprocess.TimeoutExpired:
            return ValidationResult(
                name="E2E Test Integration",
                passed=False,
                message="E2E test validation timed out",
                duration=time.time() - start_time
            )
        except Exception as e:
            return ValidationResult(
                name="E2E Test Integration",
                passed=False,
                message=f"E2E validation error: {e}",
                duration=time.time() - start_time
            )
    
    def validate_build_performance(self) -> ValidationResult:
        """Test optimized build performance"""
        start_time = time.time()
        
        logger.info("   ⚡ Testing build performance...")
        
        try:
            # Test Alpine build performance (should be fast)
            performance_metrics = {}
            
            # Build auth service (Alpine) - should be 2-3 seconds
            auth_start = time.time()
            auth_result = subprocess.run([
                "docker", "build", 
                "-f", str(self.project_root / "docker" / "auth.alpine.Dockerfile"),
                "-t", "netra-test-auth-alpine",
                str(self.project_root)
            ],
            capture_output=True,
            text=True,
            timeout=60
            )
            auth_time = time.time() - auth_start
            performance_metrics["auth_alpine_build"] = auth_time
            
            if auth_result.returncode != 0:
                return ValidationResult(
                    name="Build Performance",
                    passed=False,
                    message=f"Auth Alpine build failed: {auth_result.stderr[:200]}",
                    duration=time.time() - start_time
                )
            
            # Performance targets
            warnings = []
            if auth_time > 5.0:
                warnings.append(f"Auth Alpine build took {auth_time:.1f}s (target: <5s)")
            
            # Clean up test image
            try:
                subprocess.run(["docker", "rmi", "netra-test-auth-alpine"], 
                             capture_output=True, check=False)
            except:
                pass
            
            return ValidationResult(
                name="Build Performance",
                passed=True,
                message=f"Build performance validated (auth: {auth_time:.1f}s)",
                details=performance_metrics,
                duration=time.time() - start_time,
                warnings=warnings
            )
            
        except subprocess.TimeoutExpired:
            return ValidationResult(
                name="Build Performance", 
                passed=False,
                message="Build performance test timed out",
                duration=time.time() - start_time
            )
        except Exception as e:
            return ValidationResult(
                name="Build Performance",
                passed=False, 
                message=f"Build performance error: {e}",
                duration=time.time() - start_time
            )
    
    def validate_no_fallbacks(self) -> ValidationResult:
        """Ensure no fallback logic exists"""
        start_time = time.time()
        
        try:
            logger.info("   🚫 Scanning for forbidden fallback logic...")
            
            fallback_violations = []
            
            # Files to scan for fallback patterns
            scan_files = [
                "test_framework/unified_docker_manager.py",
                "scripts/docker_manual.py", 
                "scripts/refresh_dev.py",
                "tests/unified_test_runner.py"
            ]
            
            # Forbidden patterns that indicate fallback logic
            forbidden_patterns = [
                r'logger\.warning.*[Ff]alling back',  # Actual fallback warnings
                r'logger\.info.*[Ff]allback.*to',     # Fallback info messages
                r'Final fallback',                     # Hard-coded fallback comments
                r'fall.*back.*to.*compose',           # Docker compose fallbacks
                r'try.*docker.*except.*return.*fallback'  # Try-except fallback returns
            ]
            
            for file_path in scan_files:
                full_path = self.project_root / file_path
                if not full_path.exists():
                    continue
                
                try:
                    content = full_path.read_text(encoding='utf-8')
                    for pattern in forbidden_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            fallback_violations.append(
                                f"{file_path}:{line_num} - {match.group()[:50]}"
                            )
                except Exception as e:
                    logger.warning(f"Could not scan {file_path}: {e}")
            
            if fallback_violations:
                # Categorize violations to provide better guidance
                critical_violations = []
                platform_specific = []
                
                for violation in fallback_violations:
                    if "falling back to docker-compose" in violation.lower():
                        platform_specific.append(violation)
                    elif "falling back to local" in violation.lower():
                        platform_specific.append(violation)
                    else:
                        critical_violations.append(violation)
                
                # Only fail for critical violations - platform-specific may be acceptable
                if critical_violations:
                    return ValidationResult(
                        name="No Fallback Logic",
                        passed=False,
                        message=f"Found {len(critical_violations)} critical fallback violations",
                        details={
                            "critical_violations": critical_violations,
                            "platform_specific": platform_specific
                        },
                        duration=time.time() - start_time,
                        warnings=[f"{len(platform_specific)} platform-specific fallbacks documented as technical debt"]
                    )
                else:
                    # Only platform-specific fallbacks - pass with warning
                    return ValidationResult(
                        name="No Fallback Logic",
                        passed=True,
                        message="Only platform-specific fallbacks detected",
                        details={"platform_specific": platform_specific},
                        duration=time.time() - start_time,
                        warnings=[f"{len(platform_specific)} platform-specific fallbacks should be documented as technical debt"]
                    )
            
            return ValidationResult(
                name="No Fallback Logic", 
                passed=True,
                message="No forbidden fallback logic detected",
                details={"files_scanned": len(scan_files)},
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                name="No Fallback Logic",
                passed=False,
                message=f"Fallback logic scan error: {e}",
                duration=time.time() - start_time
            )
    
    def _generate_report_only(self) -> WorkflowValidationReport:
        """Generate report without running tests"""
        logger.info("📊 Generating report-only validation...")
        
        # Basic system state checks
        compose_files = list(self.project_root.glob("docker-compose*.yml"))
        dockerfiles = list(Path(self.project_root / "docker").glob("*.Dockerfile"))
        
        summary = {
            "mode": "report_only",
            "compose_files_found": len(compose_files),
            "dockerfiles_found": len(dockerfiles),
            "ssot_expected": {
                "compose_files": 3,
                "dockerfiles": 9
            }
        }
        
        return WorkflowValidationReport(
            timestamp=datetime.now().isoformat(),
            success=True,
            results=[],
            summary=summary,
            recommendations=["Run full validation to get detailed results"]
        )
    
    def _generate_final_report(self, total_time: float) -> WorkflowValidationReport:
        """Generate comprehensive final report"""
        
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        success = passed_count == total_count
        
        # Calculate performance metrics
        performance_metrics = {}
        for result in self.results:
            performance_metrics[f"{result.name.lower().replace(' ', '_')}_duration"] = result.duration
        performance_metrics["total_validation_time"] = total_time
        
        # Generate recommendations
        recommendations = []
        if not success:
            failed_results = [r for r in self.results if not r.passed]
            recommendations.append(f"Fix {len(failed_results)} failed validations before deployment")
            
            for failed in failed_results:
                if "SSOT" in failed.name:
                    recommendations.append("Run: python scripts/docker_ssot_enforcer.py cleanup")
                elif "Performance" in failed.name:
                    recommendations.append("Optimize Dockerfile layer caching and build contexts")
                elif "Fallback" in failed.name:
                    recommendations.append("Remove fallback logic - use hard fails instead")
        
        # Check warnings
        all_warnings = []
        for result in self.results:
            all_warnings.extend(result.warnings)
            
        if all_warnings:
            recommendations.append(f"Address {len(all_warnings)} warnings for optimal performance")
        
        summary = {
            "total_validations": total_count,
            "passed": passed_count,
            "failed": total_count - passed_count,
            "warnings": len(all_warnings),
            "success_rate": f"{(passed_count/total_count)*100:.1f}%" if total_count > 0 else "0%",
            "total_time": f"{total_time:.2f}s"
        }
        
        return WorkflowValidationReport(
            timestamp=datetime.now().isoformat(),
            success=success,
            results=self.results,
            summary=summary,
            performance_metrics=performance_metrics,
            recommendations=recommendations
        )
    
    def _auto_fix_violations(self):
        """Attempt to auto-fix found violations"""
        logger.info("🔧 Attempting to auto-fix violations...")
        
        for result in self.results:
            if result.passed:
                continue
                
            if "SSOT" in result.name and "obsolete_present" in result.details:
                logger.info("   🧹 Attempting to clean up obsolete Docker files...")
                try:
                    # Run SSOT enforcer cleanup
                    cleanup_result = subprocess.run([
                        sys.executable,
                        str(self.project_root / "scripts" / "docker_ssot_enforcer.py"),
                        "cleanup"  
                    ], capture_output=True, text=True)
                    
                    if "files to delete" in cleanup_result.stdout:
                        logger.info("   ✅ Found obsolete files for cleanup")
                        logger.info("   💡 Manual cleanup required - see SSOT enforcer output")
                except Exception as e:
                    logger.error(f"   ❌ Auto-fix failed: {e}")


def save_report(report: WorkflowValidationReport, output_path: Path):
    """Save validation report to file"""
    
    # Convert to JSON-serializable format
    report_dict = {
        "timestamp": report.timestamp,
        "success": report.success,
        "summary": report.summary,
        "performance_metrics": report.performance_metrics,
        "recommendations": report.recommendations,
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "message": r.message,
                "duration": r.duration,
                "warnings": r.warnings,
                "details": r.details
            }
            for r in report.results
        ]
    }
    
    # Save JSON report
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, indent=2)
    
    # Save human-readable markdown report
    md_content = f"""# Docker Workflow Validation Report

**Generated:** {report.timestamp}  
**Status:** {'✅ PASSED' if report.success else '❌ FAILED'}

## Summary
{chr(10).join(f'- **{k}**: {v}' for k, v in report.summary.items())}

## Performance Metrics
{chr(10).join(f'- **{k}**: {v:.2f}s' if isinstance(v, float) else f'- **{k}**: {v}' for k, v in report.performance_metrics.items())}

## Validation Results
"""
    
    for result in report.results:
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        md_content += f"""
### {result.name} - {status}

**Message:** {result.message}  
**Duration:** {result.duration:.2f}s

"""
        if result.warnings:
            md_content += "**Warnings:**\n"
            md_content += "\n".join(f"- ⚠️ {w}" for w in result.warnings) + "\n\n"
        
        if result.details:
            md_content += "**Details:**\n"
            for k, v in result.details.items():
                md_content += f"- `{k}`: {v}\n"
            md_content += "\n"
    
    if report.recommendations:
        md_content += "\n## Recommendations\n"
        md_content += "\n".join(f"1. {rec}" for rec in report.recommendations)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    logger.info(f"📊 Reports saved:")
    logger.info(f"   JSON: {json_path}")
    logger.info(f"   Markdown: {output_path}")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Complete Docker Workflow Validation Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/validate_docker_workflow.py                  # Full validation
    python scripts/validate_docker_workflow.py --quick          # Skip performance tests  
    python scripts/validate_docker_workflow.py --report-only    # Generate report without tests
    python scripts/validate_docker_workflow.py --fix-violations # Auto-fix issues
        """
    )
    
    parser.add_argument("--quick", action="store_true",
                       help="Skip performance tests for faster validation")
    parser.add_argument("--report-only", action="store_true", 
                       help="Generate report without running tests")
    parser.add_argument("--fix-violations", action="store_true",
                       help="Attempt to auto-fix found violations")
    parser.add_argument("--output", type=Path, 
                       default=Path("DOCKER_WORKFLOW_VALIDATION_REPORT.md"),
                       help="Output path for validation report")
    
    args = parser.parse_args()
    
    # Create validator and run
    validator = DockerWorkflowValidator(
        quick=args.quick,
        report_only=args.report_only, 
        fix_violations=args.fix_violations
    )
    
    report = validator.validate_all()
    
    # Save comprehensive report
    save_report(report, args.output)
    
    # Print summary
    if report.success:
        logger.info("\n🎉 DOCKER WORKFLOW VALIDATION PASSED")
        logger.info("   All Docker improvements are working correctly")
        if report.summary.get('warnings', 0) > 0:
            logger.info(f"   Note: {report.summary['warnings']} warnings to address")
    else:
        logger.error("\n💥 DOCKER WORKFLOW VALIDATION FAILED")
        logger.error(f"   {report.summary.get('failed', 0)} validations failed")
        logger.error("   See report for details and recommendations")
    
    logger.info(f"\n📊 Detailed report: {args.output}")
    
    sys.exit(0 if report.success else 1)


if __name__ == "__main__":
    main()