"""
Business Value Validation Framework for E2E Tests

MISSION CRITICAL: Validates that agents deliver substantive business value,
not just technical success. This framework ensures the Golden Path user
journey delivers 90% of platform value ($500K+ ARR).

Business Value Justification (BVJ):
- Segment: All Users (Free/Early/Mid/Enterprise)  
- Business Goal: Platform Revenue Protection & Customer Satisfaction
- Value Impact: Ensures AI responses provide actionable insights and solutions
- Strategic Impact: $500K+ ARR depends on quality AI chat interactions

Usage:
- Integrate into existing E2E and integration tests
- Add business value assertions to existing technical validations
- Fail tests when responses lack substance or actionability
- Validate customer outcome achievement, not just message delivery
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class BusinessValueDimension(Enum):
    """Core dimensions of business value delivery."""
    PROBLEM_SOLVING = "problem_solving"  # Does it solve the user's problem?
    ACTIONABILITY = "actionability"      # Are the recommendations actionable?
    COST_OPTIMIZATION = "cost_optimization"  # Does it help optimize costs?
    INSIGHT_QUALITY = "insight_quality"  # Quality of insights provided
    CUSTOMER_OUTCOME = "customer_outcome"  # Achievement of customer goals
    BUSINESS_IMPACT = "business_impact"  # Measurable business impact


@dataclass
class BusinessValueScore:
    """Score for a specific business value dimension."""
    dimension: BusinessValueDimension
    score: float  # 0.0 to 1.0 where 1.0 is excellent business value
    evidence: List[str]  # Evidence supporting the score
    deficiencies: List[str]  # Areas lacking business value
    customer_impact: str  # Description of customer impact


@dataclass
class BusinessValueAssessment:
    """Comprehensive business value assessment of an AI response."""
    overall_score: float  # 0.0 to 1.0
    dimension_scores: Dict[BusinessValueDimension, BusinessValueScore]
    delivers_business_value: bool  # Does this meet business standards?
    customer_satisfaction_tier: str  # "Poor", "Acceptable", "Good", "Excellent"
    revenue_protection_score: float  # How well does this protect $500K+ ARR?
    competitive_advantage: bool  # Does this provide competitive advantage?
    
    # Golden Path specific metrics
    chat_substance_quality: float  # Quality of chat substance (0.0-1.0)
    ai_optimization_value: float   # AI optimization value delivered (0.0-1.0)
    user_goal_achievement: float   # How well user goals were achieved (0.0-1.0)


class BusinessValueValidator:
    """
    Validates business value delivery in AI agent responses.
    
    This validator focuses on the SUBSTANCE and VALUE of AI interactions,
    not just technical success metrics. It ensures responses justify
    the platform's premium positioning and protect revenue.
    """
    
    def __init__(self):
        self.business_value_thresholds = {
            "Poor": 0.0,      # No discernible business value
            "Acceptable": 0.6,  # Minimum acceptable business value
            "Good": 0.75,      # Good business value delivery
            "Excellent": 0.9   # Exceptional business value
        }
        
        self.revenue_protection_threshold = 0.7  # Minimum score to protect $500K+ ARR
        
        # Problem-solving indicators
        self.problem_solving_indicators = [
            'analyze', 'identify', 'diagnose', 'troubleshoot', 'solve',
            'resolve', 'fix', 'address', 'investigate', 'determine',
            'root cause', 'issue', 'problem', 'challenge', 'bottleneck'
        ]
        
        # Actionability indicators  
        self.actionability_indicators = [
            'recommend', 'suggest', 'implement', 'configure', 'set up',
            'deploy', 'optimize', 'improve', 'increase', 'reduce',
            'step 1', 'step 2', 'next steps', 'action plan', 'roadmap',
            'execute', 'apply', 'install', 'upgrade', 'modify'
        ]
        
        # Cost optimization indicators
        self.cost_optimization_indicators = [
            'cost reduction', 'save money', 'reduce costs', 'optimize spend',
            'efficiency', 'resource utilization', 'waste reduction',
            'budget optimization', 'roi', 'return on investment',
            'cost-effective', 'economic benefit', 'financial impact'
        ]
        
        # Business impact indicators
        self.business_impact_indicators = [
            'revenue', 'growth', 'scalability', 'competitive advantage',
            'market position', 'customer satisfaction', 'retention',
            'productivity', 'performance improvement', 'strategic value',
            'business outcome', 'measurable impact', 'kpi', 'metric'
        ]
        
        # Quality insight indicators
        self.insight_quality_indicators = [
            'insight', 'trend', 'pattern', 'correlation', 'analysis',
            'data-driven', 'evidence-based', 'research', 'benchmark',
            'comparison', 'forecast', 'prediction', 'strategic implication'
        ]

    def validate_business_value(
        self, 
        response: Union[str, Dict, Any], 
        user_query: str = "",
        user_context: Optional[Dict] = None,
        expected_outcomes: Optional[List[str]] = None
    ) -> BusinessValueAssessment:
        """
        Comprehensive business value validation of an AI agent response.
        
        Args:
            response: The AI agent response (string, dict, or structured data)
            user_query: Original user query/request
            user_context: Additional context about user and their goals
            expected_outcomes: Expected business outcomes for this interaction
            
        Returns:
            BusinessValueAssessment with detailed scoring and analysis
        """
        # Convert response to analyzable text
        response_text = self._extract_response_text(response)
        
        if not response_text:
            return self._create_failed_assessment("Empty or invalid response")
        
        # Evaluate each business value dimension
        dimension_scores = {}
        dimension_scores[BusinessValueDimension.PROBLEM_SOLVING] = self._evaluate_problem_solving(
            response_text, user_query
        )
        dimension_scores[BusinessValueDimension.ACTIONABILITY] = self._evaluate_actionability(
            response_text
        )
        dimension_scores[BusinessValueDimension.COST_OPTIMIZATION] = self._evaluate_cost_optimization(
            response_text
        )
        dimension_scores[BusinessValueDimension.INSIGHT_QUALITY] = self._evaluate_insight_quality(
            response_text
        )
        dimension_scores[BusinessValueDimension.CUSTOMER_OUTCOME] = self._evaluate_customer_outcome(
            response_text, user_query, expected_outcomes
        )
        dimension_scores[BusinessValueDimension.BUSINESS_IMPACT] = self._evaluate_business_impact(
            response_text
        )
        
        # Calculate overall business value score
        overall_score = sum(score.score for score in dimension_scores.values()) / len(dimension_scores)
        
        # Determine customer satisfaction tier
        customer_satisfaction_tier = "Poor"
        for tier, threshold in sorted(self.business_value_thresholds.items(), key=lambda x: x[1], reverse=True):
            if overall_score >= threshold:
                customer_satisfaction_tier = tier
                break
        
        # Calculate Golden Path specific metrics
        chat_substance_quality = self._calculate_chat_substance_quality(dimension_scores)
        ai_optimization_value = self._calculate_ai_optimization_value(dimension_scores)
        user_goal_achievement = self._calculate_user_goal_achievement(dimension_scores, expected_outcomes)
        
        # Determine business value delivery status
        delivers_business_value = overall_score >= 0.6  # 60% minimum for business value
        revenue_protection_score = overall_score  # Direct correlation for now
        competitive_advantage = overall_score >= 0.8  # 80% threshold for competitive advantage
        
        return BusinessValueAssessment(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            delivers_business_value=delivers_business_value,
            customer_satisfaction_tier=customer_satisfaction_tier,
            revenue_protection_score=revenue_protection_score,
            competitive_advantage=competitive_advantage,
            chat_substance_quality=chat_substance_quality,
            ai_optimization_value=ai_optimization_value,
            user_goal_achievement=user_goal_achievement
        )

    def _extract_response_text(self, response: Union[str, Dict, Any]) -> str:
        """Extract text content from various response formats."""
        if isinstance(response, str):
            return response
        
        if isinstance(response, dict):
            # Handle various dict structures
            for key in ['content', 'text', 'message', 'response', 'result', 'output']:
                if key in response and isinstance(response[key], str):
                    return response[key]
            
            # If it's a dict, convert to JSON string for analysis
            return json.dumps(response, indent=2)
        
        # For other types, convert to string
        return str(response)

    def _evaluate_problem_solving(self, response_text: str, user_query: str) -> BusinessValueScore:
        """Evaluate problem-solving capability of the response."""
        response_lower = response_text.lower()
        query_lower = user_query.lower() if user_query else ""
        
        score = 0.3  # Base score
        evidence = []
        deficiencies = []
        
        # Count problem-solving indicators
        problem_indicators_found = sum(1 for indicator in self.problem_solving_indicators 
                                     if indicator in response_lower)
        
        # Analyze problem identification
        if problem_indicators_found >= 3:
            score += 0.4
            evidence.append(f"Strong problem-solving approach with {problem_indicators_found} key indicators")
        elif problem_indicators_found >= 1:
            score += 0.2
            evidence.append(f"Some problem-solving elements with {problem_indicators_found} indicators")
        else:
            deficiencies.append("Lacks clear problem-solving approach or terminology")
        
        # Check if response addresses user query context
        if user_query and len(user_query) > 10:
            query_keywords = set(re.findall(r'\b\w{4,}\b', query_lower))
            response_keywords = set(re.findall(r'\b\w{4,}\b', response_lower))
            keyword_overlap = len(query_keywords.intersection(response_keywords))
            
            if keyword_overlap >= 3:
                score += 0.2
                evidence.append(f"Addresses user query with {keyword_overlap} relevant keywords")
            elif keyword_overlap >= 1:
                score += 0.1
                evidence.append(f"Partially addresses user query")
            else:
                deficiencies.append("Response doesn't clearly address user query")
        
        # Ensure score doesn't exceed 1.0
        score = min(score, 1.0)
        
        customer_impact = self._assess_customer_impact_problem_solving(score, evidence)
        
        return BusinessValueScore(
            dimension=BusinessValueDimension.PROBLEM_SOLVING,
            score=score,
            evidence=evidence,
            deficiencies=deficiencies,
            customer_impact=customer_impact
        )

    def _evaluate_actionability(self, response_text: str) -> BusinessValueScore:
        """Evaluate actionability and implementability of recommendations."""
        response_lower = response_text.lower()
        
        score = 0.2  # Base score
        evidence = []
        deficiencies = []
        
        # Count actionability indicators
        action_indicators_found = sum(1 for indicator in self.actionability_indicators 
                                    if indicator in response_lower)
        
        if action_indicators_found >= 5:
            score = 0.9
            evidence.append(f"Highly actionable with {action_indicators_found} action indicators")
        elif action_indicators_found >= 3:
            score = 0.7
            evidence.append(f"Good actionability with {action_indicators_found} action indicators")
        elif action_indicators_found >= 1:
            score = 0.5
            evidence.append(f"Some actionable elements with {action_indicators_found} indicators")
        else:
            score = 0.2
            deficiencies.append("Lacks clear actionable recommendations")
        
        # Check for structured recommendations (numbered lists, bullet points)
        if re.search(r'\d+\.|\-|\*|\•', response_text):
            score += 0.1
            evidence.append("Contains structured recommendations (lists/steps)")
        
        # Check for specific implementation details
        implementation_indicators = ['configure', 'install', 'set up', 'command', 'script', 'code']
        impl_count = sum(1 for indicator in implementation_indicators if indicator in response_lower)
        if impl_count >= 2:
            score += 0.1
            evidence.append("Includes specific implementation details")
        
        score = min(score, 1.0)
        customer_impact = self._assess_customer_impact_actionability(score, evidence)
        
        return BusinessValueScore(
            dimension=BusinessValueDimension.ACTIONABILITY,
            score=score,
            evidence=evidence,
            deficiencies=deficiencies,
            customer_impact=customer_impact
        )

    def _evaluate_cost_optimization(self, response_text: str) -> BusinessValueScore:
        """Evaluate cost optimization value delivered."""
        response_lower = response_text.lower()
        
        score = 0.1  # Base score
        evidence = []
        deficiencies = []
        
        # Count cost optimization indicators
        cost_indicators_found = sum(1 for indicator in self.cost_optimization_indicators 
                                  if indicator in response_lower)
        
        if cost_indicators_found >= 3:
            score = 0.8
            evidence.append(f"Strong cost optimization focus with {cost_indicators_found} indicators")
        elif cost_indicators_found >= 1:
            score = 0.5
            evidence.append(f"Some cost optimization elements with {cost_indicators_found} indicators")
        else:
            score = 0.1
            deficiencies.append("Limited focus on cost optimization or financial benefits")
        
        # Check for quantitative cost information
        if re.search(r'\$\d+|\d+%|\d+\s*(percent|%)', response_text):
            score += 0.2
            evidence.append("Includes quantitative cost/savings information")
        
        score = min(score, 1.0)
        customer_impact = self._assess_customer_impact_cost_optimization(score, evidence)
        
        return BusinessValueScore(
            dimension=BusinessValueDimension.COST_OPTIMIZATION,
            score=score,
            evidence=evidence,
            deficiencies=deficiencies,
            customer_impact=customer_impact
        )

    def _evaluate_insight_quality(self, response_text: str) -> BusinessValueScore:
        """Evaluate quality and depth of insights provided."""
        response_lower = response_text.lower()
        
        score = 0.2  # Base score
        evidence = []
        deficiencies = []
        
        # Count insight quality indicators
        insight_indicators_found = sum(1 for indicator in self.insight_quality_indicators 
                                     if indicator in response_lower)
        
        if insight_indicators_found >= 3:
            score = 0.8
            evidence.append(f"High-quality insights with {insight_indicators_found} quality indicators")
        elif insight_indicators_found >= 1:
            score = 0.5
            evidence.append(f"Some quality insights with {insight_indicators_found} indicators")
        else:
            deficiencies.append("Lacks deep insights or analysis")
        
        # Check response length as proxy for depth
        if len(response_text) > 500:
            score += 0.1
            evidence.append("Detailed response suggesting thorough analysis")
        elif len(response_text) < 100:
            score -= 0.1
            deficiencies.append("Response may be too brief for comprehensive insights")
        
        score = min(max(score, 0.0), 1.0)
        customer_impact = self._assess_customer_impact_insights(score, evidence)
        
        return BusinessValueScore(
            dimension=BusinessValueDimension.INSIGHT_QUALITY,
            score=score,
            evidence=evidence,
            deficiencies=deficiencies,
            customer_impact=customer_impact
        )

    def _evaluate_customer_outcome(self, response_text: str, user_query: str, 
                                 expected_outcomes: Optional[List[str]]) -> BusinessValueScore:
        """Evaluate likelihood of achieving customer outcomes."""
        score = 0.3  # Base score
        evidence = []
        deficiencies = []
        
        # If expected outcomes are provided, check alignment
        if expected_outcomes:
            outcome_alignment = 0
            for outcome in expected_outcomes:
                if outcome.lower() in response_text.lower():
                    outcome_alignment += 1
                    evidence.append(f"Addresses expected outcome: {outcome}")
            
            if outcome_alignment >= len(expected_outcomes) * 0.8:
                score = 0.9
                evidence.append("Addresses most expected customer outcomes")
            elif outcome_alignment >= 1:
                score = 0.6
                evidence.append("Addresses some expected customer outcomes")
            else:
                score = 0.3
                deficiencies.append("Doesn't clearly address expected customer outcomes")
        else:
            # General customer outcome assessment
            outcome_indicators = ['result', 'outcome', 'achieve', 'goal', 'success', 
                                'benefit', 'value', 'improvement', 'solution']
            outcome_count = sum(1 for indicator in outcome_indicators 
                              if indicator in response_text.lower())
            
            if outcome_count >= 3:
                score = 0.7
                evidence.append(f"Strong outcome focus with {outcome_count} indicators")
            elif outcome_count >= 1:
                score = 0.5
                evidence.append(f"Some outcome focus with {outcome_count} indicators")
        
        customer_impact = self._assess_customer_impact_outcomes(score, evidence)
        
        return BusinessValueScore(
            dimension=BusinessValueDimension.CUSTOMER_OUTCOME,
            score=score,
            evidence=evidence,
            deficiencies=deficiencies,
            customer_impact=customer_impact
        )

    def _evaluate_business_impact(self, response_text: str) -> BusinessValueScore:
        """Evaluate potential business impact of the response."""
        response_lower = response_text.lower()
        
        score = 0.2  # Base score
        evidence = []
        deficiencies = []
        
        # Count business impact indicators
        impact_indicators_found = sum(1 for indicator in self.business_impact_indicators 
                                    if indicator in response_lower)
        
        if impact_indicators_found >= 4:
            score = 0.9
            evidence.append(f"Strong business impact focus with {impact_indicators_found} indicators")
        elif impact_indicators_found >= 2:
            score = 0.6
            evidence.append(f"Good business impact focus with {impact_indicators_found} indicators")
        elif impact_indicators_found >= 1:
            score = 0.4
            evidence.append(f"Some business impact focus with {impact_indicators_found} indicators")
        else:
            deficiencies.append("Limited focus on business impact or strategic value")
        
        customer_impact = self._assess_customer_impact_business(score, evidence)
        
        return BusinessValueScore(
            dimension=BusinessValueDimension.BUSINESS_IMPACT,
            score=score,
            evidence=evidence,
            deficiencies=deficiencies,
            customer_impact=customer_impact
        )

    def _calculate_chat_substance_quality(self, dimension_scores: Dict) -> float:
        """Calculate chat substance quality for Golden Path validation."""
        # Weight problem solving and actionability heavily for chat substance
        problem_solving_score = dimension_scores[BusinessValueDimension.PROBLEM_SOLVING].score
        actionability_score = dimension_scores[BusinessValueDimension.ACTIONABILITY].score
        insight_quality_score = dimension_scores[BusinessValueDimension.INSIGHT_QUALITY].score
        
        return (problem_solving_score * 0.4 + actionability_score * 0.4 + insight_quality_score * 0.2)

    def _calculate_ai_optimization_value(self, dimension_scores: Dict) -> float:
        """Calculate AI optimization value delivered."""
        cost_opt_score = dimension_scores[BusinessValueDimension.COST_OPTIMIZATION].score
        business_impact_score = dimension_scores[BusinessValueDimension.BUSINESS_IMPACT].score
        
        return (cost_opt_score * 0.6 + business_impact_score * 0.4)

    def _calculate_user_goal_achievement(self, dimension_scores: Dict, 
                                       expected_outcomes: Optional[List[str]]) -> float:
        """Calculate user goal achievement score."""
        customer_outcome_score = dimension_scores[BusinessValueDimension.CUSTOMER_OUTCOME].score
        problem_solving_score = dimension_scores[BusinessValueDimension.PROBLEM_SOLVING].score
        
        # If we have expected outcomes, weight customer outcome more heavily
        if expected_outcomes:
            return (customer_outcome_score * 0.7 + problem_solving_score * 0.3)
        else:
            return (customer_outcome_score * 0.5 + problem_solving_score * 0.5)

    def _assess_customer_impact_problem_solving(self, score: float, evidence: List[str]) -> str:
        """Assess customer impact for problem-solving dimension."""
        if score >= 0.8:
            return "Excellent problem-solving that likely resolves customer issues completely"
        elif score >= 0.6:
            return "Good problem-solving approach that should help customer significantly"
        elif score >= 0.4:
            return "Some problem-solving value but may leave customer with additional questions"
        else:
            return "Limited problem-solving value, customer likely still needs help"

    def _assess_customer_impact_actionability(self, score: float, evidence: List[str]) -> str:
        """Assess customer impact for actionability dimension."""
        if score >= 0.8:
            return "Highly actionable recommendations that customer can implement immediately"
        elif score >= 0.6:
            return "Good actionable guidance that customer can likely follow"
        elif score >= 0.4:
            return "Some actionable elements but customer may need additional guidance"
        else:
            return "Limited actionable value, customer may struggle to implement"

    def _assess_customer_impact_cost_optimization(self, score: float, evidence: List[str]) -> str:
        """Assess customer impact for cost optimization dimension."""
        if score >= 0.8:
            return "Strong cost optimization value that could significantly reduce customer expenses"
        elif score >= 0.6:
            return "Good cost optimization insights that should benefit customer financially"
        elif score >= 0.4:
            return "Some cost considerations mentioned but limited optimization value"
        else:
            return "Little to no cost optimization value for customer"

    def _assess_customer_impact_insights(self, score: float, evidence: List[str]) -> str:
        """Assess customer impact for insight quality dimension."""
        if score >= 0.8:
            return "High-quality insights that provide significant strategic value to customer"
        elif score >= 0.6:
            return "Good insights that should help customer understand their situation better"
        elif score >= 0.4:
            return "Some valuable insights but may lack depth or strategic focus"
        else:
            return "Limited insight value, customer may not gain new understanding"

    def _assess_customer_impact_outcomes(self, score: float, evidence: List[str]) -> str:
        """Assess customer impact for customer outcome dimension."""
        if score >= 0.8:
            return "Directly addresses customer outcomes and likely to achieve desired results"
        elif score >= 0.6:
            return "Good alignment with customer outcomes, likely to be helpful"
        elif score >= 0.4:
            return "Some focus on outcomes but may not fully meet customer expectations"
        else:
            return "Limited outcome focus, customer may not achieve desired results"

    def _assess_customer_impact_business(self, score: float, evidence: List[str]) -> str:
        """Assess customer impact for business impact dimension."""
        if score >= 0.8:
            return "Strong business impact potential that could drive significant value for customer"
        elif score >= 0.6:
            return "Good business focus that should provide measurable value to customer"
        elif score >= 0.4:
            return "Some business considerations but limited strategic impact"
        else:
            return "Little business impact focus, may not drive meaningful customer value"

    def _create_failed_assessment(self, reason: str) -> BusinessValueAssessment:
        """Create a failed business value assessment."""
        failed_score = BusinessValueScore(
            dimension=BusinessValueDimension.PROBLEM_SOLVING,  # Dummy dimension
            score=0.0,
            evidence=[],
            deficiencies=[reason],
            customer_impact="No business value - response failed validation"
        )
        
        dimension_scores = {dim: failed_score for dim in BusinessValueDimension}
        
        return BusinessValueAssessment(
            overall_score=0.0,
            dimension_scores=dimension_scores,
            delivers_business_value=False,
            customer_satisfaction_tier="Poor",
            revenue_protection_score=0.0,
            competitive_advantage=False,
            chat_substance_quality=0.0,
            ai_optimization_value=0.0,
            user_goal_achievement=0.0
        )

    def assert_business_value_delivered(
        self, 
        assessment: BusinessValueAssessment, 
        min_score: float = 0.6,
        require_actionability: bool = True,
        require_problem_solving: bool = True
    ):
        """
        Assert that business value was delivered, for use in test cases.
        
        Args:
            assessment: Business value assessment to validate
            min_score: Minimum overall score required (default 0.6)
            require_actionability: Require minimum actionability score
            require_problem_solving: Require minimum problem-solving score
            
        Raises:
            AssertionError: If business value standards are not met
        """
        # Overall business value check
        assert assessment.delivers_business_value, (
            f"Response failed to deliver business value. Overall score: {assessment.overall_score:.2f}, "
            f"Customer satisfaction: {assessment.customer_satisfaction_tier}, "
            f"Revenue protection score: {assessment.revenue_protection_score:.2f}"
        )
        
        assert assessment.overall_score >= min_score, (
            f"Business value score {assessment.overall_score:.2f} below minimum {min_score}. "
            f"Customer satisfaction tier: {assessment.customer_satisfaction_tier}"
        )
        
        # Specific dimension checks
        if require_actionability:
            actionability_score = assessment.dimension_scores[BusinessValueDimension.ACTIONABILITY].score
            assert actionability_score >= 0.5, (
                f"Actionability score {actionability_score:.2f} too low. "
                f"Evidence: {assessment.dimension_scores[BusinessValueDimension.ACTIONABILITY].evidence}"
            )
        
        if require_problem_solving:
            problem_solving_score = assessment.dimension_scores[BusinessValueDimension.PROBLEM_SOLVING].score
            assert problem_solving_score >= 0.5, (
                f"Problem-solving score {problem_solving_score:.2f} too low. "
                f"Evidence: {assessment.dimension_scores[BusinessValueDimension.PROBLEM_SOLVING].evidence}"
            )
        
        # Revenue protection check
        assert assessment.revenue_protection_score >= self.revenue_protection_threshold, (
            f"Revenue protection score {assessment.revenue_protection_score:.2f} below threshold "
            f"{self.revenue_protection_threshold}. This response may not protect $500K+ ARR."
        )
        
        # Golden Path specific checks
        assert assessment.chat_substance_quality >= 0.5, (
            f"Chat substance quality {assessment.chat_substance_quality:.2f} too low for Golden Path. "
            f"Chat must deliver substantive value, not just technical success."
        )

    def generate_business_value_report(self, assessment: BusinessValueAssessment) -> str:
        """Generate a detailed business value report."""
        report_lines = [
            f"=== BUSINESS VALUE ASSESSMENT REPORT ===",
            f"Overall Score: {assessment.overall_score:.2f}/1.0",
            f"Customer Satisfaction Tier: {assessment.customer_satisfaction_tier}",
            f"Delivers Business Value: {'YES' if assessment.delivers_business_value else 'NO'}",
            f"Revenue Protection Score: {assessment.revenue_protection_score:.2f}/1.0",
            f"Competitive Advantage: {'YES' if assessment.competitive_advantage else 'NO'}",
            f"",
            f"=== GOLDEN PATH METRICS ===",
            f"Chat Substance Quality: {assessment.chat_substance_quality:.2f}/1.0",
            f"AI Optimization Value: {assessment.ai_optimization_value:.2f}/1.0", 
            f"User Goal Achievement: {assessment.user_goal_achievement:.2f}/1.0",
            f"",
            f"=== DIMENSION ANALYSIS ==="
        ]
        
        for dimension, score_data in assessment.dimension_scores.items():
            report_lines.extend([
                f"",
                f"{dimension.value.upper()}: {score_data.score:.2f}/1.0",
                f"  Customer Impact: {score_data.customer_impact}",
                f"  Evidence: {'; '.join(score_data.evidence) if score_data.evidence else 'None'}",
                f"  Deficiencies: {'; '.join(score_data.deficiencies) if score_data.deficiencies else 'None'}"
            ])
        
        return "\n".join(report_lines)


# Convenience functions for test integration
def validate_agent_business_value(
    response: Union[str, Dict, Any],
    user_query: str = "",
    expected_outcomes: Optional[List[str]] = None,
    min_score: float = 0.6
) -> BusinessValueAssessment:
    """
    Convenience function to validate business value in tests.
    
    Example usage:
        assessment = validate_agent_business_value(
            response=agent_response,
            user_query="Help me optimize my AI costs",
            expected_outcomes=["cost reduction", "optimization recommendations"],
            min_score=0.7
        )
        assert assessment.delivers_business_value
    """
    validator = BusinessValueValidator()
    assessment = validator.validate_business_value(
        response=response,
        user_query=user_query,
        expected_outcomes=expected_outcomes
    )
    
    # Log assessment for debugging
    logger.info(f"Business value assessment: {assessment.overall_score:.2f} "
               f"({assessment.customer_satisfaction_tier})")
    
    return assessment


def assert_golden_path_business_value(
    response: Union[str, Dict, Any],
    user_query: str = "",
    expected_outcomes: Optional[List[str]] = None,
    min_chat_substance: float = 0.6,
    min_overall_score: float = 0.6
):
    """
    Assert Golden Path business value standards are met.
    
    This function enforces the business requirement that chat functionality
    delivers 90% of platform value through substantive AI interactions.
    
    Example usage:
        assert_golden_path_business_value(
            response=agent_response,
            user_query="Help me with AI cost optimization",
            expected_outcomes=["actionable recommendations", "cost savings"],
            min_chat_substance=0.7
        )
    """
    validator = BusinessValueValidator()
    assessment = validator.validate_business_value(
        response=response,
        user_query=user_query,
        expected_outcomes=expected_outcomes
    )
    
    # Golden Path specific assertions
    assert assessment.chat_substance_quality >= min_chat_substance, (
        f"Chat substance quality {assessment.chat_substance_quality:.2f} below Golden Path "
        f"minimum {min_chat_substance}. Golden Path requires substantive chat value delivery."
    )
    
    assert assessment.overall_score >= min_overall_score, (
        f"Overall business value {assessment.overall_score:.2f} below minimum {min_overall_score}. "
        f"This fails to protect $500K+ ARR through quality AI interactions."
    )
    
    # Use validator's assertion method for comprehensive checks
    validator.assert_business_value_delivered(
        assessment=assessment,
        min_score=min_overall_score,
        require_actionability=True,
        require_problem_solving=True
    )
    
    logger.info(f"✓ Golden Path business value validated: {assessment.customer_satisfaction_tier} "
               f"quality with {assessment.overall_score:.2f} score")
    
    return assessment