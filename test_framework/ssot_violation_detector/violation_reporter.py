"""
SSOT Violation Reporter

Generates comprehensive reports on SSOT violations detected in the codebase.
Provides detailed analysis, remediation guidance, and tracking capabilities.

Business Value:
- Provides clear visibility into SSOT compliance status
- Enables prioritized remediation based on severity
- Tracks progress of SSOT compliance improvements
- Supports audit and governance requirements
"""

import json
import time
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .violation_detector import ComparisonReport, ViolationResult
from .message_pattern_analyzer import AnalysisResult, PatternMatch
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ViolationReporter:
    """
    Generates comprehensive reports on SSOT violations.
    
    Supports multiple output formats and provides detailed analysis
    of violations with remediation guidance.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("reports/ssot_violations")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_comprehensive_report(
        self,
        detection_reports: List[ComparisonReport],
        analysis_result: AnalysisResult,
        report_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate comprehensive SSOT violation report.
        
        Args:
            detection_reports: Results from violation detection
            analysis_result: Results from pattern analysis
            report_name: Custom name for the report
            
        Returns:
            Dictionary with paths to generated report files
        """
        logger.info("Generating comprehensive SSOT violation report")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = report_name or f"ssot_violation_report_{timestamp}"
        
        generated_files = {}
        
        # Generate executive summary
        summary_path = self.output_dir / f"{base_name}_executive_summary.md"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_executive_summary(detection_reports, analysis_result))
        generated_files["executive_summary"] = str(summary_path)
        
        # Generate detailed violation analysis
        detailed_path = self.output_dir / f"{base_name}_detailed_analysis.md"
        with open(detailed_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_detailed_analysis(detection_reports, analysis_result))
        generated_files["detailed_analysis"] = str(detailed_path)
        
        # Generate remediation guide
        remediation_path = self.output_dir / f"{base_name}_remediation_guide.md"
        with open(remediation_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_remediation_guide(detection_reports, analysis_result))
        generated_files["remediation_guide"] = str(remediation_path)
        
        # Generate JSON data export
        json_path = self.output_dir / f"{base_name}_data.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self._generate_json_export(detection_reports, analysis_result), f, indent=2)
        generated_files["json_data"] = str(json_path)
        
        logger.info(f"Report generation complete - {len(generated_files)} files created")
        return generated_files
        
    def _generate_executive_summary(
        self,
        detection_reports: List[ComparisonReport],
        analysis_result: AnalysisResult
    ) -> str:
        """Generate executive summary report."""
        
        # Calculate aggregate statistics
        total_critical_violations = sum(
            report.violation_count_by_severity.get("critical", 0)
            for report in detection_reports
        ) + analysis_result.violations_by_severity.get("critical", 0)
        
        total_high_violations = sum(
            report.violation_count_by_severity.get("high", 0)
            for report in detection_reports
        ) + analysis_result.violations_by_severity.get("high", 0)
        
        critical_reports = [r for r in detection_reports if r.has_critical_violations]
        
        compliance_score = analysis_result.summary.get("ssot_compliance_score", 0)
        
        return f"""# SSOT Violation Report - Executive Summary
Generated: {datetime.now(timezone.utc).isoformat()}

##  ALERT:  Critical Findings

### Violation Overview
- **Critical Violations:** {total_critical_violations}
- **High Severity Violations:** {total_high_violations}
- **Files Affected:** {len(analysis_result.files_with_violations)}
- **SSOT Compliance Score:** {compliance_score}%

### Business Impact
- **Risk Level:** {'[U+1F534] HIGH' if total_critical_violations > 0 else '[U+1F7E1] MEDIUM' if total_high_violations > 0 else '[U+1F7E2] LOW'}
- **Data Integrity Risk:** {'Critical' if total_critical_violations > 5 else 'Moderate' if total_critical_violations > 0 else 'Low'}
- **Platform Stability Impact:** {'High' if len(critical_reports) > 3 else 'Medium' if len(critical_reports) > 0 else 'Low'}

##  CHART:  Key Statistics

### Violation Distribution
| Severity | Count | Percentage |
|----------|-------|------------|
| Critical | {total_critical_violations} | {(total_critical_violations / max(1, analysis_result.total_matches + len(detection_reports)) * 100):.1f}% |
| High | {total_high_violations} | {(total_high_violations / max(1, analysis_result.total_matches + len(detection_reports)) * 100):.1f}% |
| Medium | {analysis_result.violations_by_severity.get('medium', 0)} | {(analysis_result.violations_by_severity.get('medium', 0) / max(1, analysis_result.total_matches) * 100):.1f}% |
| Low | {analysis_result.violations_by_severity.get('low', 0)} | {(analysis_result.violations_by_severity.get('low', 0) / max(1, analysis_result.total_matches) * 100):.1f}% |

### Most Common Violations
{self._format_top_violations(analysis_result)}

##  TARGET:  Primary Target for Remediation

**File:** `test_framework/ssot/database.py`  
**Line:** 596  
**Issue:** Direct `session.add()` bypassing MessageRepository SSOT pattern  
**Impact:** Critical - affects all test framework message creation  
**Priority:** [U+1F534] IMMEDIATE  

## [U+1F4CB] Immediate Action Items

1. **Fix Critical Violation** - Update `test_framework/ssot/database.py:596`
2. **Validate Tests** - Ensure all existing tests pass after remediation
3. **Update Documentation** - Reflect SSOT compliance requirements
4. **Implement Monitoring** - Add automated SSOT violation detection

## [U+1F4C8] Success Metrics

- **Target Compliance Score:** 95%+
- **Critical Violations:** 0
- **High Violations:** < 3
- **Test Coverage:** All message creation paths tested

## [U+1F517] Related Documents

- [Detailed Analysis Report](detailed_analysis.md)
- [Remediation Guide](remediation_guide.md)
- [Raw Data Export](data.json)
"""

    def _generate_detailed_analysis(
        self,
        detection_reports: List[ComparisonReport],
        analysis_result: AnalysisResult
    ) -> str:
        """Generate detailed violation analysis."""
        
        report_lines = [
            "# SSOT Violation Report - Detailed Analysis",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Detection Reports Analysis",
            ""
        ]
        
        # Analyze detection reports
        for i, report in enumerate(detection_reports, 1):
            report_lines.extend([
                f"### Detection Report #{i}",
                f"- **SSOT Message ID:** `{report.ssot_message_id}`",
                f"- **Violation Message ID:** `{report.violation_message_id}`",
                f"- **Violations Found:** {len(report.violations)}",
                f"- **Critical Violations:** {'[U+1F534] YES' if report.has_critical_violations else '[U+1F7E2] NO'}",
                ""
            ])
            
            if report.violations:
                report_lines.extend([
                    "#### Specific Violations:",
                    ""
                ])
                
                for violation in report.violations:
                    severity_icon = {
                        "critical": "[U+1F534]",
                        "high": "[U+1F7E0]", 
                        "medium": "[U+1F7E1]",
                        "low": "[U+1F7E2]"
                    }.get(violation.severity, "[U+26AA]")
                    
                    report_lines.extend([
                        f"**{severity_icon} {violation.violation_type.value.upper()}**",
                        f"- **Severity:** {violation.severity}",
                        f"- **Description:** {violation.description}",
                        f"- **Expected:** `{violation.expected_value}`",
                        f"- **Actual:** `{violation.actual_value}`",
                        ""
                    ])
                    
        # Analyze pattern analysis results
        report_lines.extend([
            "## Codebase Pattern Analysis",
            "",
            f"- **Files Scanned:** {analysis_result.total_files_scanned}",
            f"- **Pattern Matches:** {analysis_result.total_matches}",
            f"- **Files with Violations:** {len(analysis_result.files_with_violations)}",
            ""
        ])
        
        # Top violation files
        if analysis_result.summary.get("files_with_highest_violations"):
            report_lines.extend([
                "### Files with Most Violations",
                ""
            ])
            
            for file_info in analysis_result.summary["files_with_highest_violations"]:
                report_lines.append(f"- **`{file_info['file']}`** - {file_info['violation_count']} violations")
                
            report_lines.append("")
            
        # Detailed pattern matches
        if analysis_result.pattern_matches:
            report_lines.extend([
                "### Detailed Pattern Violations",
                ""
            ])
            
            # Group by file for better organization
            files_dict = {}
            for match in analysis_result.pattern_matches:
                if match.file_path not in files_dict:
                    files_dict[match.file_path] = []
                files_dict[match.file_path].append(match)
                
            for file_path, matches in files_dict.items():
                report_lines.extend([
                    f"#### {file_path}",
                    ""
                ])
                
                for match in matches:
                    severity_icon = {
                        "critical": "[U+1F534]",
                        "high": "[U+1F7E0]",
                        "medium": "[U+1F7E1]", 
                        "low": "[U+1F7E2]"
                    }.get(match.severity, "[U+26AA]")
                    
                    report_lines.extend([
                        f"**Line {match.line_number}** {severity_icon} {match.severity.upper()}",
                        f"- **Pattern:** {match.pattern_type}",
                        f"- **Description:** {match.description}",
                        "",
                        "```python",
                        match.line_content,
                        "```",
                        ""
                    ])
                    
        return "\n".join(report_lines)
        
    def _generate_remediation_guide(
        self,
        detection_reports: List[ComparisonReport],
        analysis_result: AnalysisResult
    ) -> str:
        """Generate comprehensive remediation guide."""
        
        return f"""# SSOT Violation Remediation Guide
Generated: {datetime.now(timezone.utc).isoformat()}

## [U+1F680] Quick Start Remediation

### Priority 1: Critical Violation Fix

**Target:** `test_framework/ssot/database.py:596`

**Current Code:**
```python
session.add(message_data)
```

**Required Fix:**
```python
# Replace direct session.add() with SSOT repository pattern
message = await self.message_repository.create_message(
    db=session,
    thread_id=thread_id,
    role=kwargs.get("role", "user"),
    content=kwargs.get("content", "Test message"),
    metadata=kwargs.get("metadata", {{}})
)
```

**Required Import:**
```python
from netra_backend.app.services.database.message_repository import MessageRepository
```

### Step-by-Step Implementation

1. **Update Class Constructor**
   ```python
   def __init__(self):
       self.message_repository = MessageRepository()
   ```

2. **Replace Direct Database Operations**
   - Find all `session.add(message_data)` calls
   - Replace with `await self.message_repository.create_message()`
   - Ensure proper async/await handling

3. **Update Method Signatures**
   - Add `async` keyword to methods if needed
   - Ensure proper database session handling

4. **Test Validation**
   - Run affected tests to ensure functionality preserved
   - Verify message structure consistency

## [U+1F4CB] Complete Remediation Checklist

### Phase 1: Critical Fixes
- [ ] Fix `test_framework/ssot/database.py:596`
- [ ] Add MessageRepository import
- [ ] Update method to async if needed
- [ ] Validate message creation works

### Phase 2: Additional Violations
{self._generate_violation_checklist(analysis_result)}

### Phase 3: Testing & Validation
- [ ] Run full test suite
- [ ] Verify SSOT compliance with detection tools
- [ ] Update any failing tests
- [ ] Validate performance impact

### Phase 4: Documentation & Monitoring
- [ ] Update SSOT documentation
- [ ] Add automated violation detection
- [ ] Create monitoring dashboard
- [ ] Train team on SSOT patterns

## [U+1F527] Technical Implementation Details

### SSOT MessageRepository Pattern

The canonical way to create messages:

```python
from netra_backend.app.services.database.message_repository import MessageRepository

# Initialize repository
message_repository = MessageRepository()

# Create message (proper SSOT pattern)
message = await message_repository.create_message(
    db=session,
    thread_id="thread_12345",
    role="user",
    content="Message content",
    assistant_id=None,  # Optional
    run_id=None,        # Optional  
    metadata={{          # Optional
        "source": "api",
        "priority": "normal"
    }}
)
```

### Required Message Structure

SSOT-compliant messages have this structure:
- `object`: Always "thread.message"
- `content`: List of content objects with type/text structure
- `metadata_`: Dictionary for additional data
- `file_ids`: List (empty if no files)
- `created_at`: Integer timestamp
- `id`: Format "msg_<uuid>"

### Anti-Patterns to Avoid

 FAIL:  **Direct model instantiation:**
```python
message = Message(thread_id=thread_id, content=content)  # DON'T
```

 FAIL:  **Direct session operations:**
```python
session.add(message_data)  # DON'T
```

 FAIL:  **Raw SQL:**
```python
session.execute("INSERT INTO message...")  # DON'T
```

 PASS:  **Correct SSOT pattern:**
```python
message = await message_repository.create_message(...)  # DO
```

## [U+1F9EA] Testing Your Remediation

### Before Remediation
Run the violation detection tests:
```bash
python tests/mission_critical/test_ssot_message_repository_compliance_suite.py
```
**Expected:** Tests should FAIL, exposing violations

### After Remediation  
Run the same tests:
```bash
python tests/mission_critical/test_ssot_message_repository_compliance_suite.py
```
**Expected:** Tests should PASS, confirming compliance

### Full Validation
```bash
# Run complete test suite
python tests/unified_test_runner.py --real-services

# Run integration tests
python tests/integration/test_ssot_database_pattern_violations.py

# Run E2E tests
python tests/e2e/test_ssot_message_flow_end_to_end.py
```

##  TARGET:  Success Criteria

-  PASS:  All violation detection tests pass
-  PASS:  No critical or high severity violations remain
-  PASS:  SSOT compliance score > 95%
-  PASS:  All existing functionality preserved
-  PASS:  Performance impact < 5%

##  SEARCH:  Monitoring & Prevention

### Automated Detection
Add to CI/CD pipeline:
```bash
python -m test_framework.ssot_violation_detector.cli --check-compliance
```

### Code Review Checklist
- [ ] All message creation uses MessageRepository
- [ ] No direct database operations on message table
- [ ] Proper async/await patterns
- [ ] SSOT import statements present

## [U+1F198] Troubleshooting

### Common Issues

**Issue:** Tests fail after remediation
**Solution:** Ensure async methods are properly awaited

**Issue:** Import errors
**Solution:** Verify absolute imports from correct modules

**Issue:** Performance degradation  
**Solution:** Check for unnecessary database round-trips

**Issue:** Message structure differences
**Solution:** Validate content format matches SSOT pattern

## [U+1F4DE] Support

For remediation support:
- Review SSOT documentation in `netra_backend/app/services/database/`
- Check existing SSOT implementations for patterns
- Run violation detection tools for guidance
- Refer to test examples in mission_critical tests
"""

    def _format_top_violations(self, analysis_result: AnalysisResult) -> str:
        """Format top violations for executive summary."""
        if not analysis_result.violations_by_type:
            return "No violations detected."
            
        lines = []
        for violation_type, count in sorted(
            analysis_result.violations_by_type.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]:
            lines.append(f"- **{violation_type}**: {count} occurrences")
            
        return "\n".join(lines)
        
    def _generate_violation_checklist(self, analysis_result: AnalysisResult) -> str:
        """Generate checklist for violations."""
        lines = []
        
        for match in analysis_result.pattern_matches:
            if match.severity in ["critical", "high"]:
                lines.append(f"- [ ] Fix {match.pattern_type} in `{match.file_path}:{match.line_number}`")
                
        return "\n".join(lines) if lines else "- [ ] No additional high-priority violations found"
        
    def _generate_json_export(
        self,
        detection_reports: List[ComparisonReport],
        analysis_result: AnalysisResult
    ) -> Dict[str, Any]:
        """Generate JSON export of all violation data."""
        
        return {
            "report_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "detection_reports_count": len(detection_reports),
                "analysis_files_scanned": analysis_result.total_files_scanned,
                "total_violations": analysis_result.total_matches + len(detection_reports)
            },
            "detection_reports": [
                {
                    "ssot_message_id": report.ssot_message_id,
                    "violation_message_id": report.violation_message_id,
                    "violations": [asdict(v) for v in report.violations],
                    "summary": report.summary,
                    "timestamp": report.timestamp
                }
                for report in detection_reports
            ],
            "pattern_analysis": {
                "total_files_scanned": analysis_result.total_files_scanned,
                "total_matches": analysis_result.total_matches,
                "violations_by_severity": analysis_result.violations_by_severity,
                "violations_by_type": analysis_result.violations_by_type,
                "files_with_violations": analysis_result.files_with_violations,
                "pattern_matches": [asdict(match) for match in analysis_result.pattern_matches],
                "summary": analysis_result.summary
            }
        }