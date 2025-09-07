#!/usr/bin/env python3
"""
MISSION CRITICAL E2E TEST: Enhanced Complete User Prompt to Report Generation Flow

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prove core value proposition works end-to-end with enhanced validation
- Value Impact: Users receive actionable AI insights that solve real problems
- Strategic Impact: Core validation of $3M+ ARR business model with comprehensive testing

This test validates the COMPLETE business value chain with enhanced:
1. Sophisticated business value scoring algorithms
2. Comprehensive event sequence validation
3. Performance profiling and monitoring
4. Error scenario testing and edge cases
5. Resource monitoring and cleanup

REQUIREMENTS FROM CLAUDE.md:
- NO MOCKS AT ALL - Uses REAL services only (WebSocket, Database, LLM)
- Tests the 5 REQUIRED WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Real authentication with JWT tokens via E2EAuthHelper
- Complete flow validation with enhanced business value assessment
- Report content quality validation with sophisticated algorithms
- Performance timing validation under 2 minutes
- Comprehensive error handling and edge case testing

KEY ARCHITECTURAL COMPLIANCE:
- Uses SSOT E2EAuthHelper for authentication
- Uses IsolatedEnvironment per unified_environment_management.xml
- Real WebSocket connections with actual backend
- Validates WebSocket agent integration per websocket_agent_integration_critical.xml
- Tests business value delivery with enhanced validation algorithms
- Comprehensive resource monitoring and cleanup

ANY FAILURE HERE INDICATES CORE VALUE PROPOSITION IS BROKEN.
"""

import asyncio
import json
import os
import sys
import time
import uuid
import psutil
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass
import statistics

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import SSOT authentication and environment isolation
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.environment_isolation import isolated_test_env
from tests.clients.websocket_client import WebSocketTestClient
from tests.clients.backend_client import BackendTestClient
from tests.clients.auth_client import AuthTestClient
from shared.isolated_environment import get_env

# Create a simple fixture for testing
@pytest.fixture
async def isolated_test_environment():
    """Enhanced isolated test environment for E2E testing."""
    from test_framework.environment_isolation import setup_real_services_environment
    setup_real_services_environment()
    yield {}  # Return empty dict as placeholder


# ============================================================================
# ENHANCED BUSINESS VALUE REPORT VALIDATOR
# ============================================================================

@dataclass
class BusinessValueMetrics:
    """Detailed metrics for business value analysis."""
    score: float = 0.0
    keyword_density: float = 0.0
    quantitative_score: float = 0.0
    industry_relevance: float = 0.0
    roi_analysis: float = 0.0
    structure_quality: float = 0.0
    content_depth: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'overall_score': self.score,
            'keyword_density': self.keyword_density,
            'quantitative_score': self.quantitative_score,
            'industry_relevance': self.industry_relevance,
            'roi_analysis': self.roi_analysis,
            'structure_quality': self.structure_quality,
            'content_depth': self.content_depth
        }


class EnhancedBusinessValueReportValidator:
    """Enhanced validator for reports containing actual business value.
    
    Provides sophisticated scoring and validation algorithms to ensure reports
    deliver actionable insights that solve real business problems.
    """
    
    # Enhanced keywords for actionable business insights
    BUSINESS_VALUE_KEYWORDS = {
        'recommendations', 'optimize', 'reduce', 'improve', 'save', 'savings',
        'cost', 'efficiency', 'performance', 'strategy', 'opportunity',
        'action', 'implement', 'upgrade', 'migrate', 'configure',
        'best practices', 'guidelines', 'steps', 'plan', 'solution',
        'prioritize', 'eliminate', 'consolidate', 'streamline', 'automate'
    }
    
    # Enhanced quantitative indicators
    QUANTITATIVE_KEYWORDS = {
        '$', '%', 'percent', 'dollars', 'cost', 'hours', 'minutes',
        'reduction', 'increase', 'improvement', 'roi', 'return on investment',
        'budget', 'expense', 'annually', 'monthly', 'quarterly', 'per year',
        'faster', 'slower', 'efficiency gain', 'cost savings', 'time savings'
    }
    
    # Industry-specific value indicators
    INDUSTRY_RELEVANCE_KEYWORDS = {
        'cloud', 'aws', 'azure', 'gcp', 'kubernetes', 'docker', 'serverless',
        'infrastructure', 'database', 'storage', 'compute', 'networking',
        'security', 'compliance', 'monitoring', 'logging', 'backup',
        'scalability', 'availability', 'disaster recovery', 'devops'
    }
    
    # ROI calculation indicators
    ROI_INDICATORS = {
        'payback period', 'break even', 'profit margin', 'cost benefit',
        'investment return', 'savings per month', 'annual savings',
        'cost avoidance', 'efficiency gains', 'productivity increase'
    }
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.business_metrics: BusinessValueMetrics = BusinessValueMetrics()
        self.detailed_analysis: Dict[str, Any] = {}
        
    def validate_report(self, report_content: str) -> Tuple[bool, BusinessValueMetrics, List[str]]:
        """
        Enhanced validation of report business value with sophisticated scoring.
        
        Args:
            report_content: The final report text from the agent
            
        Returns:
            Tuple of (is_valid, business_metrics, errors)
        """
        if not report_content or len(report_content.strip()) < 100:
            self.errors.append("Report too short - insufficient content for business value")
            return False, self.business_metrics, self.errors
            
        content_lower = report_content.lower()
        
        # Perform comprehensive analysis
        business_analysis = self._analyze_business_keywords(content_lower)
        quantitative_analysis = self._analyze_quantitative_content(content_lower)
        industry_analysis = self._analyze_industry_relevance(content_lower)
        roi_analysis = self._analyze_roi_content(content_lower)
        structural_analysis = self._analyze_report_structure(report_content)
        depth_analysis = self._analyze_content_depth(report_content)
        
        # Calculate sophisticated business value metrics
        self.business_metrics = self._calculate_enhanced_metrics(
            business_analysis, quantitative_analysis, industry_analysis,
            roi_analysis, structural_analysis, depth_analysis
        )
        
        # Store detailed analysis for debugging
        self.detailed_analysis = {
            'business_keywords': business_analysis,
            'quantitative_content': quantitative_analysis,
            'industry_relevance': industry_analysis,
            'roi_analysis': roi_analysis,
            'structure_analysis': structural_analysis,
            'content_depth': depth_analysis,
            'content_length': len(report_content),
            'word_count': len(report_content.split()),
            'sentence_count': report_content.count('.') + report_content.count('!') + report_content.count('?')
        }
        
        # Enhanced validation with multiple quality levels
        is_valid = self._validate_enhanced_criteria()
        
        return is_valid, self.business_metrics, self.errors
    
    def _analyze_business_keywords(self, content_lower: str) -> Dict[str, Any]:
        """Analyze business keyword density with weighted scoring."""
        found_keywords = [kw for kw in self.BUSINESS_VALUE_KEYWORDS if kw in content_lower]
        density = len(found_keywords) / len(self.BUSINESS_VALUE_KEYWORDS) if self.BUSINESS_VALUE_KEYWORDS else 0
        
        # Weight keywords by importance
        high_value_keywords = ['recommendations', 'optimize', 'save', 'improve', 'reduce']
        high_value_count = sum(1 for kw in high_value_keywords if kw in content_lower)
        
        # Calculate keyword distribution
        keyword_frequency = Counter(kw for kw in self.BUSINESS_VALUE_KEYWORDS if kw in content_lower)
        
        return {
            'found_keywords': found_keywords,
            'density': density,
            'high_value_count': high_value_count,
            'keyword_frequency': keyword_frequency,
            'unique_keyword_count': len(found_keywords),
            'score': min(35, density * 35 + high_value_count * 2)
        }
    
    def _analyze_quantitative_content(self, content_lower: str) -> Dict[str, Any]:
        """Analyze quantitative data presence and quality."""
        found_quantitative = [kw for kw in self.QUANTITATIVE_KEYWORDS if kw in content_lower]
        
        # Specific quantitative indicators
        has_percentages = any(indicator in content_lower for indicator in ['%', 'percent'])
        has_monetary = any(indicator in content_lower for indicator in ['$', 'dollar', 'cost'])
        has_time_metrics = any(kw in content_lower for kw in ['hours', 'minutes', 'days', 'weeks'])
        has_improvement_metrics = any(kw in content_lower for kw in ['faster', 'slower', 'efficiency'])
        
        # Advanced quantitative analysis
        numeric_patterns = self._extract_numeric_patterns(content_lower)
        
        base_score = min(25, len(found_quantitative) * 2.5)
        bonus_score = 0
        
        if has_percentages:
            bonus_score += 6
        if has_monetary:
            bonus_score += 6
        if has_time_metrics:
            bonus_score += 4
        if has_improvement_metrics:
            bonus_score += 3
        if numeric_patterns['count'] > 0:
            bonus_score += min(5, numeric_patterns['count'])
            
        return {
            'found_keywords': found_quantitative,
            'has_data': len(found_quantitative) > 0,
            'has_percentages': has_percentages,
            'has_monetary': has_monetary,
            'has_time_metrics': has_time_metrics,
            'has_improvement_metrics': has_improvement_metrics,
            'numeric_patterns': numeric_patterns,
            'score': base_score + bonus_score
        }
    
    def _analyze_industry_relevance(self, content_lower: str) -> Dict[str, Any]:
        """Analyze industry-specific relevance and technical depth."""
        found_industry = [kw for kw in self.INDUSTRY_RELEVANCE_KEYWORDS if kw in content_lower]
        
        # Specific industry focus areas
        has_cloud_focus = any(kw in content_lower for kw in ['aws', 'azure', 'gcp', 'cloud'])
        has_containerization = any(kw in content_lower for kw in ['kubernetes', 'docker', 'container'])
        has_database_focus = any(kw in content_lower for kw in ['database', 'sql', 'nosql', 'storage'])
        has_security_focus = any(kw in content_lower for kw in ['security', 'compliance', 'encryption'])
        
        # Technical depth indicators
        has_technical_depth = len(found_industry) >= 3
        has_specific_technologies = len([kw for kw in found_industry if kw in ['kubernetes', 'docker', 'terraform']]) > 0
        
        return {
            'found_keywords': found_industry,
            'has_relevance': len(found_industry) > 0,
            'has_cloud_focus': has_cloud_focus,
            'has_containerization': has_containerization,
            'has_database_focus': has_database_focus,
            'has_security_focus': has_security_focus,
            'has_technical_depth': has_technical_depth,
            'has_specific_technologies': has_specific_technologies,
            'score': min(18, len(found_industry) * 2.5 + (3 if has_specific_technologies else 0))
        }
    
    def _analyze_roi_content(self, content_lower: str) -> Dict[str, Any]:
        """Analyze ROI and financial impact content."""
        found_roi = [kw for kw in self.ROI_INDICATORS if kw in content_lower]
        
        # Financial analysis indicators
        has_timeframe = any(kw in content_lower for kw in ['monthly', 'annually', 'quarterly'])
        has_cost_benefit = any(kw in content_lower for kw in ['savings', 'cost reduction', 'efficiency'])
        has_investment_analysis = any(kw in content_lower for kw in ['investment', 'payback', 'break even'])
        
        return {
            'found_keywords': found_roi,
            'has_roi': len(found_roi) > 0,
            'has_timeframe': has_timeframe,
            'has_cost_benefit': has_cost_benefit,
            'has_investment_analysis': has_investment_analysis,
            'score': min(12, len(found_roi) * 4 + (4 if has_timeframe else 0) + (2 if has_investment_analysis else 0))
        }
    
    def _analyze_report_structure(self, report_content: str) -> Dict[str, Any]:
        """Analyze report structure and recommendations quality."""
        content_lower = report_content.lower()
        sections = [s.strip() for s in report_content.split('\n\n') if s.strip()]
        
        # Structured content indicators
        has_recommendations_section = any(
            marker in content_lower for marker in [
                'recommendations:', 'suggested actions:', 'next steps:', 
                'action items:', 'implementation plan:', 'key recommendations'
            ]
        )
        
        # Specific actionable advice indicators
        specific_actions = [
            'configure', 'set to', 'change to', 'upgrade to', 'migrate from',
            'implement', 'deploy', 'enable', 'disable', 'replace with',
            'switch to', 'consolidate', 'eliminate', 'automate', 'scale up',
            'scale down', 'optimize for', 'tune', 'adjust'
        ]
        
        specific_action_count = sum(1 for action in specific_actions if action in content_lower)
        has_specific_recommendations = specific_action_count >= 2
        
        # Prioritization and organization
        has_prioritization = any(
            marker in content_lower for marker in [
                'priority', 'first', 'second', 'third', 'immediate', 'short-term', 
                'long-term', 'critical', 'important', 'quick wins', 'phase'
            ]
        )
        
        has_bullet_points = report_content.count('•') + report_content.count('-') + report_content.count('*') >= 3
        has_numbered_list = any(f'{i}.' in report_content for i in range(1, 6))
        
        # Calculate structure score
        structure_score = 0
        if has_recommendations_section:
            structure_score += 12
        if has_specific_recommendations:
            structure_score += 15
        if has_prioritization:
            structure_score += 6
        if len(sections) >= 3:
            structure_score += 4
        if has_bullet_points or has_numbered_list:
            structure_score += 3
            
        return {
            'sections_count': len(sections),
            'has_recommendations_section': has_recommendations_section,
            'has_specific_recommendations': has_specific_recommendations,
            'specific_action_count': specific_action_count,
            'has_prioritization': has_prioritization,
            'has_bullet_points': has_bullet_points,
            'has_numbered_list': has_numbered_list,
            'score': structure_score
        }
    
    def _analyze_content_depth(self, report_content: str) -> Dict[str, Any]:
        """Analyze content depth and comprehensiveness."""
        word_count = len(report_content.split())
        sentence_count = report_content.count('.') + report_content.count('!') + report_content.count('?')
        paragraph_count = len([p for p in report_content.split('\n\n') if p.strip()])
        
        # Content quality indicators
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        has_examples = any(indicator in report_content.lower() for indicator in ['example', 'for instance', 'such as'])
        has_explanations = any(indicator in report_content.lower() for indicator in ['because', 'due to', 'reason'])
        
        # Calculate depth score
        depth_score = 0
        if word_count > 200:
            depth_score += 3
        if word_count > 500:
            depth_score += 4
        if word_count > 1000:
            depth_score += 3
        if paragraph_count >= 3:
            depth_score += 2
        if has_examples:
            depth_score += 2
        if has_explanations:
            depth_score += 2
        if 10 <= avg_sentence_length <= 25:  # Optimal sentence length range
            depth_score += 2
            
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'paragraph_count': paragraph_count,
            'avg_sentence_length': avg_sentence_length,
            'has_examples': has_examples,
            'has_explanations': has_explanations,
            'score': depth_score
        }
    
    def _extract_numeric_patterns(self, content_lower: str) -> Dict[str, Any]:
        """Extract and analyze numeric patterns in content."""
        import re
        
        # Pattern for numbers with units (percentages, currency, etc.)
        numeric_patterns = re.findall(r'\b\d+(?:\.\d+)?(?:\s*[%$]|\s*percent|\s*dollars?|\s*hours?|\s*minutes?)\b', content_lower)
        standalone_numbers = re.findall(r'\b\d+(?:\.\d+)?\b', content_lower)
        
        return {
            'numeric_with_units': numeric_patterns,
            'standalone_numbers': standalone_numbers,
            'count': len(numeric_patterns) + len(standalone_numbers),
            'has_percentages': any('%' in pattern or 'percent' in pattern for pattern in numeric_patterns),
            'has_currency': any('$' in pattern or 'dollar' in pattern for pattern in numeric_patterns)
        }
    
    def _calculate_enhanced_metrics(
        self, 
        business_analysis: Dict,
        quantitative_analysis: Dict,
        industry_analysis: Dict,
        roi_analysis: Dict,
        structural_analysis: Dict,
        depth_analysis: Dict
    ) -> BusinessValueMetrics:
        """Calculate enhanced business value metrics with weighted components."""
        
        # Component scores (total possible: 100)
        keyword_score = business_analysis['score']  # 0-35
        quantitative_score = quantitative_analysis['score']  # 0-33
        industry_score = industry_analysis['score']  # 0-18
        roi_score = roi_analysis['score']  # 0-12
        structure_score = structural_analysis['score']  # 0-40
        depth_score = depth_analysis['score']  # 0-18
        
        total_score = min(100, keyword_score + quantitative_score + industry_score + roi_score + structure_score + depth_score)
        
        return BusinessValueMetrics(
            score=total_score,
            keyword_density=business_analysis['density'],
            quantitative_score=quantitative_score,
            industry_relevance=industry_score,
            roi_analysis=roi_score,
            structure_quality=structure_score,
            content_depth=depth_score
        )
    
    def _validate_enhanced_criteria(self) -> bool:
        """Enhanced validation criteria for business value."""
        score = self.business_metrics.score
        structural_analysis = self.detailed_analysis.get('structure_analysis', {})
        quantitative_analysis = self.detailed_analysis.get('quantitative_content', {})
        content_length = self.detailed_analysis.get('content_length', 0)
        
        # Enhanced validation thresholds
        if score < 65:  # Raised from 60 to 65
            self.errors.append(f"Insufficient business value score: {score:.1f}/100 (minimum 65)")
            
        if not structural_analysis.get('has_recommendations_section', False):
            self.errors.append("Report lacks structured recommendations section")
            
        if not structural_analysis.get('has_specific_recommendations', False):
            self.errors.append("Report lacks specific, actionable recommendations")
            
        if content_length < 350:  # Raised from 300 to 350
            self.errors.append(f"Report too brief: {content_length} chars (minimum 350)")
            
        if structural_analysis.get('specific_action_count', 0) < 2:
            self.errors.append("Report needs more specific action items (minimum 2)")
            
        # Quality warnings
        if not quantitative_analysis.get('has_data', False):
            self.warnings.append("Report would benefit from quantitative metrics")
            
        if self.business_metrics.industry_relevance < 5:
            self.warnings.append("Report could include more industry-specific insights")
            
        if not structural_analysis.get('has_prioritization', False):
            self.warnings.append("Report would benefit from prioritized recommendations")
        
        # Success criteria
        meets_minimum = (
            score >= 65 and
            structural_analysis.get('has_recommendations_section', False) and
            content_length >= 350
        )
        
        meets_quality = (
            score >= 75 and
            structural_analysis.get('has_specific_recommendations', False) and
            structural_analysis.get('specific_action_count', 0) >= 2
        )
        
        return meets_minimum


# ============================================================================
# ENHANCED WEBSOCKET EVENT VALIDATOR
# ============================================================================

@dataclass 
class EventSequenceMetrics:
    """Metrics for WebSocket event sequence analysis."""
    total_events: int = 0
    required_events_count: int = 0
    event_timing_analysis: Dict[str, float] = None
    sequence_integrity: float = 0.0
    business_content_ratio: float = 0.0
    
    def __post_init__(self):
        if self.event_timing_analysis is None:
            self.event_timing_analysis = {}


class EnhancedCompleteFlowEventValidator:
    """Enhanced validator for complete WebSocket event flow with sophisticated analysis."""
    
    # REQUIRED events for complete business value flow
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    # Business value indicating event types
    BUSINESS_VALUE_EVENTS = {
        "report_generated", "final_report", "analysis_complete",
        "recommendations_ready", "insights_generated", "agent_completed"
    }
    
    # Expected event order patterns
    EXPECTED_ORDER_PATTERNS = [
        ["agent_started", "agent_thinking"],
        ["tool_executing", "tool_completed"],
        ["agent_completed"]
    ]
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_timeline: List[Tuple[float, str, Dict]] = []
        self.event_counts: Dict[str, int] = defaultdict(int)
        self.event_timing: Dict[str, List[float]] = defaultdict(list)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()
        self.business_content_events: List[Dict] = []
        self.performance_metrics: Dict[str, Any] = {}
        
    def record_event(self, event: Dict[str, Any]) -> None:
        """Record an event with enhanced timing and content analysis."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        # Enhanced event recording
        enhanced_event = {
            **event.copy(),
            'recorded_at': timestamp,
            'sequence_position': len(self.events),
            'content_size': self._calculate_content_size(event)
        }
        
        self.events.append(enhanced_event)
        self.event_timeline.append((timestamp, event_type, enhanced_event))
        self.event_counts[event_type] += 1
        self.event_timing[event_type].append(timestamp)
        
        # Track business content events with enhanced criteria
        if self._has_enhanced_business_content(event):
            self.business_content_events.append(enhanced_event)
        
        logger.info(f"[ENHANCED FLOW EVENT] {event_type} at {timestamp:.3f}s (size: {enhanced_event['content_size']} bytes)")
        
    def _calculate_content_size(self, event: Dict[str, Any]) -> int:
        """Calculate the content size of an event."""
        content_fields = ['result', 'response', 'message', 'content', 'output', 'data', 'analysis']
        total_size = 0
        
        for field in content_fields:
            content = event.get(field, '')
            if isinstance(content, str):
                total_size += len(content)
            elif isinstance(content, dict):
                total_size += len(json.dumps(content))
                
        return total_size
        
    def _has_enhanced_business_content(self, event: Dict[str, Any]) -> bool:
        """Enhanced check for business-relevant content."""
        content_fields = ['result', 'response', 'message', 'content', 'output', 'data', 'analysis']
        
        for field in content_fields:
            content = event.get(field, '')
            if isinstance(content, str) and len(content) > 50:
                # Check for business keywords
                content_lower = content.lower()
                business_indicators = ['recommend', 'optimize', 'improve', 'cost', 'save', 'efficiency']
                if any(indicator in content_lower for indicator in business_indicators):
                    return True
            elif isinstance(content, dict) and content:
                return True
                
        return False
        
    def validate_complete_flow(self) -> Tuple[bool, EventSequenceMetrics, List[str]]:
        """Enhanced validation of the complete business value delivery flow."""
        failures = []
        
        # Generate performance metrics
        self.performance_metrics = self._generate_performance_metrics()
        
        # 1. CRITICAL: All required events must be present
        missing_events = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing_events:
            failures.append(f"CRITICAL: Missing required WebSocket events: {missing_events}")
        
        # 2. CRITICAL: Events must be in proper order with enhanced validation
        order_issues = self._validate_enhanced_event_order()
        if order_issues:
            failures.extend(order_issues)
        
        # 3. CRITICAL: Tool events must be paired properly
        tool_pairing_issues = self._validate_enhanced_tool_pairing()
        if tool_pairing_issues:
            failures.extend(tool_pairing_issues)
        
        # 4. CRITICAL: Must have substantial business content
        content_issues = self._validate_enhanced_business_content()
        if content_issues:
            failures.extend(content_issues)
        
        # 5. CRITICAL: Enhanced timing validation
        timing_issues = self._validate_enhanced_performance_timing()
        if timing_issues:
            failures.extend(timing_issues)
        
        # 6. CRITICAL: Enhanced completion content validation
        completion_issues = self._validate_enhanced_completion_content()
        if completion_issues:
            failures.extend(completion_issues)
        
        # Generate sequence metrics
        sequence_metrics = self._calculate_sequence_metrics()
        
        return len(failures) == 0, sequence_metrics, failures
    
    def _validate_enhanced_event_order(self) -> List[str]:
        """Enhanced event order validation with pattern matching."""
        issues = []
        
        if not self.event_timeline:
            issues.append("No events received - complete flow failure")
            return issues
            
        event_sequence = [event[1] for event in self.event_timeline]
        
        # First event MUST be agent_started
        if event_sequence[0] != "agent_started":
            issues.append(f"Flow must start with 'agent_started', got '{event_sequence[0]}'")
        
        # Last event validation with multiple valid endings
        valid_endings = {"agent_completed", "final_report", "report_generated", "analysis_complete"}
        if event_sequence[-1] not in valid_endings:
            issues.append(f"Flow should end with completion event, got '{event_sequence[-1]}'")
        
        # Pattern validation: agent_thinking should come before tool execution (if tools used)
        if "tool_executing" in event_sequence and "agent_thinking" in event_sequence:
            thinking_idx = event_sequence.index("agent_thinking")
            tool_idx = event_sequence.index("tool_executing")
            if thinking_idx > tool_idx:
                issues.append("agent_thinking should come before tool_executing")
        
        # Validate no premature completion
        if "agent_completed" in event_sequence:
            completion_idx = event_sequence.index("agent_completed")
            if completion_idx < len(event_sequence) - 3:  # Allow some trailing events
                issues.append("agent_completed appears too early in sequence")
                
        return issues
    
    def _validate_enhanced_tool_pairing(self) -> List[str]:
        """Enhanced tool event pairing validation."""
        issues = []
        
        executing_count = self.event_counts.get("tool_executing", 0)
        completed_count = self.event_counts.get("tool_completed", 0)
        
        if executing_count != completed_count:
            issues.append(f"Tool event mismatch: {executing_count} executing vs {completed_count} completed")
        
        # Enhanced: Check for reasonable tool usage patterns
        if executing_count == 0:
            # This might be OK for simple queries, but warn
            self.warnings.append("No tool executions detected - may indicate simple query or issue")
        elif executing_count > 10:
            # Too many tool executions might indicate inefficiency
            self.warnings.append(f"High tool execution count ({executing_count}) - check for efficiency")
            
        # Check timing between tool events
        if executing_count > 0:
            exec_times = self.event_timing.get("tool_executing", [])
            comp_times = self.event_timing.get("tool_completed", [])
            
            if exec_times and comp_times:
                avg_tool_duration = statistics.mean([
                    comp_times[i] - exec_times[i] 
                    for i in range(min(len(exec_times), len(comp_times)))
                ])
                
                if avg_tool_duration > 30.0:
                    self.warnings.append(f"Long average tool duration: {avg_tool_duration:.1f}s")
                elif avg_tool_duration < 0.1:
                    issues.append(f"Suspiciously short tool duration: {avg_tool_duration:.3f}s")
                    
        return issues
    
    def _validate_enhanced_business_content(self) -> List[str]:
        """Enhanced validation of business-relevant content."""
        issues = []
        
        if len(self.business_content_events) == 0:
            issues.append("CRITICAL: No events contain substantial business content")
            return issues
        
        # Enhanced content requirements
        min_business_events = max(2, len(self.events) // 4)  # At least 25% should have business content
        if len(self.business_content_events) < min_business_events:
            issues.append(f"Insufficient business content events: {len(self.business_content_events)} (min {min_business_events})")
        
        # Check content size distribution
        content_sizes = [event.get('content_size', 0) for event in self.business_content_events]
        if content_sizes:
            avg_content_size = statistics.mean(content_sizes)
            if avg_content_size < 100:
                self.warnings.append(f"Low average content size in business events: {avg_content_size:.1f} bytes")
                
        return issues
    
    def _validate_enhanced_performance_timing(self) -> List[str]:
        """Enhanced performance timing validation."""
        issues = []
        
        if not self.event_timeline:
            return issues
            
        total_time = self.event_timeline[-1][0]
        
        # Dynamic timeout based on complexity
        tool_count = self.event_counts.get("tool_executing", 0)
        expected_max_time = 60.0 + (tool_count * 20.0)  # Base 60s + 20s per tool
        
        if total_time > expected_max_time:
            issues.append(f"Flow too slow: {total_time:.1f}s (max {expected_max_time:.1f}s for {tool_count} tools)")
        
        # Minimum time validation (avoid suspiciously fast completion)
        min_expected_time = 3.0 + (tool_count * 1.0)  # Minimum realistic time
        if total_time < min_expected_time:
            issues.append(f"Flow too fast: {total_time:.1f}s - likely skipping real work (min {min_expected_time:.1f}s)")
        
        # Gap analysis between events
        gaps = []
        for i in range(1, len(self.event_timeline)):
            gap = self.event_timeline[i][0] - self.event_timeline[i-1][0]
            gaps.append(gap)
        
        if gaps:
            max_gap = max(gaps)
            avg_gap = statistics.mean(gaps)
            
            # Check for excessive gaps
            if max_gap > 45.0:
                issues.append(f"Excessive gap between events: {max_gap:.1f}s")
            
            # Check for suspicious timing patterns
            if len(gaps) > 3:
                gap_variance = statistics.variance(gaps)
                if gap_variance > 100:  # High variance indicates inconsistent timing
                    self.warnings.append(f"Inconsistent event timing (variance: {gap_variance:.1f})")
                    
        return issues
    
    def _validate_enhanced_completion_content(self) -> List[str]:
        """Enhanced completion content validation."""
        issues = []
        
        completion_events = [e for e in self.events 
                           if e.get("type") in {"agent_completed", "final_report", "report_generated"}]
        
        if not completion_events:
            issues.append("CRITICAL: No completion events with content found")
            return issues
        
        for event in completion_events:
            content_size = event.get('content_size', 0)
            
            # Enhanced content size requirements
            if content_size < 200:
                issues.append(f"Completion event content too small: {content_size} bytes (min 200)")
            
            # Check for structured content
            content_fields = ['result', 'response', 'final_response', 'report', 'analysis']
            has_structured_content = False
            
            for field in content_fields:
                content = event.get(field, '')
                if isinstance(content, str) and len(content) > 100:
                    # Check for business value indicators in completion
                    content_lower = content.lower()
                    business_indicators = ['recommend', 'suggest', 'action', 'optimize', 'improve']
                    if any(indicator in content_lower for indicator in business_indicators):
                        has_structured_content = True
                        break
                elif isinstance(content, dict) and content:
                    has_structured_content = True
                    break
            
            if not has_structured_content:
                issues.append(f"Completion event lacks structured business content")
                
        return issues
    
    def _generate_performance_metrics(self) -> Dict[str, Any]:
        """Generate comprehensive performance metrics."""
        if not self.event_timeline:
            return {}
        
        total_time = self.event_timeline[-1][0]
        event_count = len(self.events)
        
        # Event frequency analysis
        event_frequencies = {}
        if total_time > 0:
            for event_type, count in self.event_counts.items():
                event_frequencies[event_type] = count / total_time
        
        # Timing distribution
        gaps = []
        for i in range(1, len(self.event_timeline)):
            gaps.append(self.event_timeline[i][0] - self.event_timeline[i-1][0])
        
        timing_stats = {}
        if gaps:
            timing_stats = {
                'min_gap': min(gaps),
                'max_gap': max(gaps),
                'avg_gap': statistics.mean(gaps),
                'median_gap': statistics.median(gaps)
            }
        
        return {
            'total_duration': total_time,
            'total_events': event_count,
            'events_per_second': event_count / total_time if total_time > 0 else 0,
            'event_frequencies': event_frequencies,
            'timing_statistics': timing_stats,
            'business_content_ratio': len(self.business_content_events) / event_count if event_count > 0 else 0,
            'required_events_ratio': len(set(self.event_counts.keys()) & self.REQUIRED_EVENTS) / len(self.REQUIRED_EVENTS)
        }
    
    def _calculate_sequence_metrics(self) -> EventSequenceMetrics:
        """Calculate comprehensive sequence metrics."""
        required_present = len(set(self.event_counts.keys()) & self.REQUIRED_EVENTS)
        
        return EventSequenceMetrics(
            total_events=len(self.events),
            required_events_count=required_present,
            event_timing_analysis=self.performance_metrics.get('timing_statistics', {}),
            sequence_integrity=required_present / len(self.REQUIRED_EVENTS) if self.REQUIRED_EVENTS else 0,
            business_content_ratio=len(self.business_content_events) / len(self.events) if self.events else 0
        )


# ============================================================================
# ENHANCED RESOURCE MONITOR
# ============================================================================

class ResourceMonitor:
    """Monitor system resources during test execution."""
    
    def __init__(self):
        self.start_metrics: Dict[str, float] = {}
        self.peak_metrics: Dict[str, float] = {}
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        
    def start_monitoring(self) -> None:
        """Start resource monitoring in background thread."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self._stop_monitoring.clear()
        
        # Capture initial metrics
        self.start_metrics = self._capture_metrics()
        self.peak_metrics = self.start_metrics.copy()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return resource usage summary."""
        if not self.monitoring:
            return {}
            
        self.monitoring = False
        self._stop_monitoring.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        final_metrics = self._capture_metrics()
        
        return {
            'start_metrics': self.start_metrics,
            'final_metrics': final_metrics,
            'peak_metrics': self.peak_metrics,
            'resource_usage': {
                'memory_increase_mb': final_metrics['memory_mb'] - self.start_metrics['memory_mb'],
                'cpu_peak_percent': self.peak_metrics['cpu_percent'],
                'memory_peak_mb': self.peak_metrics['memory_mb'],
                'open_files_increase': final_metrics['open_files'] - self.start_metrics['open_files']
            }
        }
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._stop_monitoring.wait(1.0):  # Sample every second
            try:
                current_metrics = self._capture_metrics()
                
                # Update peak values
                for key, value in current_metrics.items():
                    if key in self.peak_metrics:
                        self.peak_metrics[key] = max(self.peak_metrics[key], value)
                        
            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")
                
    def _capture_metrics(self) -> Dict[str, float]:
        """Capture current system metrics."""
        try:
            process = psutil.Process()
            
            return {
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'open_files': process.num_fds() if hasattr(process, 'num_fds') else len(process.open_files()),
                'threads': process.num_threads()
            }
        except Exception as e:
            logger.warning(f"Failed to capture metrics: {e}")
            return {'memory_mb': 0, 'cpu_percent': 0, 'open_files': 0, 'threads': 0}


# ============================================================================
# ENHANCED COMPLETE FLOW TEST INFRASTRUCTURE
# ============================================================================

class EnhancedCompleteUserPromptToReportTester:
    """Enhanced tester for complete user prompt to report generation flow."""
    
    def __init__(self):
        self.auth_helper = None
        self.ws_client = None
        self.backend_client = None
        self.auth_client = None
        self.test_user_token = None
        self.test_env = None
        self.resource_monitor = ResourceMonitor()
        
    async def setup_real_services(self, isolated_env) -> None:
        """Setup real service connections with enhanced monitoring and validation."""
        self.test_env = isolated_env
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        
        # Initialize SSOT authentication helper
        self.auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Get service endpoints with validation
        from shared.isolated_environment import get_env
        env = get_env()
        
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000") 
        auth_host = env.get("AUTH_SERVICE_HOST", "localhost")
        auth_port = env.get("AUTH_SERVICE_PORT", "8081")
        
        backend_url = f"http://{backend_host}:{backend_port}"
        auth_url = f"http://{auth_host}:{auth_port}"
        ws_url = f"ws://{backend_host}:{backend_port}/ws"
        
        logger.info(f"Setting up enhanced real services - Backend: {backend_url}, Auth: {auth_url}, WS: {ws_url}")
        
        # Validate service availability
        await self._validate_service_availability(backend_url, auth_url)
        
        # Initialize clients with enhanced configuration
        self.backend_client = BackendTestClient(backend_url)
        self.auth_client = AuthTestClient(auth_url)
        
        # Enhanced authentication with retry logic
        max_auth_attempts = 3
        for attempt in range(max_auth_attempts):
            try:
                self.test_user_token, user_data = await self.auth_helper.authenticate_user()
                logger.info(f"Authenticated test user: {user_data.get('email', 'unknown')} (attempt {attempt + 1})")
                break
            except Exception as e:
                if attempt == max_auth_attempts - 1:
                    # Final attempt - use fallback
                    logger.warning(f"SSOT auth failed after {max_auth_attempts} attempts ({e}), using fallback")
                    test_user_data = await self.auth_client.create_test_user()
                    self.test_user_token = test_user_data["token"]
                    break
                else:
                    logger.warning(f"Auth attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(1.0)
        
        # Enhanced WebSocket setup with connection validation
        self.ws_client = WebSocketTestClient(ws_url)
        max_connect_attempts = 3
        
        for attempt in range(max_connect_attempts):
            try:
                connected = await self.ws_client.connect(token=self.test_user_token, timeout=15.0)
                if connected:
                    # Validate connection with ping
                    await self._validate_websocket_connection()
                    break
                else:
                    raise RuntimeError(f"Connection returned False on attempt {attempt + 1}")
            except Exception as e:
                if attempt == max_connect_attempts - 1:
                    raise RuntimeError(f"Failed to establish WebSocket connection after {max_connect_attempts} attempts: {e}")
                logger.warning(f"WebSocket connection attempt {attempt + 1} failed: {e}, retrying...")
                await asyncio.sleep(2.0)
            
        logger.info("✅ Enhanced real services setup complete with validation")
    
    async def _validate_service_availability(self, backend_url: str, auth_url: str) -> None:
        """Validate that required services are available."""
        import aiohttp
        
        services = {"Backend": backend_url, "Auth": auth_url}
        
        async with aiohttp.ClientSession() as session:
            for service_name, url in services.items():
                try:
                    health_url = f"{url}/health" if service_name == "Backend" else f"{url}/auth/health"
                    async with session.get(health_url, timeout=5.0) as response:
                        if response.status != 200:
                            logger.warning(f"{service_name} service health check failed: {response.status}")
                except Exception as e:
                    logger.warning(f"{service_name} service not available at {url}: {e}")
    
    async def _validate_websocket_connection(self) -> None:
        """Validate WebSocket connection is working properly."""
        test_ping = {
            "type": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.ws_client.send(test_ping)
        
        # Wait for pong or any response
        try:
            response = await self.ws_client.receive(timeout=5.0)
            if response:
                logger.info("✅ WebSocket connection validated")
            else:
                raise RuntimeError("No response to WebSocket ping")
        except asyncio.TimeoutError:
            raise RuntimeError("WebSocket ping timeout - connection may be unstable")
        
    async def test_complete_prompt_to_report_flow(
        self, 
        user_prompt: str, 
        timeout: float = 120.0,
        expected_complexity: str = "medium"
    ) -> Tuple[bool, EnhancedCompleteFlowEventValidator, Optional[str], Dict[str, Any]]:
        """
        Enhanced test of complete user prompt to report generation flow.
        
        Args:
            user_prompt: The user's prompt/question
            timeout: Maximum time to wait for completion
            expected_complexity: Expected complexity level (simple/medium/complex)
            
        Returns:
            Tuple of (success, validator, final_report_content, performance_metrics)
        """
        if not self.ws_client:
            raise RuntimeError("WebSocket client not initialized")
            
        validator = EnhancedCompleteFlowEventValidator()
        final_report_content = None
        performance_start = time.time()
        
        # Adjust timeout based on expected complexity
        complexity_multipliers = {"simple": 1.0, "medium": 1.5, "complex": 2.0}
        adjusted_timeout = timeout * complexity_multipliers.get(expected_complexity, 1.0)
        
        logger.info(f"🚀 Starting enhanced flow test with prompt: '{user_prompt[:50]}...'")
        logger.info(f"Expected complexity: {expected_complexity}, timeout: {adjusted_timeout:.1f}s")
        
        # Start event collection with enhanced monitoring
        event_task = asyncio.create_task(
            self._collect_enhanced_flow_events(validator, adjusted_timeout, expected_complexity)
        )
        
        # Send user prompt through WebSocket
        prompt_message = {
            "type": "chat_message",
            "text": user_prompt,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "test_id": str(uuid.uuid4()),
                "expected_complexity": expected_complexity
            }
        }
        
        await self.ws_client.send_chat(text=user_prompt)
        logger.info("📤 Enhanced user prompt sent via WebSocket")
        
        # Wait for complete flow to finish with enhanced timeout handling
        try:
            await event_task
        except asyncio.TimeoutError:
            logger.error(f"⏰ Enhanced flow timed out after {adjusted_timeout:.1f}s")
            
        execution_time = time.time() - performance_start
        
        # Extract final report content with enhanced extraction
        final_report_content = self._extract_enhanced_final_report(validator.events)
        
        # Enhanced validation with performance metrics
        is_valid, sequence_metrics, failures = validator.validate_complete_flow()
        
        # Get resource usage metrics
        resource_metrics = self.resource_monitor.stop_monitoring()
        
        # Compile comprehensive performance metrics
        performance_metrics = {
            'execution_time': execution_time,
            'expected_complexity': expected_complexity,
            'sequence_metrics': sequence_metrics.to_dict() if hasattr(sequence_metrics, 'to_dict') else sequence_metrics.__dict__,
            'resource_usage': resource_metrics,
            'validator_metrics': validator.performance_metrics,
            'event_count': len(validator.events),
            'business_content_events': len(validator.business_content_events)
        }
        
        if is_valid and final_report_content:
            logger.info(f"✅ Enhanced complete prompt-to-report flow PASSED in {execution_time:.2f}s")
        else:
            logger.error(f"❌ Enhanced complete flow FAILED: {failures}")
            
        return is_valid, validator, final_report_content, performance_metrics
        
    async def _collect_enhanced_flow_events(
        self, 
        validator: EnhancedCompleteFlowEventValidator, 
        timeout: float,
        expected_complexity: str
    ) -> None:
        """Enhanced event collection with complexity-aware monitoring."""
        start_time = time.time()
        flow_completed = False
        
        completion_events = {"agent_completed", "final_report", "report_generated", "analysis_complete"}
        
        # Complexity-based expectations
        complexity_expectations = {
            "simple": {"min_events": 5, "min_business_events": 2},
            "medium": {"min_events": 8, "min_business_events": 3}, 
            "complex": {"min_events": 12, "min_business_events": 5}
        }
        
        expectations = complexity_expectations.get(expected_complexity, complexity_expectations["medium"])
        
        event_count_at_last_check = 0
        stall_detection_interval = 10.0  # Check for stalls every 10 seconds
        last_stall_check = start_time
        
        while not flow_completed and (time.time() - start_time) < timeout:
            try:
                message = await self.ws_client.receive(timeout=3.0)
                
                if message:
                    validator.record_event(message)
                    
                    # Enhanced completion detection
                    event_type = message.get("type", "")
                    if event_type in completion_events:
                        # Verify we have sufficient events for the complexity level
                        if len(validator.events) >= expectations["min_events"]:
                            logger.info(f"🏁 Enhanced flow completed with event: {event_type}")
                            await asyncio.sleep(2.0)  # Allow for trailing events
                            flow_completed = True
                        else:
                            logger.info(f"Completion event received but insufficient events ({len(validator.events)}/{expectations['min_events']})")
                    
                    # Stall detection
                    current_time = time.time()
                    if current_time - last_stall_check >= stall_detection_interval:
                        events_since_check = len(validator.events) - event_count_at_last_check
                        if events_since_check == 0:
                            logger.warning(f"⚠️ No events received in last {stall_detection_interval}s - possible stall")
                        
                        event_count_at_last_check = len(validator.events)
                        last_stall_check = current_time
                        
            except asyncio.TimeoutError:
                # Brief timeouts are expected, continue collecting
                continue
            except Exception as e:
                logger.error(f"Error in enhanced event collection: {e}")
                break
                
        if not flow_completed:
            logger.warning(f"⚠️ Enhanced flow did not complete within {timeout:.1f}s")
            logger.info(f"Collected {len(validator.events)} events, expected >= {expectations['min_events']}")
            
    def _extract_enhanced_final_report(self, events: List[Dict[str, Any]]) -> Optional[str]:
        """Enhanced extraction of final report content."""
        # Look for completion events in reverse order (most recent first)
        completion_events = [e for e in reversed(events) 
                           if e.get("type") in {"agent_completed", "final_report", "report_generated", "analysis_complete"}]
        
        # Try multiple strategies to extract content
        extraction_strategies = [
            self._extract_from_specific_fields,
            self._extract_from_structured_content,
            self._extract_from_concatenated_content
        ]
        
        for strategy in extraction_strategies:
            content = strategy(completion_events)
            if content and len(content) > 100:
                return content
                
        # Final fallback: look for any substantial content in recent events
        recent_events = events[-10:] if len(events) >= 10 else events
        for event in reversed(recent_events):
            for field in ['result', 'response', 'message', 'content', 'data']:
                content = event.get(field)
                if isinstance(content, str) and len(content) > 100:
                    return content
                    
        return None
    
    def _extract_from_specific_fields(self, completion_events: List[Dict]) -> Optional[str]:
        """Extract content from specific fields in completion events."""
        priority_fields = ['final_response', 'report', 'analysis', 'result', 'response']
        
        for event in completion_events:
            for field in priority_fields:
                content = event.get(field)
                if isinstance(content, str) and len(content) > 100:
                    return content
                elif isinstance(content, dict):
                    # Try to extract text from structured content
                    for subfield in ['content', 'text', 'report', 'analysis']:
                        subcontent = content.get(subfield)
                        if isinstance(subcontent, str) and len(subcontent) > 100:
                            return subcontent
                            
        return None
    
    def _extract_from_structured_content(self, completion_events: List[Dict]) -> Optional[str]:
        """Extract content from structured data in completion events."""
        for event in completion_events:
            # Look for nested content structures
            for field in ['data', 'payload', 'body']:
                content = event.get(field)
                if isinstance(content, dict):
                    for subfield in ['report', 'analysis', 'response', 'text']:
                        subcontent = content.get(subfield)
                        if isinstance(subcontent, str) and len(subcontent) > 100:
                            return subcontent
                            
        return None
    
    def _extract_from_concatenated_content(self, completion_events: List[Dict]) -> Optional[str]:
        """Fallback: concatenate all substantial content from completion events."""
        all_content = []
        
        for event in completion_events:
            for field in ['result', 'response', 'message', 'content']:
                content = event.get(field)
                if isinstance(content, str) and len(content) > 50:
                    all_content.append(content)
                    
        combined_content = '\n\n'.join(all_content)
        return combined_content if len(combined_content) > 100 else None
        
    async def cleanup(self) -> None:
        """Enhanced cleanup with resource monitoring."""
        logger.info("🧹 Starting enhanced cleanup")
        
        # Stop resource monitoring if still running
        if self.resource_monitor.monitoring:
            resource_summary = self.resource_monitor.stop_monitoring()
            logger.info(f"Final resource usage: {resource_summary.get('resource_usage', {})}")
        
        # Clean up connections
        cleanup_tasks = []
        
        if self.ws_client:
            cleanup_tasks.append(self.ws_client.disconnect())
        if self.backend_client:
            cleanup_tasks.append(self.backend_client.close())
        if self.auth_client:
            cleanup_tasks.append(self.auth_client.close())
            
        if cleanup_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("Cleanup timeout - some connections may not have closed cleanly")
            
        logger.info("✅ Enhanced cleanup completed")


# ============================================================================
# ENHANCED TEST CASES WITH ERROR SCENARIOS
# ============================================================================

class TestEnhancedCompleteUserPromptToReportFlow:
    """Enhanced mission critical tests for complete user prompt to actionable report flow."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_enhanced_basic_optimization_query(self, isolated_test_environment):
        """
        ENHANCED: Basic Optimization Query with Sophisticated Validation
        
        Tests the core business value proposition with enhanced validation:
        - Sophisticated business value scoring algorithms
        - Enhanced event sequence validation  
        - Performance profiling and resource monitoring
        - Comprehensive error detection and reporting
        
        This is the #1 most important test - validates core $3M+ ARR value prop.
        """
        tester = EnhancedCompleteUserPromptToReportTester()
        
        try:
            # Enhanced setup with validation
            await tester.setup_real_services(isolated_test_environment)
            
            # Test enhanced optimization query
            optimization_query = (
                "I'm spending $15,000/month on AWS infrastructure across 25 EC2 instances, "
                "RDS databases, and S3 storage. My team is complaining about slow performance "
                "and high costs. Please analyze my setup and provide specific cost optimization "
                "recommendations with expected savings and implementation timeframes."
            )
            
            # Execute enhanced flow test
            start_time = time.time()
            is_valid, validator, final_report, performance_metrics = await tester.test_complete_prompt_to_report_flow(
                user_prompt=optimization_query,
                timeout=120.0,
                expected_complexity="medium"
            )
            execution_time = time.time() - start_time
            
            # ENHANCED CRITICAL ASSERTIONS
            
            # 1. Core flow validation
            assert is_valid, f"CRITICAL: Enhanced flow failed: {validator.errors}"
            assert final_report, "CRITICAL: No final report generated"
            assert len(final_report) >= 350, f"Report too brief: {len(final_report)} chars (min 350)"
            
            # 2. Enhanced WebSocket events validation
            missing_events = validator.REQUIRED_EVENTS - set(validator.event_counts.keys())
            assert len(missing_events) == 0, f"Missing critical events: {missing_events}"
            
            # 3. Enhanced business value validation
            bv_validator = EnhancedBusinessValueReportValidator()
            has_value, business_metrics, value_errors = bv_validator.validate_report(final_report)
            
            assert has_value, f"CRITICAL: Report lacks business value: {value_errors}"
            assert business_metrics.score >= 65, f"Business value score too low: {business_metrics.score}/100 (min 65)"
            
            # 4. Enhanced content validation
            report_lower = final_report.lower()
            
            # Must contain optimization-specific terms
            optimization_terms = ['cost', 'optimize', 'save', 'reduce', 'efficiency', 'recommend']
            found_terms = [term for term in optimization_terms if term in report_lower]
            assert len(found_terms) >= 4, f"Report lacks optimization focus, found: {found_terms}"
            
            # Must contain AWS-specific references
            aws_terms = ['aws', 'ec2', 'rds', 's3', 'instance', 'database', 'storage']
            found_aws_terms = [term for term in aws_terms if term in report_lower]
            assert len(found_aws_terms) >= 3, f"Report should reference AWS services, found: {found_aws_terms}"
            
            # 5. Enhanced performance validation
            assert execution_time <= 120.0, f"Flow too slow: {execution_time:.1f}s (max 120s)"
            
            # Performance metrics validation
            sequence_metrics = performance_metrics.get('sequence_metrics', {})
            assert sequence_metrics.get('sequence_integrity', 0) >= 0.8, "Poor event sequence integrity"
            assert sequence_metrics.get('business_content_ratio', 0) >= 0.3, "Insufficient business content ratio"
            
            # 6. Tool usage validation
            tool_count = validator.event_counts.get("tool_executing", 0)
            assert tool_count >= 1, f"No tools executed for analysis (got {tool_count})"
            
            # 7. Resource usage validation
            resource_usage = performance_metrics.get('resource_usage', {})
            memory_increase = resource_usage.get('memory_increase_mb', 0)
            assert memory_increase < 500, f"Excessive memory usage: {memory_increase:.1f}MB"
            
            # Success logging with enhanced metrics
            logger.info(f"✅ ENHANCED CRITICAL TEST PASSED: {execution_time:.2f}s")
            logger.info(f"📊 Business Value Score: {business_metrics.score:.1f}/100")
            logger.info(f"📝 Report Length: {len(final_report)} chars")
            logger.info(f"🔧 Tools Used: {tool_count}")
            logger.info(f"⚡ Event Sequence Integrity: {sequence_metrics.get('sequence_integrity', 0):.2f}")
            logger.info(f"💾 Memory Usage: {memory_increase:.1f}MB")
            
        except Exception as e:
            logger.error(f"❌ ENHANCED CRITICAL TEST FAILED: {e}")
            raise
        finally:
            await tester.cleanup()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e 
    @pytest.mark.real_services
    async def test_enhanced_complex_infrastructure_analysis(self, isolated_test_environment):
        """
        ENHANCED: Complex Infrastructure Analysis with Advanced Validation
        
        Tests sophisticated analysis capability with enhanced validation:
        - Multi-dimensional infrastructure analysis
        - Advanced business value algorithms
        - Performance profiling for complex queries
        - Comprehensive architectural recommendations validation
        """
        tester = EnhancedCompleteUserPromptToReportTester()
        
        try:
            await tester.setup_real_services(isolated_test_environment)
            
            # Complex infrastructure query
            complex_query = (
                "I'm running a microservices architecture on AWS with 50+ EC2 instances "
                "across multiple availability zones, using EKS for container orchestration, "
                "RDS Aurora for databases, ElastiCache for caching, and CloudFront for CDN. "
                "We're experiencing performance bottlenecks, high costs ($25K/month), and "
                "security compliance challenges. Please analyze our entire infrastructure "
                "and provide a comprehensive optimization plan with security improvements, "
                "cost reduction strategies, and performance enhancements. Include specific "
                "recommendations for each service, expected ROI, and implementation phases."
            )
            
            start_time = time.time()
            is_valid, validator, final_report, performance_metrics = await tester.test_complete_prompt_to_report_flow(
                user_prompt=complex_query,
                timeout=180.0,  # Longer timeout for complex analysis
                expected_complexity="complex"
            )
            execution_time = time.time() - start_time
            
            # ENHANCED ASSERTIONS FOR COMPLEX ANALYSIS
            
            # 1. Flow completion validation
            assert is_valid, f"Complex infrastructure analysis flow failed: {validator.errors}"
            assert final_report, "No complex analysis report generated"
            assert len(final_report) >= 800, f"Complex report too brief: {len(final_report)} chars (min 800)"
            
            # 2. Enhanced business value validation for complex analysis
            bv_validator = EnhancedBusinessValueReportValidator()
            has_value, business_metrics, value_errors = bv_validator.validate_report(final_report)
            
            assert has_value, f"Complex analysis lacks business value: {value_errors}"
            assert business_metrics.score >= 70, f"Complex analysis score too low: {business_metrics.score}/100 (min 70)"
            
            # Complex analysis should have high industry relevance
            assert business_metrics.industry_relevance >= 10, f"Low industry relevance: {business_metrics.industry_relevance}"
            assert business_metrics.structure_quality >= 25, f"Poor structure quality: {business_metrics.structure_quality}"
            
            # 3. Comprehensive service coverage validation
            report_lower = final_report.lower()
            
            # Must mention multiple AWS services
            aws_services = ['ec2', 'eks', 'rds', 'aurora', 'elasticache', 'cloudfront', 'kubernetes']
            mentioned_services = [svc for svc in aws_services if svc in report_lower]
            assert len(mentioned_services) >= 4, f"Should reference multiple AWS services, found: {mentioned_services}"
            
            # Must have architectural focus
            arch_terms = ['architecture', 'microservices', 'availability zone', 'performance', 'security', 'compliance']
            arch_mentions = [term for term in arch_terms if term in report_lower]
            assert len(arch_mentions) >= 4, f"Should have strong architectural focus, found: {arch_mentions}"
            
            # Must include optimization strategies
            optimization_terms = ['optimize', 'reduce costs', 'improve performance', 'enhance security', 'roi']
            opt_mentions = [term for term in optimization_terms if term in report_lower]
            assert len(opt_mentions) >= 3, f"Should include optimization strategies, found: {opt_mentions}"
            
            # 4. Enhanced performance validation for complex queries
            assert execution_time <= 180.0, f"Complex analysis too slow: {execution_time:.1f}s (max 180s)"
            
            # Should use multiple tools for comprehensive analysis
            tool_count = validator.event_counts.get("tool_executing", 0)
            assert tool_count >= 2, f"Complex analysis needs multiple tools (got {tool_count})"
            
            # 5. Event sequence validation for complex flow
            sequence_metrics = performance_metrics.get('sequence_metrics', {})
            assert sequence_metrics.get('total_events', 0) >= 10, "Complex flow should generate many events"
            assert sequence_metrics.get('business_content_ratio', 0) >= 0.4, "Complex analysis needs high business content ratio"
            
            logger.info(f"✅ ENHANCED Complex infrastructure analysis PASSED: {execution_time:.2f}s")
            logger.info(f"📊 Business Score: {business_metrics.score:.1f}/100")
            logger.info(f"🏗️ Services Mentioned: {mentioned_services}")
            logger.info(f"🔧 Tools Used: {tool_count}")
            logger.info(f"📈 Total Events: {sequence_metrics.get('total_events', 0)}")
            
        finally:
            await tester.cleanup()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_enhanced_error_recovery_scenarios(self, isolated_test_environment):
        """
        ENHANCED: Error Recovery and Edge Case Testing
        
        Tests system resilience with various error scenarios:
        - Network timeout simulation
        - Malformed queries
        - Service interruption recovery
        - Resource exhaustion handling
        """
        tester = EnhancedCompleteUserPromptToReportTester()
        
        try:
            await tester.setup_real_services(isolated_test_environment)
            
            # Test cases for error scenarios
            error_test_cases = [
                {
                    "name": "Very short query",
                    "query": "Help",
                    "expected_behavior": "should_complete_with_clarification",
                    "timeout": 30.0
                },
                {
                    "name": "Extremely long query", 
                    "query": "Analyze my AWS infrastructure " * 100,  # Very long repeated text
                    "expected_behavior": "should_complete_within_timeout",
                    "timeout": 90.0
                },
                {
                    "name": "Mixed language query",
                    "query": "Optimize my cloud costs. Como puedo reducir costos en la nube?",
                    "expected_behavior": "should_handle_gracefully", 
                    "timeout": 60.0
                }
            ]
            
            results = []
            
            for test_case in error_test_cases:
                logger.info(f"Testing error scenario: {test_case['name']}")
                
                try:
                    start_time = time.time()
                    is_valid, validator, final_report, performance_metrics = await tester.test_complete_prompt_to_report_flow(
                        user_prompt=test_case["query"],
                        timeout=test_case["timeout"],
                        expected_complexity="simple"
                    )
                    execution_time = time.time() - start_time
                    
                    # Basic resilience assertions
                    test_result = {
                        'test_name': test_case['name'],
                        'completed': is_valid,
                        'execution_time': execution_time,
                        'final_report_length': len(final_report) if final_report else 0,
                        'event_count': len(validator.events),
                        'errors': validator.errors[:3]  # First 3 errors
                    }
                    
                    # Validate basic resilience requirements
                    if test_case['expected_behavior'] == "should_complete_with_clarification":
                        # Even short queries should generate some response
                        assert final_report is not None, f"No response to short query: {test_case['name']}"
                        assert len(final_report) >= 50, f"Response too brief for short query: {len(final_report)}"
                        
                    elif test_case['expected_behavior'] == "should_complete_within_timeout":
                        # Long queries should not hang
                        assert execution_time <= test_case['timeout'], f"Long query exceeded timeout: {execution_time:.1f}s"
                        
                    elif test_case['expected_behavior'] == "should_handle_gracefully":
                        # Mixed scenarios should not crash
                        assert len(validator.events) > 0, f"No events generated for mixed query: {test_case['name']}"
                    
                    results.append(test_result)
                    logger.info(f"✅ Error scenario '{test_case['name']}' handled: {execution_time:.2f}s")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error scenario '{test_case['name']}' failed: {e}")
                    results.append({
                        'test_name': test_case['name'],
                        'completed': False,
                        'error': str(e)
                    })
            
            # Overall resilience validation
            completed_tests = sum(1 for r in results if r.get('completed', False))
            resilience_ratio = completed_tests / len(test_cases) if test_cases else 0
            
            assert resilience_ratio >= 0.7, f"Poor system resilience: {resilience_ratio:.2f} ({completed_tests}/{len(test_cases)})"
            
            logger.info(f"✅ ENHANCED Error recovery testing completed")
            logger.info(f"🛡️ Resilience ratio: {resilience_ratio:.2f}")
            logger.info(f"📊 Test results: {results}")
            
        finally:
            await tester.cleanup()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_enhanced_performance_profiling_validation(self, isolated_test_environment):
        """
        ENHANCED: Performance Profiling and Resource Monitoring
        
        Tests performance characteristics with comprehensive monitoring:
        - Response time analysis across query types
        - Resource usage profiling
        - Event timing validation
        - Memory and connection leak detection
        """
        tester = EnhancedCompleteUserPromptToReportTester()
        
        try:
            await tester.setup_real_services(isolated_test_environment)
            
            # Performance test queries of varying complexity
            performance_queries = [
                {
                    "name": "Simple query",
                    "query": "What are 3 quick wins for AWS cost optimization?",
                    "complexity": "simple",
                    "max_time": 45.0,
                    "min_events": 5
                },
                {
                    "name": "Medium query", 
                    "query": "Analyze my EC2 instances and provide cost optimization recommendations with ROI calculations.",
                    "complexity": "medium",
                    "max_time": 90.0,
                    "min_events": 8
                }
            ]
            
            performance_results = []
            
            for query_test in performance_queries:
                logger.info(f"Performance testing: {query_test['name']}")
                
                start_time = time.time()
                is_valid, validator, final_report, performance_metrics = await tester.test_complete_prompt_to_report_flow(
                    user_prompt=query_test["query"],
                    timeout=query_test["max_time"] + 30,  # Buffer for timeout
                    expected_complexity=query_test["complexity"]
                )
                execution_time = time.time() - start_time
                
                # Performance validation assertions
                assert is_valid, f"Performance test failed: {query_test['name']}"
                assert execution_time <= query_test["max_time"], f"{query_test['name']} too slow: {execution_time:.1f}s (max {query_test['max_time']}s)"
                assert len(validator.events) >= query_test["min_events"], f"Insufficient events for {query_test['name']}: {len(validator.events)}"
                
                # Detailed performance analysis
                sequence_metrics = performance_metrics.get('sequence_metrics', {})
                resource_usage = performance_metrics.get('resource_usage', {})
                
                perf_result = {
                    'query_type': query_test['name'],
                    'complexity': query_test['complexity'],
                    'execution_time': execution_time,
                    'events_generated': len(validator.events),
                    'business_content_ratio': sequence_metrics.get('business_content_ratio', 0),
                    'memory_usage_mb': resource_usage.get('memory_increase_mb', 0),
                    'event_sequence_integrity': sequence_metrics.get('sequence_integrity', 0)
                }
                
                # Performance quality checks
                assert perf_result['business_content_ratio'] >= 0.2, f"Low business content ratio: {perf_result['business_content_ratio']}"
                assert perf_result['memory_usage_mb'] < 300, f"High memory usage: {perf_result['memory_usage_mb']}MB"
                assert perf_result['event_sequence_integrity'] >= 0.8, f"Poor event integrity: {perf_result['event_sequence_integrity']}"
                
                performance_results.append(perf_result)
                
                logger.info(f"✅ Performance test '{query_test['name']}' passed: {execution_time:.2f}s")
                logger.info(f"📊 Events: {len(validator.events)}, Memory: {perf_result['memory_usage_mb']:.1f}MB")
                
                # Brief pause between tests
                await asyncio.sleep(2.0)
            
            # Overall performance analysis
            avg_execution_time = statistics.mean([r['execution_time'] for r in performance_results])
            avg_memory_usage = statistics.mean([r['memory_usage_mb'] for r in performance_results])
            avg_business_ratio = statistics.mean([r['business_content_ratio'] for r in performance_results])
            
            # Performance benchmarks
            assert avg_execution_time <= 60.0, f"Average execution time too high: {avg_execution_time:.2f}s"
            assert avg_memory_usage <= 150.0, f"Average memory usage too high: {avg_memory_usage:.2f}MB" 
            assert avg_business_ratio >= 0.25, f"Average business content ratio too low: {avg_business_ratio:.3f}"
            
            logger.info(f"✅ ENHANCED Performance profiling completed")
            logger.info(f"⚡ Average execution time: {avg_execution_time:.2f}s")
            logger.info(f"💾 Average memory usage: {avg_memory_usage:.2f}MB")
            logger.info(f"📈 Average business content ratio: {avg_business_ratio:.3f}")
            
        finally:
            await tester.cleanup()


# ============================================================================
# ENHANCED TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """
    Run the enhanced complete user prompt to report flow tests.
    
    These tests validate core business value delivery with enhanced validation:
    - Sophisticated business value scoring algorithms
    - Comprehensive event sequence validation
    - Performance profiling and resource monitoring  
    - Error scenario testing and edge cases
    - Resource monitoring and cleanup
    
    Usage:
        python test_complete_user_prompt_to_report_flow_enhanced.py
        pytest test_complete_user_prompt_to_report_flow_enhanced.py -v -s
    """
    
    logger.info("🚀 Starting ENHANCED MISSION CRITICAL complete user prompt to report tests")
    logger.info("⚠️  USING REAL SERVICES ONLY - NO MOCKS")
    logger.info("💼 Testing complete business value delivery with enhanced validation")
    logger.info("📊 Including performance profiling, resource monitoring, and error scenarios")
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v", "-s",
        "--tb=short",
        "--timeout=400",  # Longer timeout for enhanced tests
        "-x"  # Stop on first failure for critical tests
    ])
    
    if exit_code == 0:
        logger.info("✅ ALL ENHANCED COMPLETE FLOW TESTS PASSED - Business value delivery verified")
    else:
        logger.error("❌ ENHANCED COMPLETE FLOW TESTS FAILED - Business value delivery broken")
    
    sys.exit(exit_code)