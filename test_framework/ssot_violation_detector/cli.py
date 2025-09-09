"""
SSOT Violation Detection CLI

Command-line interface for detecting and reporting SSOT violations
in the message repository patterns across the codebase.

Business Value:
- Provides automated SSOT compliance checking
- Enables CI/CD integration for violation detection
- Supports systematic remediation tracking
- Maintains code quality standards

Usage:
    python -m test_framework.ssot_violation_detector.cli --check-compliance
    python -m test_framework.ssot_violation_detector.cli --analyze-patterns
    python -m test_framework.ssot_violation_detector.cli --generate-report
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from .violation_detector import SSotViolationDetector, ComparisonReport
from .message_pattern_analyzer import MessagePatternAnalyzer, AnalysisResult
from .violation_reporter import ViolationReporter


class SSotViolationCLI:
    """Command-line interface for SSOT violation detection."""
    
    def __init__(self):
        self.detector = SSotViolationDetector()
        self.analyzer = MessagePatternAnalyzer()
        self.reporter = ViolationReporter()
        
    async def check_compliance(self, target_dirs: List[str] = None) -> bool:
        """
        Check SSOT compliance across the codebase.
        
        Returns:
            True if compliant, False if violations found
        """
        print("🔍 Checking SSOT Compliance...")
        
        # Analyze codebase patterns
        analysis_result = self.analyzer.analyze_codebase(target_dirs)
        
        print(f"📊 Analysis Results:")
        print(f"   Files scanned: {analysis_result.total_files_scanned}")
        print(f"   Violations found: {analysis_result.total_matches}")
        print(f"   Critical violations: {analysis_result.violations_by_severity.get('critical', 0)}")
        print(f"   High violations: {analysis_result.violations_by_severity.get('high', 0)}")
        
        # Check compliance score
        compliance_score = analysis_result.summary.get("ssot_compliance_score", 0)
        print(f"   Compliance score: {compliance_score}%")
        
        # Determine compliance status
        is_compliant = (
            analysis_result.violations_by_severity.get('critical', 0) == 0 and
            analysis_result.violations_by_severity.get('high', 0) <= 3 and
            compliance_score >= 95.0
        )
        
        if is_compliant:
            print("✅ SSOT Compliance: PASSED")
            return True
        else:
            print("❌ SSOT Compliance: FAILED")
            print("\n🚨 Critical Issues Found:")
            
            for match in analysis_result.pattern_matches:
                if match.severity in ["critical", "high"]:
                    print(f"   {match.file_path}:{match.line_number} - {match.description}")
                    
            return False
            
    async def analyze_patterns(self, target_dirs: List[str] = None) -> AnalysisResult:
        """
        Analyze message creation patterns in the codebase.
        
        Returns:
            AnalysisResult with detailed pattern analysis
        """
        print("🔍 Analyzing Message Creation Patterns...")
        
        analysis_result = self.analyzer.analyze_codebase(target_dirs)
        
        print(f"\n📊 Pattern Analysis Complete:")
        print(f"   Total files scanned: {analysis_result.total_files_scanned}")
        print(f"   Pattern matches found: {analysis_result.total_matches}")
        print(f"   Files with violations: {len(analysis_result.files_with_violations)}")
        
        # Show violations by type
        if analysis_result.violations_by_type:
            print(f"\n📋 Violations by Type:")
            for violation_type, count in sorted(analysis_result.violations_by_type.items(), key=lambda x: x[1], reverse=True):
                print(f"   {violation_type}: {count}")
                
        # Show top violation files
        if analysis_result.summary.get("files_with_highest_violations"):
            print(f"\n🎯 Top Violation Files:")
            for file_info in analysis_result.summary["files_with_highest_violations"]:
                print(f"   {file_info['file']}: {file_info['violation_count']} violations")
                
        return analysis_result
        
    async def generate_report(self, output_dir: str = "reports/ssot_violations") -> Dict[str, str]:
        """
        Generate comprehensive SSOT violation report.
        
        Args:
            output_dir: Directory to save reports
            
        Returns:
            Dictionary with paths to generated report files
        """
        print("📝 Generating SSOT Violation Report...")
        
        # Analyze patterns
        analysis_result = await self.analyze_patterns()
        
        # For now, create empty detection reports since we can't run the detector
        # without database connectivity in this environment
        detection_reports = []
        
        # Generate comprehensive report
        self.reporter.output_dir = Path(output_dir)
        report_files = self.reporter.generate_comprehensive_report(
            detection_reports=detection_reports,
            analysis_result=analysis_result,
            report_name=f"ssot_violation_analysis_{int(time.time())}"
        )
        
        print(f"\n📄 Reports Generated:")
        for report_type, file_path in report_files.items():
            print(f"   {report_type}: {file_path}")
            
        return report_files
        
    async def detect_specific_violation(self, file_path: str, line_number: int) -> Dict:
        """
        Analyze a specific violation in detail.
        
        Args:
            file_path: Path to file containing violation
            line_number: Line number of violation
            
        Returns:
            Detailed analysis of the specific violation
        """
        print(f"🔍 Analyzing specific violation: {file_path}:{line_number}")
        
        analysis = self.analyzer.analyze_specific_violation(file_path, line_number)
        
        if "error" in analysis:
            print(f"❌ Error: {analysis['error']}")
            return analysis
            
        print(f"\n📋 Violation Analysis:")
        print(f"   File: {analysis['file_path']}")
        print(f"   Line: {analysis['line_number']}")
        print(f"   Content: {analysis['line_content']}")
        
        if analysis.get("matching_patterns"):
            print(f"\n🚨 Matching Patterns:")
            for pattern in analysis["matching_patterns"]:
                print(f"   {pattern['pattern_name']} ({pattern['severity']}): {pattern['description']}")
                
        if analysis.get("remediation_suggestions"):
            print(f"\n💡 Remediation Suggestions:")
            for suggestion in analysis["remediation_suggestions"]:
                print(f"   - {suggestion}")
                
        return analysis


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SSOT Violation Detection CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m test_framework.ssot_violation_detector.cli --check-compliance
  python -m test_framework.ssot_violation_detector.cli --analyze-patterns --target-dirs netra_backend test_framework
  python -m test_framework.ssot_violation_detector.cli --generate-report --output-dir reports/custom
  python -m test_framework.ssot_violation_detector.cli --analyze-violation test_framework/ssot/database.py 596
        """
    )
    
    parser.add_argument(
        "--check-compliance",
        action="store_true",
        help="Check SSOT compliance and exit with status code"
    )
    
    parser.add_argument(
        "--analyze-patterns",
        action="store_true",
        help="Analyze message creation patterns in codebase"
    )
    
    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate comprehensive violation report"
    )
    
    parser.add_argument(
        "--analyze-violation",
        nargs=2,
        metavar=("FILE", "LINE"),
        help="Analyze specific violation at file:line"
    )
    
    parser.add_argument(
        "--target-dirs",
        nargs="+",
        help="Specific directories to analyze (default: entire project)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="reports/ssot_violations",
        help="Output directory for reports (default: reports/ssot_violations)"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )
    
    args = parser.parse_args()
    
    if not any([args.check_compliance, args.analyze_patterns, args.generate_report, args.analyze_violation]):
        parser.print_help()
        return 1
        
    cli = SSotViolationCLI()
    
    async def run_cli():
        try:
            if args.check_compliance:
                is_compliant = await cli.check_compliance(args.target_dirs)
                return 0 if is_compliant else 1
                
            elif args.analyze_patterns:
                result = await cli.analyze_patterns(args.target_dirs)
                if args.json:
                    print(json.dumps({
                        "total_files_scanned": result.total_files_scanned,
                        "total_matches": result.total_matches,
                        "violations_by_severity": result.violations_by_severity,
                        "violations_by_type": result.violations_by_type,
                        "files_with_violations": result.files_with_violations,
                        "summary": result.summary
                    }, indent=2))
                return 0
                
            elif args.generate_report:
                report_files = await cli.generate_report(args.output_dir)
                if args.json:
                    print(json.dumps(report_files, indent=2))
                return 0
                
            elif args.analyze_violation:
                file_path, line_number = args.analyze_violation
                result = await cli.detect_specific_violation(file_path, int(line_number))
                if args.json:
                    print(json.dumps(result, indent=2))
                return 0
                
        except Exception as e:
            print(f"💥 CLI Error: {e}")
            return 1
            
    # Run the async CLI
    exit_code = asyncio.run(run_cli())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()