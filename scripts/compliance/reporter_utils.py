#!/usr/bin/env python3
"""
Utilities for compliance reporting.
Handles violation sorting, limits, and severity markers.
"""

from typing import List

from scripts.compliance.core import Violation


class ReporterUtils:
    """Utility functions for compliance reporting"""
    
    def __init__(self, default_limit: int = 10, smart_limits: bool = True,
                 use_emoji: bool = True):
        self.default_limit = default_limit
        self.smart_limits = smart_limits
        self.use_emoji = use_emoji
    
    def sort_violations_by_severity(self, violations: List[Violation]) -> List[Violation]:
        """Sort violations by severity and impact - 4-tier system"""
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        return sorted(violations, key=lambda v: (
            severity_order.get(v.severity, 4),
            -(v.actual_value or 0),
            v.file_path
        ))
    
    def get_smart_limit(self, total_count: int, base_limit: int = None) -> int:
        """Get smart display limit based on violation count"""
        if not self.smart_limits:
            return base_limit or self.default_limit
        if total_count <= 5:
            return total_count
        elif total_count <= 10:
            return min(total_count, base_limit or self.default_limit)
        elif total_count <= 20:
            return min(10, base_limit or self.default_limit)
        else:
            return min(base_limit or self.default_limit, max(5, total_count // 10))
    
    def get_severity_marker(self, severity: str) -> str:
        """Get visual marker for severity level - 4-tier system"""
        if not self.use_emoji:
            text_markers = {
                'critical': '[CRIT]',
                'high': '[HIGH]',
                'medium': '[MED]',
                'low': '[LOW]'
            }
            return text_markers.get(severity, '[ ]')
        markers = {
            'critical': ' ALERT: ',
            'high': '[U+1F534]',
            'medium': '[U+1F7E1]',
            'low': '[U+1F7E2]'
        }
        return markers.get(severity, '[U+26AA]')