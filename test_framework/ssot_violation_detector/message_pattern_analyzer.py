"""
Message Pattern Analyzer

Analyzes message creation patterns across the codebase to identify
deviations from SSOT repository patterns.

Business Value:
- Identifies all locations bypassing SSOT message repository
- Provides statistical analysis of message creation patterns
- Enables systematic remediation of SSOT violations
- Maintains consistency across the entire platform
"""

import ast
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class PatternMatch:
    """Represents a pattern match in the codebase."""
    file_path: str
    line_number: int
    line_content: str
    pattern_type: str
    severity: str
    description: str
    context_lines: List[str]


@dataclass
class AnalysisResult:
    """Results of message pattern analysis."""
    total_files_scanned: int
    total_matches: int
    violations_by_severity: Dict[str, int]
    violations_by_type: Dict[str, int]
    files_with_violations: List[str]
    pattern_matches: List[PatternMatch]
    summary: Dict[str, Any]


class MessagePatternAnalyzer:
    """
    Analyzes message creation patterns across the codebase.
    
    Identifies locations where code bypasses SSOT message repository
    and creates messages directly through other means.
    """
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        
        # Patterns that indicate SSOT violations
        self.violation_patterns = {
            # Direct database operations on message table
            "direct_session_add": {
                "pattern": r"session\.add\s*\(\s*[^)]*[Mm]essage",
                "severity": "critical",
                "description": "Direct session.add() with Message model bypasses SSOT repository"
            },
            
            # Direct database inserts
            "direct_insert": {
                "pattern": r"INSERT\s+INTO\s+message",
                "severity": "critical", 
                "description": "Direct SQL INSERT into message table bypasses SSOT repository"
            },
            
            # Direct model instantiation
            "direct_model_create": {
                "pattern": r"Message\s*\(\s*[^)]*\)",
                "severity": "high",
                "description": "Direct Message model instantiation may bypass SSOT repository"
            },
            
            # Bulk operations bypassing repository
            "bulk_operations": {
                "pattern": r"bulk_insert_mappings.*[Mm]essage|bulk_save_objects.*[Mm]essage",
                "severity": "high",
                "description": "Bulk operations on Message model bypass SSOT repository"
            },
            
            # Raw SQL execution
            "raw_sql": {
                "pattern": r"execute\s*\(\s*['\"].*INSERT.*message.*['\"]",
                "severity": "critical",
                "description": "Raw SQL execution on message table bypasses SSOT repository"
            }
        }
        
        # Files to exclude from analysis
        self.excluded_patterns = {
            "migrations", "__pycache__", ".git", "node_modules",
            "*.pyc", "*.pyo", "*.log", "*.tmp"
        }
        
        # SSOT compliant patterns (should be present)
        self.ssot_patterns = {
            "message_repository_import": {
                "pattern": r"from.*message_repository.*import.*MessageRepository",
                "description": "Proper SSOT MessageRepository import"
            },
            
            "message_repository_usage": {
                "pattern": r"MessageRepository\(\)\.create_message|message_repository\.create_message",
                "description": "Proper SSOT MessageRepository usage"
            }
        }
        
    def analyze_codebase(self, target_dirs: Optional[List[str]] = None) -> AnalysisResult:
        """
        Analyze the entire codebase for message creation pattern violations.
        
        Args:
            target_dirs: Specific directories to analyze. If None, analyzes entire project.
            
        Returns:
            AnalysisResult with detected violations
        """
        logger.info("Starting codebase analysis for message pattern violations")
        
        if target_dirs:
            scan_paths = [self.project_root / dir_name for dir_name in target_dirs]
        else:
            scan_paths = [self.project_root]
            
        all_matches = []
        files_scanned = 0
        files_with_violations = set()
        
        for scan_path in scan_paths:
            if not scan_path.exists():
                logger.warning(f"Scan path does not exist: {scan_path}")
                continue
                
            for file_path in self._get_python_files(scan_path):
                files_scanned += 1
                matches = self._analyze_file(file_path)
                
                if matches:
                    all_matches.extend(matches)
                    files_with_violations.add(str(file_path))
                    
        # Generate analysis summary
        violations_by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        violations_by_type = {}
        
        for match in all_matches:
            violations_by_severity[match.severity] += 1
            violations_by_type[match.pattern_type] = violations_by_type.get(match.pattern_type, 0) + 1
            
        summary = {
            "scan_paths": [str(p) for p in scan_paths],
            "most_common_violation": max(violations_by_type.items(), key=lambda x: x[1])[0] if violations_by_type else None,
            "files_with_highest_violations": self._get_top_violation_files(all_matches),
            "ssot_compliance_score": self._calculate_compliance_score(all_matches, files_scanned)
        }
        
        result = AnalysisResult(
            total_files_scanned=files_scanned,
            total_matches=len(all_matches),
            violations_by_severity=violations_by_severity,
            violations_by_type=violations_by_type,
            files_with_violations=list(files_with_violations),
            pattern_matches=all_matches,
            summary=summary
        )
        
        logger.info(f"Codebase analysis complete - {len(all_matches)} violations found in {files_scanned} files")
        return result
        
    def _get_python_files(self, directory: Path) -> List[Path]:
        """Get all Python files in directory, excluding patterns."""
        python_files = []
        
        for root, dirs, files in os.walk(directory):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self.excluded_patterns)]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    
                    # Skip if matches excluded patterns
                    if not any(pattern in str(file_path) for pattern in self.excluded_patterns):
                        python_files.append(file_path)
                        
        return python_files
        
    def _analyze_file(self, file_path: Path) -> List[PatternMatch]:
        """Analyze a single file for pattern violations."""
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                line_content = line.strip()
                
                # Check each violation pattern
                for pattern_name, pattern_info in self.violation_patterns.items():
                    if re.search(pattern_info["pattern"], line_content, re.IGNORECASE):
                        # Get context lines
                        context_start = max(0, line_num - 3)
                        context_end = min(len(lines), line_num + 2)
                        context_lines = [lines[i].strip() for i in range(context_start, context_end)]
                        
                        matches.append(PatternMatch(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            line_content=line_content,
                            pattern_type=pattern_name,
                            severity=pattern_info["severity"],
                            description=pattern_info["description"],
                            context_lines=context_lines
                        ))
                        
        except Exception as e:
            logger.warning(f"Error analyzing file {file_path}: {e}")
            
        return matches
        
    def _get_top_violation_files(self, matches: List[PatternMatch], limit: int = 5) -> List[Dict[str, Any]]:
        """Get files with the most violations."""
        file_counts = {}
        
        for match in matches:
            file_counts[match.file_path] = file_counts.get(match.file_path, 0) + 1
            
        # Sort by violation count and return top files
        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"file": file_path, "violation_count": count}
            for file_path, count in sorted_files[:limit]
        ]
        
    def _calculate_compliance_score(self, matches: List[PatternMatch], total_files: int) -> float:
        """Calculate SSOT compliance score (0-100)."""
        if total_files == 0:
            return 100.0
            
        # Weight violations by severity
        severity_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        
        total_violation_weight = sum(
            severity_weights.get(match.severity, 1) for match in matches
        )
        
        # Calculate score (higher violations = lower score)
        max_possible_weight = total_files * 10  # Assume worst case
        compliance_score = max(0, 100 - (total_violation_weight / max_possible_weight * 100))
        
        return round(compliance_score, 2)
        
    def analyze_specific_violation(self, file_path: str, line_number: int) -> Dict[str, Any]:
        """
        Analyze a specific violation in detail.
        
        Args:
            file_path: Path to file containing violation
            line_number: Line number of violation
            
        Returns:
            Detailed analysis of the specific violation
        """
        logger.info(f"Analyzing specific violation at {file_path}:{line_number}")
        
        full_path = self.project_root / file_path
        
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if line_number > len(lines) or line_number < 1:
                return {"error": f"Invalid line number: {line_number}"}
                
            target_line = lines[line_number - 1].strip()
            
            # Extended context
            context_start = max(0, line_number - 10)
            context_end = min(len(lines), line_number + 10)
            extended_context = [
                {"line_num": i + 1, "content": lines[i].rstrip()}
                for i in range(context_start, context_end)
            ]
            
            # Check what patterns match
            matching_patterns = []
            for pattern_name, pattern_info in self.violation_patterns.items():
                if re.search(pattern_info["pattern"], target_line, re.IGNORECASE):
                    matching_patterns.append({
                        "pattern_name": pattern_name,
                        "severity": pattern_info["severity"],
                        "description": pattern_info["description"]
                    })
                    
            # Suggest remediation
            remediation_suggestions = self._generate_remediation_suggestions(target_line, matching_patterns)
            
            return {
                "file_path": file_path,
                "line_number": line_number,
                "line_content": target_line,
                "matching_patterns": matching_patterns,
                "extended_context": extended_context,
                "remediation_suggestions": remediation_suggestions,
                "analysis_timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing specific violation: {e}")
            return {"error": str(e)}
            
    def _generate_remediation_suggestions(
        self, 
        line_content: str, 
        matching_patterns: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate remediation suggestions for violations."""
        suggestions = []
        
        for pattern in matching_patterns:
            pattern_name = pattern["pattern_name"]
            
            if pattern_name == "direct_session_add":
                suggestions.append(
                    "Replace direct session.add() with MessageRepository.create_message() method"
                )
                suggestions.append(
                    "Import: from netra_backend.app.services.database.message_repository import MessageRepository"
                )
                suggestions.append(
                    "Usage: await message_repository.create_message(db=session, thread_id=..., role=..., content=...)"
                )
                
            elif pattern_name == "direct_model_create":
                suggestions.append(
                    "Replace direct Message() instantiation with MessageRepository.create_message()"
                )
                suggestions.append(
                    "This ensures proper business logic, validation, and SSOT compliance"
                )
                
            elif pattern_name == "direct_insert":
                suggestions.append(
                    "Replace raw SQL INSERT with MessageRepository.create_message() method"
                )
                suggestions.append(
                    "Raw SQL bypasses ORM validation and business logic"
                )
                
            elif pattern_name == "bulk_operations":
                suggestions.append(
                    "Consider using MessageRepository in a loop with batch commits"
                )
                suggestions.append(
                    "If bulk operations are required for performance, ensure SSOT compliance"
                )
                
        # General suggestions
        if suggestions:
            suggestions.append("Refer to SSOT documentation in netra_backend/app/services/database/")
            suggestions.append("Run tests after remediation to ensure functionality is preserved")
            
        return suggestions
        
    def generate_violation_report(self, analysis_result: AnalysisResult) -> str:
        """Generate a formatted violation report."""
        report_lines = [
            "# SSOT Message Pattern Violation Report",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Summary",
            f"- **Total files scanned:** {analysis_result.total_files_scanned}",
            f"- **Total violations found:** {analysis_result.total_matches}",
            f"- **Files with violations:** {len(analysis_result.files_with_violations)}",
            f"- **SSOT compliance score:** {analysis_result.summary.get('ssot_compliance_score', 'N/A')}%",
            ""
        ]
        
        # Violations by severity
        report_lines.extend([
            "## Violations by Severity",
            ""
        ])
        
        for severity, count in analysis_result.violations_by_severity.items():
            if count > 0:
                report_lines.append(f"- **{severity.upper()}:** {count}")
                
        report_lines.append("")
        
        # Top violation files
        if analysis_result.summary.get("files_with_highest_violations"):
            report_lines.extend([
                "## Files with Most Violations",
                ""
            ])
            
            for file_info in analysis_result.summary["files_with_highest_violations"]:
                report_lines.append(f"- `{file_info['file']}`: {file_info['violation_count']} violations")
                
            report_lines.append("")
            
        # Detailed violations
        report_lines.extend([
            "## Detailed Violations",
            ""
        ])
        
        for match in analysis_result.pattern_matches:
            report_lines.extend([
                f"### {match.file_path}:{match.line_number}",
                f"**Severity:** {match.severity.upper()}",
                f"**Type:** {match.pattern_type}",
                f"**Description:** {match.description}",
                "",
                "```python",
                match.line_content,
                "```",
                ""
            ])
            
        return "\n".join(report_lines)