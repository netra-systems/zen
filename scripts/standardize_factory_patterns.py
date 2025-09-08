#!/usr/bin/env python3
"""
Factory Pattern Standardization Script

This script implements systematic factory pattern standardization to address
the ROOT CAUSE #3: Factory Pattern Consistency - Unified validation across all factories

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Systematic prevention of parameter mismatch failures
- Value Impact: Zero production failures from factory interface inconsistencies
- Strategic Impact: Addresses WHY #3 in the Five Whys analysis

Key Features:
- Automated parameter name standardization
- Factory-to-constructor mapping validation
- SSOT parameter name enforcement
- Comprehensive pattern analysis
- Safe batch transformation

Root Cause Prevention:
- WHY #3: Factory Pattern Consistency - Enforces unified patterns
- WHY #2: Parameter Name Standardization - Automated SSOT naming
- WHY #1: Better Error Messages - Clear transformation reporting

Usage:
    python scripts/standardize_factory_patterns.py --analyze        # Analyze patterns
    python scripts/standardize_factory_patterns.py --standardize   # Apply fixes
    python scripts/standardize_factory_patterns.py --verify        # Verify changes
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import json
import logging
from dataclasses import dataclass, field
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ParameterMismatchPattern:
    """Represents a parameter mismatch pattern to fix."""
    old_name: str
    new_name: str
    context_patterns: List[str] = field(default_factory=list)
    file_extensions: Set[str] = field(default_factory=lambda: {'.py'})
    description: str = ""
    
    def __post_init__(self):
        if not self.description:
            self.description = f"Replace {self.old_name} with {self.new_name}"


@dataclass
class FactoryPatternViolation:
    """Represents a detected factory pattern violation."""
    file_path: Path
    line_number: int
    line_content: str
    violation_type: str
    old_parameter: str
    suggested_fix: str
    context: str = ""


@dataclass
class StandardizationResult:
    """Result of standardization operation."""
    files_analyzed: int = 0
    violations_found: List[FactoryPatternViolation] = field(default_factory=list)
    fixes_applied: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    patterns_detected: Dict[str, int] = field(default_factory=dict)


class FactoryPatternStandardizer:
    """Standardizes factory patterns across the codebase."""
    
    def __init__(self):
        self.mismatch_patterns = self._initialize_mismatch_patterns()
        self.result = StandardizationResult()
        self.dry_run = True
        
    def _initialize_mismatch_patterns(self) -> List[ParameterMismatchPattern]:
        """Initialize known parameter mismatch patterns."""
        patterns = [
            # CRITICAL: The exact issue from the Five Whys analysis
            ParameterMismatchPattern(
                old_name="websocket_connection_id",
                new_name="websocket_client_id",
                context_patterns=[
                    r"UserExecutionContext\s*\(",
                    r"\.from_request\s*\(",
                    r"create_supervisor",
                    r"get_websocket_scoped_supervisor",
                    r"create_agent_instance",
                    r"create_websocket_manager"
                ],
                description="Fix WebSocket parameter mismatch - ROOT CAUSE of supervisor factory bug"
            ),
            
            # Related parameter inconsistencies
            ParameterMismatchPattern(
                old_name="connection_id",
                new_name="websocket_client_id",
                context_patterns=[
                    r"websocket.*=.*connection_id",
                    r"UserExecutionContext.*connection_id"
                ],
                description="Standardize connection_id to websocket_client_id in WebSocket contexts"
            ),
            
            # Database session consistency
            ParameterMismatchPattern(
                old_name="db_session",
                new_name="db_session",  # Already correct, but validate usage
                context_patterns=[
                    r"UserExecutionContext\s*\(",
                    r"\.from_request\s*\("
                ],
                description="Validate db_session parameter usage consistency"
            ),
            
            # Factory method naming consistency  
            ParameterMismatchPattern(
                old_name="user_context",
                new_name="user_context",  # Already correct, validate type
                context_patterns=[
                    r"def.*create_.*\(",
                    r"factory.*user_context"
                ],
                description="Validate user_context parameter type consistency"
            )
        ]
        
        return patterns
    
    def analyze_directory(self, directory: Path, pattern: str = "*.py") -> StandardizationResult:
        """Analyze directory for factory pattern violations."""
        logger.info(f"Analyzing factory patterns in {directory}")
        
        self.result = StandardizationResult()
        
        for py_file in directory.rglob(pattern):
            if self._should_skip_file(py_file):
                continue
                
            try:
                self._analyze_file(py_file)
                self.result.files_analyzed += 1
            except Exception as e:
                error_msg = f"Error analyzing {py_file}: {e}"
                logger.warning(error_msg)
                self.result.errors.append(error_msg)
        
        logger.info(f"Analysis complete: {self.result.files_analyzed} files, {len(self.result.violations_found)} violations")
        return self.result
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single file for factory pattern violations."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            self.result.errors.append(f"Could not read {file_path}: {e}")
            return
        
        for line_num, line in enumerate(lines, 1):
            self._analyze_line(file_path, line_num, line)
    
    def _analyze_line(self, file_path: Path, line_num: int, line: str) -> None:
        """Analyze a single line for factory pattern violations."""
        for pattern in self.mismatch_patterns:
            # Skip if this is the same parameter (validation patterns)
            if pattern.old_name == pattern.new_name:
                continue
                
            # Look for the old parameter name
            old_param_regex = rf"\\b{re.escape(pattern.old_name)}\\s*="
            if re.search(old_param_regex, line):
                # Check if this line matches any context patterns
                context_match = False
                matched_context = ""
                
                for context_pattern in pattern.context_patterns:
                    if re.search(context_pattern, line, re.IGNORECASE):
                        context_match = True
                        matched_context = context_pattern
                        break
                
                # For the critical websocket_connection_id issue, also check surrounding context
                if pattern.old_name == "websocket_connection_id":
                    # Check if this is in a UserExecutionContext creation context
                    context_match = self._check_websocket_context(file_path, line_num, line)
                    if context_match:
                        matched_context = "UserExecutionContext constructor context"
                
                if context_match:
                    violation = FactoryPatternViolation(
                        file_path=file_path,
                        line_number=line_num,
                        line_content=line.strip(),
                        violation_type="parameter_mismatch",
                        old_parameter=pattern.old_name,
                        suggested_fix=line.replace(pattern.old_name, pattern.new_name).strip(),
                        context=matched_context
                    )
                    
                    self.result.violations_found.append(violation)
                    
                    # Track pattern frequency
                    pattern_key = f"{pattern.old_name} -> {pattern.new_name}"
                    self.result.patterns_detected[pattern_key] = self.result.patterns_detected.get(pattern_key, 0) + 1
    
    def _check_websocket_context(self, file_path: Path, line_num: int, line: str) -> bool:
        """Check if line is in a WebSocket-related context that needs fixing."""
        # Read surrounding lines for context
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
        except Exception:
            return False
        
        # Check 5 lines before and after for UserExecutionContext patterns
        start_line = max(0, line_num - 6)
        end_line = min(len(all_lines), line_num + 5)
        
        context_lines = all_lines[start_line:end_line]
        context_text = ''.join(context_lines)
        
        # Look for UserExecutionContext constructor patterns
        context_patterns = [
            r"UserExecutionContext\\s*\\(",
            r"user_context\\s*=.*UserExecutionContext",
            r"from_request.*\\(",
            r"create_supervisor",
            r"websocket.*factory",
            r"supervisor.*factory"
        ]
        
        for pattern in context_patterns:
            if re.search(pattern, context_text, re.IGNORECASE):
                return True
        
        return False
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            "__pycache__",
            ".git",
            "venv",
            ".pyc",
            "node_modules",
            ".pytest_cache",
            "htmlcov",
            "reports/coverage"
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def standardize_patterns(self, directory: Path, dry_run: bool = True) -> StandardizationResult:
        """Apply factory pattern standardization."""
        self.dry_run = dry_run
        
        # First analyze to find violations
        result = self.analyze_directory(directory)
        
        if not result.violations_found:
            logger.info("No factory pattern violations found")
            return result
        
        logger.info(f"Found {len(result.violations_found)} violations to fix")
        
        if dry_run:
            logger.info("DRY RUN: Would apply the following fixes:")
            self._report_planned_fixes(result)
        else:
            logger.info("Applying factory pattern fixes...")
            self._apply_fixes(result)
        
        return result
    
    def _report_planned_fixes(self, result: StandardizationResult) -> None:
        """Report what fixes would be applied."""
        by_file = defaultdict(list)
        for violation in result.violations_found:
            by_file[violation.file_path].append(violation)
        
        for file_path, violations in by_file.items():
            logger.info(f"  {file_path} ({len(violations)} fixes):")
            for violation in violations[:3]:  # Show first 3
                logger.info(f"    Line {violation.line_number}: {violation.old_parameter} -> {violation.suggested_fix}")
            if len(violations) > 3:
                logger.info(f"    ... and {len(violations) - 3} more fixes")
    
    def _apply_fixes(self, result: StandardizationResult) -> None:
        """Apply the standardization fixes."""
        by_file = defaultdict(list)
        for violation in result.violations_found:
            by_file[violation.file_path].append(violation)
        
        for file_path, violations in by_file.items():
            try:
                fixes_applied = self._fix_file(file_path, violations)
                result.fixes_applied.extend(fixes_applied)
                logger.info(f"Applied {len(fixes_applied)} fixes to {file_path}")
            except Exception as e:
                error_msg = f"Error fixing {file_path}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
    
    def _fix_file(self, file_path: Path, violations: List[FactoryPatternViolation]) -> List[Dict[str, Any]]:
        """Apply fixes to a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise Exception(f"Could not read file: {e}")
        
        original_content = content
        fixes_applied = []
        
        # Sort violations by line number (descending) to avoid line number shifts
        violations_sorted = sorted(violations, key=lambda v: v.line_number, reverse=True)
        
        for violation in violations_sorted:
            # Apply the fix using regex replacement
            pattern = rf"\\b{re.escape(violation.old_parameter)}\\s*="
            replacement = f"{violation.old_parameter.replace(violation.old_parameter, violation.old_parameter.replace(violation.old_parameter, violation.suggested_fix.split('=')[0]))}="
            
            # More precise replacement using the exact parameter name
            old_param = violation.old_parameter
            # Extract new parameter from suggested fix
            new_param = None
            for mismatch_pattern in self.mismatch_patterns:
                if mismatch_pattern.old_name == old_param:
                    new_param = mismatch_pattern.new_name
                    break
            
            if new_param and new_param != old_param:
                pattern = rf"\\b{re.escape(old_param)}\\s*="
                replacement = f"{new_param}="
                
                new_content = re.sub(pattern, replacement, content)
                
                if new_content != content:
                    content = new_content
                    fixes_applied.append({
                        "line_number": violation.line_number,
                        "old_parameter": old_param,
                        "new_parameter": new_param,
                        "context": violation.context
                    })
        
        # Write the fixed content back
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return fixes_applied
    
    def verify_standardization(self, directory: Path) -> Dict[str, Any]:
        """Verify that standardization was successful."""
        logger.info("Verifying factory pattern standardization...")
        
        # Re-analyze to check for remaining violations
        result = self.analyze_directory(directory)
        
        verification_report = {
            "remaining_violations": len(result.violations_found),
            "files_with_violations": len(set(v.file_path for v in result.violations_found)),
            "critical_websocket_violations": len([
                v for v in result.violations_found 
                if v.old_parameter == "websocket_connection_id"
            ]),
            "verification_status": "PASS" if len(result.violations_found) == 0 else "FAIL",
            "remaining_patterns": result.patterns_detected
        }
        
        if verification_report["remaining_violations"] == 0:
            logger.info("✅ Verification PASSED: No factory pattern violations found")
        else:
            logger.warning(f"❌ Verification FAILED: {verification_report['remaining_violations']} violations remain")
            
            # Show critical violations
            critical_violations = [
                v for v in result.violations_found 
                if v.old_parameter == "websocket_connection_id"
            ]
            
            if critical_violations:
                logger.error(f"🚨 CRITICAL: {len(critical_violations)} websocket_connection_id violations remain:")
                for violation in critical_violations[:5]:
                    logger.error(f"  {violation.file_path}:{violation.line_number} - {violation.old_parameter}")
        
        return verification_report
    
    def generate_report(self, result: StandardizationResult) -> str:
        """Generate comprehensive report."""
        report_lines = [
            "=" * 80,
            "FACTORY PATTERN STANDARDIZATION REPORT",
            "=" * 80,
            "",
            "SUMMARY:",
            f"  Files Analyzed: {result.files_analyzed}",
            f"  Violations Found: {len(result.violations_found)}",
            f"  Fixes Applied: {len(result.fixes_applied)}",
            f"  Errors: {len(result.errors)}",
            ""
        ]
        
        # Pattern frequency
        if result.patterns_detected:
            report_lines.append("DETECTED PATTERNS:")
            for pattern, count in sorted(result.patterns_detected.items(), key=lambda x: x[1], reverse=True):
                report_lines.append(f"  {count:3d}: {pattern}")
            report_lines.append("")
        
        # Critical violations (websocket_connection_id)
        critical_violations = [
            v for v in result.violations_found 
            if v.old_parameter == "websocket_connection_id"
        ]
        
        if critical_violations:
            report_lines.append("🚨 CRITICAL VIOLATIONS (ROOT CAUSE):")
            report_lines.append(f"  websocket_connection_id violations: {len(critical_violations)}")
            report_lines.append("  These cause the exact supervisor factory bug from the Five Whys analysis!")
            report_lines.append("")
            
            for violation in critical_violations[:10]:  # Show first 10
                report_lines.append(f"  {violation.file_path}:{violation.line_number}")
                report_lines.append(f"    OLD: {violation.line_content}")
                report_lines.append(f"    NEW: {violation.suggested_fix}")
                report_lines.append("")
        
        # Fixes applied
        if result.fixes_applied:
            by_file = defaultdict(list)
            for fix in result.fixes_applied:
                file_key = f"{fix.get('file_path', 'unknown')}"
                by_file[file_key].append(fix)
            
            report_lines.append("FIXES APPLIED:")
            for file_path, fixes in by_file.items():
                report_lines.append(f"  {file_path} ({len(fixes)} fixes)")
            report_lines.append("")
        
        # Errors
        if result.errors:
            report_lines.append("ERRORS:")
            for error in result.errors:
                report_lines.append(f"  - {error}")
            report_lines.append("")
        
        return "\\n".join(report_lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Standardize factory patterns to prevent interface contract violations",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--dir", "-d",
        type=Path,
        default=project_root / "netra_backend",
        help="Directory to standardize (default: netra_backend)"
    )
    
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze factory patterns without making changes"
    )
    
    parser.add_argument(
        "--standardize",
        action="store_true", 
        help="Apply factory pattern standardization"
    )
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify standardization results"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file for report"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Default to analyze if no action specified
    if not any([args.analyze, args.standardize, args.verify]):
        args.analyze = True
    
    standardizer = FactoryPatternStandardizer()
    
    try:
        if args.analyze:
            logger.info("Analyzing factory patterns...")
            result = standardizer.analyze_directory(args.dir)
            
            if args.json:
                output = {
                    "files_analyzed": result.files_analyzed,
                    "violations_found": len(result.violations_found),
                    "patterns_detected": result.patterns_detected,
                    "violations": [
                        {
                            "file": str(v.file_path),
                            "line": v.line_number,
                            "old_param": v.old_parameter,
                            "violation_type": v.violation_type,
                            "context": v.context
                        }
                        for v in result.violations_found
                    ]
                }
                output_content = json.dumps(output, indent=2)
            else:
                output_content = standardizer.generate_report(result)
        
        elif args.standardize:
            logger.info("Applying factory pattern standardization...")
            result = standardizer.standardize_patterns(args.dir, dry_run=False)
            output_content = standardizer.generate_report(result)
        
        elif args.verify:
            verification_result = standardizer.verify_standardization(args.dir)
            output_content = json.dumps(verification_result, indent=2) if args.json else str(verification_result)
        
        # Output results
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            logger.info(f"Report written to {args.output}")
        else:
            print(output_content)
        
        # Exit code based on critical violations
        if hasattr(result, 'violations_found'):
            critical_violations = [
                v for v in result.violations_found 
                if v.old_parameter == "websocket_connection_id"
            ]
            if critical_violations:
                logger.error(f"🚨 CRITICAL: {len(critical_violations)} websocket_connection_id violations found")
                sys.exit(1)
        
        logger.info("Factory pattern standardization completed successfully")
        
    except Exception as e:
        logger.error(f"Factory pattern standardization failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()