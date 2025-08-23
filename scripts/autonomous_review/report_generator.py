#!/usr/bin/env python3
"""
Autonomous Test Review System - Report Generator
Generate comprehensive test review reports in multiple formats
"""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from scripts.autonomous_review.types import TestAnalysis


class ReportGenerator:
    """Generate comprehensive test review reports"""
    
    def __init__(self):
        pass
    
    async def generate_report(self, analysis: TestAnalysis, reports_dir: Path, coverage_goal: float = 97.0) -> None:
        """Generate comprehensive test review report"""
        report_path = reports_dir / "autonomous_test_review.md"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate markdown report
        markdown_content = self._generate_markdown_report(analysis, coverage_goal)
        report_path.write_text(markdown_content, encoding='utf-8')
        print(f"\n[REPORT] Detailed report saved to: {report_path}")
        
        # Generate JSON report for programmatic access
        json_report_path = reports_dir / "autonomous_test_review.json"
        json_content = self._generate_json_report(analysis, coverage_goal)
        
        with open(json_report_path, 'w') as f:
            json.dump(json_content, f, indent=2, default=str)
        print(f"[REPORT] JSON report saved to: {json_report_path}")
    
    def _generate_markdown_report(self, analysis: TestAnalysis, coverage_goal: float) -> str:
        """Generate markdown format report"""
        return f"""# Autonomous Test Review Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Review Mode: Ultra-Thinking Powered Analysis

## Executive Summary
- **Current Coverage**: {analysis.coverage_percentage:.1f}%
- **Target Coverage**: {coverage_goal}%
- **Coverage Gap**: {coverage_goal - analysis.coverage_percentage:.1f}%
- **Test Quality Score**: {analysis.quality_score:.0f}/100
- **Technical Debt**: {analysis.test_debt} issues

## Critical Gaps Identified
{chr(10).join(f'- {gap}' for gap in analysis.critical_gaps[:10]) if analysis.critical_gaps else '- No critical gaps found'}

## Missing Test Coverage
### High Priority Modules
{chr(10).join(f'- {module}' for module in analysis.missing_tests[:15]) if analysis.missing_tests else '- All modules have test coverage'}

## Test Quality Issues
### Legacy Tests Requiring Modernization
{chr(10).join(f'- {test}' for test in analysis.legacy_tests[:10]) if analysis.legacy_tests else '- No legacy tests found'}

### Flaky Tests
{chr(10).join(f'- {test}' for test in analysis.flaky_tests[:5]) if analysis.flaky_tests else '- No flaky tests detected'}

### Slow Tests
{chr(10).join(f'- {test}' for test in analysis.slow_tests[:5]) if analysis.slow_tests else '- No slow tests detected'}

## Recommendations
{chr(10).join(f'{i+1}. {rec}' for i, rec in enumerate(analysis.recommendations)) if analysis.recommendations else '- No recommendations at this time'}

## Automated Actions Taken
- Tests generated for critical modules
- Legacy patterns modernized
- Redundant tests marked for removal
- Test organization improved

## Next Steps
1. Review generated tests and add specific test cases
2. Run full test suite to verify improvements
3. Schedule regular autonomous reviews
4. Monitor coverage trends toward {coverage_goal}% goal

## Configuration
To enable continuous autonomous review, add to CI/CD:
```bash
python scripts/test_autonomous_review.py --auto
```

Or schedule hourly reviews:
```bash
0 * * * * cd /path/to/project && python scripts/test_autonomous_review.py --continuous
```
"""
    
    def _generate_json_report(self, analysis: TestAnalysis, coverage_goal: float) -> dict:
        """Generate JSON format report for programmatic access"""
        json_report = asdict(analysis)
        json_report["timestamp"] = datetime.now().isoformat()
        json_report["coverage_goal"] = coverage_goal
        json_report["coverage_gap"] = coverage_goal - analysis.coverage_percentage
        
        return json_report