#!/usr/bin/env python3
"""
NETRA APEX INTELLIGENT COVERAGE ANALYZER
========================================

Claude command for generating meaningful unit test coverage reports and identifying 
high-priority test creation opportunities.

USAGE:
    python scripts/coverage_intelligence.py                 # Full analysis report
    python scripts/coverage_intelligence.py --priority-only # Just priority tests
    python scripts/coverage_intelligence.py --format json   # Machine-readable output
    python scripts/coverage_intelligence.py --threshold 80  # Custom coverage threshold

FEATURES:
    - Line vs Branch coverage analysis with detailed explanations
    - Business value-weighted test priority scoring
    - Critical path and risk analysis
    - Test gap identification with specific recommendations
    - SSOT compliance validation for test suggestions
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import argparse
import subprocess
import re

# Windows encoding fix - MUST be before any print statements
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Ensure absolute imports from project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import IsolatedEnvironment

@dataclass 
class CoverageMetrics:
    """Coverage metrics for a single file."""
    file_path: str
    line_coverage: float
    branch_coverage: float
    total_lines: int
    covered_lines: int
    missing_lines: int
    total_branches: int
    covered_branches: int
    missing_branches: int
    complexity_score: float
    business_value_score: float
    test_priority_score: float

@dataclass
class TestRecommendation:
    """Recommendation for creating a new test."""
    file_path: str
    test_type: str  # unit, integration, e2e
    priority_score: float
    reason: str
    missing_coverage_areas: List[str]
    suggested_test_name: str
    business_justification: str

@dataclass
class CoverageAnalysisReport:
    """Complete coverage analysis report."""
    overall_line_coverage: float
    overall_branch_coverage: float
    coverage_gap: float
    total_files_analyzed: int
    files_below_threshold: int
    high_priority_files: List[CoverageMetrics]
    test_recommendations: List[TestRecommendation]
    line_vs_branch_explanation: str
    summary: str

class CoverageIntelligenceAnalyzer:
    """
    Intelligent coverage analyzer that provides business-focused insights
    and actionable test creation recommendations.
    """
    
    def __init__(self, coverage_threshold: float = 80.0):
        self.coverage_threshold = coverage_threshold
        self.project_root = PROJECT_ROOT
        self.reports_dir = self.project_root / "reports" / "coverage"
        
        # Business value weights for different file types
        self.business_value_weights = {
            'agents/': 10.0,          # Core business logic
            'routes/': 9.0,           # User-facing APIs
            'services/': 8.5,         # Business services
            'websocket': 8.0,         # Real-time user experience
            'core/': 7.5,            # Platform infrastructure
            'llm/': 7.0,             # AI capabilities
            'models/': 6.0,          # Data models
            'factories/': 5.5,       # Dependency injection
            'utils/': 4.0,           # Utilities
        }
    
    def calculate_business_value_score(self, file_path: str) -> float:
        """Calculate business value score based on file path and content analysis."""
        score = 1.0  # Base score
        
        # Path-based scoring
        for pattern, weight in self.business_value_weights.items():
            if pattern in file_path.lower():
                score = max(score, weight)
        
        # Critical files get maximum score
        critical_patterns = [
            'unified_', 'ssot_', 'factory', 'auth', 'websocket', 
            'agent_execution', 'tool_dispatcher', 'user_context'
        ]
        
        for pattern in critical_patterns:
            if pattern in Path(file_path).name.lower():
                score = max(score, 9.5)
        
        return score
    
    def calculate_complexity_score(self, file_path: str) -> float:
        """Estimate code complexity based on file analysis."""
        try:
            content = Path(file_path).read_text(encoding='utf-8')
            
            # Basic complexity indicators
            complexity = 0
            complexity += len(re.findall(r'\bif\b', content)) * 1.5
            complexity += len(re.findall(r'\bwhile\b|\bfor\b', content)) * 2
            complexity += len(re.findall(r'\btry\b|\bexcept\b', content)) * 2
            complexity += len(re.findall(r'\basync\b|\bawait\b', content)) * 1.5
            complexity += len(re.findall(r'\bclass\b', content)) * 3
            complexity += len(re.findall(r'\bdef\b', content)) * 1
            
            # Normalize by lines of code
            lines = len(content.splitlines())
            if lines > 0:
                complexity = complexity / lines * 100
            
            return min(complexity, 10.0)  # Cap at 10
        except Exception:
            return 5.0  # Default medium complexity
    
    def load_coverage_data(self) -> Optional[Dict]:
        """Load coverage data from JSON report."""
        json_report = self.reports_dir / "coverage.json"
        if not json_report.exists():
            print(f"❌ Coverage JSON report not found: {json_report}")
            print("   Run tests with coverage first: python tests/unified_test_runner.py --category unit")
            return None
        
        try:
            with open(json_report, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading coverage data: {e}")
            return None
    
    def load_xml_coverage_data(self) -> Optional[ET.Element]:
        """Load coverage data from XML report for branch coverage."""
        xml_report = self.reports_dir / "coverage.xml"
        if not xml_report.exists():
            return None
        
        try:
            tree = ET.parse(xml_report)
            return tree.getroot()
        except Exception:
            return None
    
    def analyze_file_coverage(self, file_path: str, file_data: Dict, xml_data: Optional[ET.Element] = None) -> CoverageMetrics:
        """Analyze coverage metrics for a single file."""
        summary = file_data.get('summary', {})
        
        # Line coverage metrics
        total_lines = summary.get('num_statements', 0)
        covered_lines = summary.get('covered_lines', 0)
        missing_lines = summary.get('missing_lines', 0)
        line_coverage = summary.get('percent_covered', 0)
        
        # Branch coverage metrics (from XML if available)
        total_branches = 0
        covered_branches = 0
        branch_coverage = 0.0
        
        if xml_data is not None:
            # Find corresponding file in XML
            for package in xml_data.findall('.//package'):
                for class_elem in package.findall('.//class'):
                    filename = class_elem.get('filename', '')
                    if filename and filename.replace('\\', '/') in file_path:
                        total_branches = int(class_elem.get('branch-rate', 0)) * 100  # Approximate
                        covered_branches = int(float(class_elem.get('branch-rate', 0)) * total_branches)
                        branch_coverage = float(class_elem.get('branch-rate', 0)) * 100
                        break
        
        # Calculate derived metrics
        complexity = self.calculate_complexity_score(file_path)
        business_value = self.calculate_business_value_score(file_path)
        
        # Test priority score combines multiple factors
        priority_score = (
            (100 - line_coverage) * 0.4 +  # Higher priority for lower coverage
            (100 - branch_coverage) * 0.3 +  # Branch coverage gap
            complexity * 0.2 +              # Code complexity
            business_value * 0.1            # Business value
        )
        
        return CoverageMetrics(
            file_path=file_path.replace('\\', '/'),
            line_coverage=line_coverage,
            branch_coverage=branch_coverage,
            total_lines=total_lines,
            covered_lines=covered_lines,
            missing_lines=missing_lines,
            total_branches=total_branches,
            covered_branches=covered_branches,
            missing_branches=total_branches - covered_branches,
            complexity_score=complexity,
            business_value_score=business_value,
            test_priority_score=priority_score
        )
    
    def generate_test_recommendations(self, metrics: List[CoverageMetrics]) -> List[TestRecommendation]:
        """Generate actionable test creation recommendations."""
        recommendations = []
        
        # Sort by priority score
        high_priority_files = sorted(
            [m for m in metrics if m.test_priority_score > 30],
            key=lambda x: x.test_priority_score,
            reverse=True
        )[:15]  # Top 15 priority files
        
        for metric in high_priority_files:
            # Determine test type based on file location and business value
            if 'agents/' in metric.file_path:
                test_type = 'unit'  # Agent core logic needs unit tests
                if metric.business_value_score >= 8:
                    test_type = 'integration'  # High-value agents need integration
            elif 'routes/' in metric.file_path:
                test_type = 'integration'  # API routes need integration tests
            elif 'websocket' in metric.file_path.lower():
                test_type = 'integration'  # WebSocket needs real connections
            elif 'services/' in metric.file_path:
                test_type = 'unit'  # Business services need unit tests
            else:
                test_type = 'unit'  # Default to unit tests
            
            # Generate specific missing coverage areas
            missing_areas = []
            if metric.line_coverage < 70:
                missing_areas.append("Core business logic paths")
            if metric.branch_coverage < 60:
                missing_areas.append("Conditional branches and error handling")
            if metric.complexity_score > 7:
                missing_areas.append("Complex control flow scenarios")
            
            # Create test name suggestion
            file_name = Path(metric.file_path).stem
            suggested_name = f"test_{file_name}_comprehensive"
            if test_type == 'integration':
                suggested_name = f"test_{file_name}_integration"
            
            # Business justification
            justification = self._generate_business_justification(metric, test_type)
            
            reason = f"Line coverage: {metric.line_coverage:.1f}%, Branch coverage: {metric.branch_coverage:.1f}%, Complexity: {metric.complexity_score:.1f}"
            
            recommendation = TestRecommendation(
                file_path=metric.file_path,
                test_type=test_type,
                priority_score=metric.test_priority_score,
                reason=reason,
                missing_coverage_areas=missing_areas,
                suggested_test_name=suggested_name,
                business_justification=justification
            )
            
            recommendations.append(recommendation)
        
        return sorted(recommendations, key=lambda x: x.priority_score, reverse=True)
    
    def _generate_business_justification(self, metric: CoverageMetrics, test_type: str) -> str:
        """Generate business justification for test creation."""
        if metric.business_value_score >= 9:
            return f"CRITICAL: Core business logic affecting user experience. {test_type.title()} tests prevent revenue-impacting bugs."
        elif metric.business_value_score >= 7:
            return f"HIGH: Platform infrastructure component. {test_type.title()} tests ensure system stability and user trust."
        elif metric.business_value_score >= 5:
            return f"MEDIUM: Supporting business function. {test_type.title()} tests reduce technical debt and maintenance costs."
        else:
            return f"LOW: Utility component. {test_type.title()} tests improve code quality and developer confidence."
    
    def generate_line_vs_branch_explanation(self) -> str:
        """Generate explanation of line vs branch coverage."""
        return """
LINE COVERAGE vs BRANCH COVERAGE EXPLAINED:
==========================================

📊 LINE COVERAGE (Statement Coverage):
   - Measures: Which lines of code were executed during tests
   - Example: If function has 10 lines and tests execute 7 lines = 70% line coverage
   - Good for: Basic code execution validation
   - Limitation: Doesn't test decision logic thoroughly

🔀 BRANCH COVERAGE (Decision Coverage):  
   - Measures: Which decision branches (if/else, try/catch) were tested
   - Example: if condition_a or condition_b: needs tests for both True/False paths
   - Good for: Testing conditional logic and error handling paths  
   - Critical for: Business logic with complex decision trees

🎯 WHY BOTH MATTER FOR NETRA:
   - Line coverage ensures basic functionality works
   - Branch coverage ensures edge cases and error conditions are handled
   - For AI/LLM systems: Branch coverage critical for handling model failures
   - For multi-user systems: Branch coverage tests isolation boundaries
   - For WebSocket systems: Branch coverage tests connection/disconnection scenarios

💡 PRIORITY GUIDANCE:
   - Target 80%+ line coverage for core business logic
   - Target 70%+ branch coverage for conditional logic
   - Branch coverage gaps often indicate missing error handling tests
   - Focus branch testing on user-facing APIs and agent execution paths
        """
    
    def analyze_coverage(self) -> Optional[CoverageAnalysisReport]:
        """Perform comprehensive coverage analysis."""
        print("🔍 Analyzing test coverage intelligence...")
        
        # Load coverage data
        json_data = self.load_coverage_data()
        if not json_data:
            return None
        
        xml_data = self.load_xml_coverage_data()
        
        # Calculate overall metrics
        totals = json_data.get('totals', {})
        overall_line_coverage = totals.get('percent_covered', 0)
        
        # Overall branch coverage from XML
        overall_branch_coverage = 0.0
        if xml_data is not None:
            line_rate = float(xml_data.get('line-rate', 0)) * 100
            branch_rate = float(xml_data.get('branch-rate', 0)) * 100
            overall_branch_coverage = branch_rate
        
        coverage_gap = overall_line_coverage - overall_branch_coverage
        
        # Analyze individual files
        file_metrics = []
        files_below_threshold = 0
        
        for file_path, file_data in json_data.get('files', {}).items():
            # Skip test files and excluded paths
            if any(exclude in file_path for exclude in ['/tests/', '/test_', '__pycache__', '/migrations/', '/alembic/']):
                continue
            
            metrics = self.analyze_file_coverage(file_path, file_data, xml_data)
            file_metrics.append(metrics)
            
            if metrics.line_coverage < self.coverage_threshold:
                files_below_threshold += 1
        
        # Generate test recommendations
        test_recommendations = self.generate_test_recommendations(file_metrics)
        
        # Identify high priority files
        high_priority_files = sorted(
            [m for m in file_metrics if m.test_priority_score > 40],
            key=lambda x: x.test_priority_score,
            reverse=True
        )[:10]
        
        # Generate summary
        summary = f"""
📈 COVERAGE INTELLIGENCE SUMMARY:
• Overall Line Coverage: {overall_line_coverage:.1f}%
• Overall Branch Coverage: {overall_branch_coverage:.1f}%
• Coverage Gap: {abs(coverage_gap):.1f}% ({'line higher' if coverage_gap > 0 else 'branch higher'})
• Files Below Threshold ({self.coverage_threshold}%): {files_below_threshold}/{len(file_metrics)}
• High Priority Test Opportunities: {len(test_recommendations)}
        """
        
        return CoverageAnalysisReport(
            overall_line_coverage=overall_line_coverage,
            overall_branch_coverage=overall_branch_coverage,
            coverage_gap=coverage_gap,
            total_files_analyzed=len(file_metrics),
            files_below_threshold=files_below_threshold,
            high_priority_files=high_priority_files,
            test_recommendations=test_recommendations,
            line_vs_branch_explanation=self.generate_line_vs_branch_explanation(),
            summary=summary.strip()
        )
    
    def print_detailed_report(self, report: CoverageAnalysisReport):
        """Print detailed human-readable report."""
        print("=" * 80)
        print("🚀 NETRA APEX COVERAGE INTELLIGENCE REPORT")
        print("=" * 80)
        
        print(report.summary)
        print()
        
        # High Priority Files Section
        print("🎯 TOP PRIORITY FILES FOR TEST CREATION:")
        print("-" * 50)
        for i, metric in enumerate(report.high_priority_files, 1):
            print(f"{i:2}. {metric.file_path}")
            print(f"    📊 Line Coverage: {metric.line_coverage:5.1f}% | Branch Coverage: {metric.branch_coverage:5.1f}%")
            print(f"    🏢 Business Value: {metric.business_value_score:4.1f} | Complexity: {metric.complexity_score:4.1f}")
            print(f"    ⭐ Priority Score: {metric.test_priority_score:5.1f}")
            print()
        
        # Test Recommendations Section  
        print("💡 ACTIONABLE TEST RECOMMENDATIONS:")
        print("-" * 50)
        for i, rec in enumerate(report.test_recommendations[:10], 1):
            print(f"{i:2}. CREATE: {rec.suggested_test_name}")
            print(f"    📁 File: {rec.file_path}")
            print(f"    🧪 Type: {rec.test_type.upper()} test")
            print(f"    ⭐ Priority: {rec.priority_score:5.1f} | Reason: {rec.reason}")
            print(f"    🎯 Missing Areas: {', '.join(rec.missing_coverage_areas)}")
            print(f"    💼 Business Value: {rec.business_justification}")
            print()
        
        # Coverage Education Section
        print(report.line_vs_branch_explanation)
    
    def print_priority_only_report(self, report: CoverageAnalysisReport):
        """Print concise priority-focused report."""
        print("🎯 PRIORITY TEST CREATION OPPORTUNITIES")
        print("=" * 60)
        
        print(f"📊 Current Coverage: {report.overall_line_coverage:.1f}% line, {report.overall_branch_coverage:.1f}% branch")
        print(f"🎯 Files needing attention: {report.files_below_threshold}/{report.total_files_analyzed}")
        print()
        
        print("⚡ TOP 5 IMMEDIATE ACTIONS:")
        for i, rec in enumerate(report.test_recommendations[:5], 1):
            print(f"{i}. {rec.suggested_test_name} ({rec.test_type})")
            print(f"   Priority: {rec.priority_score:.1f} | File: {Path(rec.file_path).name}")
            print()
    
    def export_json_report(self, report: CoverageAnalysisReport, output_file: str):
        """Export machine-readable JSON report."""
        report_data = asdict(report)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 JSON report exported: {output_file}")

def run_coverage_with_tests() -> bool:
    """Run tests with coverage if coverage data is missing or stale."""
    reports_dir = PROJECT_ROOT / "reports" / "coverage"
    json_report = reports_dir / "coverage.json"
    
    # Check if coverage data exists and is recent
    if json_report.exists():
        import time
        age_hours = (time.time() - json_report.stat().st_mtime) / 3600
        if age_hours < 2:  # Less than 2 hours old
            return True
    
    print("🔄 Coverage data missing or stale. Running tests with coverage...")
    
    try:
        result = subprocess.run([
            sys.executable, "tests/unified_test_runner.py",
            "--category", "unit",
            "--fast-fail",
            "--no-real-services"  # Fast unit test run
        ], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=300)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Netra Apex Intelligent Coverage Analyzer - Claude Command for Test Intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
    python scripts/coverage_intelligence.py                    # Full detailed report
    python scripts/coverage_intelligence.py --priority-only    # Quick priority view  
    python scripts/coverage_intelligence.py --format json      # Machine readable
    python scripts/coverage_intelligence.py --threshold 85     # Custom threshold
    python scripts/coverage_intelligence.py --refresh-coverage # Force test run first
        """
    )
    
    parser.add_argument(
        "--priority-only",
        action="store_true",
        help="Show only high-priority test recommendations"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "--threshold",
        type=float,
        default=80.0,
        help="Coverage threshold percentage (default: 80.0)"
    )
    
    parser.add_argument(
        "--output",
        help="Output file for JSON format"
    )
    
    parser.add_argument(
        "--refresh-coverage",
        action="store_true",
        help="Run tests with coverage before analysis"
    )
    
    args = parser.parse_args()
    
    # Refresh coverage if requested
    if args.refresh_coverage:
        if not run_coverage_with_tests():
            print("❌ Failed to refresh coverage data")
            sys.exit(1)
    
    # Create analyzer and run analysis
    analyzer = CoverageIntelligenceAnalyzer(coverage_threshold=args.threshold)
    report = analyzer.analyze_coverage()
    
    if not report:
        print("❌ Coverage analysis failed. Run tests with coverage first.")
        sys.exit(1)
    
    # Output report based on format
    if args.format == "json":
        output_file = args.output or "coverage_intelligence_report.json"
        analyzer.export_json_report(report, output_file)
    elif args.priority_only:
        analyzer.print_priority_only_report(report)
    else:
        analyzer.print_detailed_report(report)

if __name__ == "__main__":
    main()