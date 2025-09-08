"""
Simple Agent Response Quality Test

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agents deliver high-quality, actionable responses
- Value Impact: Users receive substantive AI solutions meeting quality standards
- Strategic Impact: Core platform value delivery - quality responses drive retention

Simple test to validate quality grading system works correctly.
"""

import pytest
from typing import Dict, Any

from tests.e2e.integration.test_agent_response_quality_grading import AgentResponseQualityGrader


class TestAgentResponseQualitySimple:
    """Simple tests for agent response quality grading system."""
    
    def setup_method(self):
        """Set up test method."""
        self.grader = AgentResponseQualityGrader()
    
    def test_quality_grader_basic_functionality(self):
        """Test that the quality grader basic functionality works."""
        # Test optimization query
        query = "How can I optimize my AWS costs? I'm spending $5000/month."
        response = """To optimize your AWS costs, here are specific recommendations:

1. **Right-size your instances**: Analyze utilization and downsize over-provisioned instances (can save 20-30%)
2. **Use Reserved Instances**: For predictable workloads, commit to 1-3 year terms for 30-60% savings  
3. **Implement Auto Scaling**: Automatically adjust capacity based on demand
4. **Use Spot Instances**: For fault-tolerant workloads, save up to 90%
5. **Set up Cost Monitoring**: CloudWatch alarms when spending exceeds thresholds

**Implementation steps:**
- Start with AWS Cost Explorer to identify highest costs
- Use AWS Trusted Advisor for right-sizing recommendations  
- Configure Auto Scaling groups for your applications

This approach typically achieves 25-35% cost reduction within 30 days."""
        
        scores = self.grader.grade_response(query, response, "optimization")
        
        # Verify score structure
        assert "relevance" in scores
        assert "completeness" in scores  
        assert "actionability" in scores
        assert "overall_quality" in scores
        assert "grading_details" in scores
        
        # Verify scores are in valid range
        assert 0.0 <= scores["relevance"] <= 1.0
        assert 0.0 <= scores["completeness"] <= 1.0
        assert 0.0 <= scores["actionability"] <= 1.0
        assert 0.0 <= scores["overall_quality"] <= 1.0
        
        # This should be a high-quality response
        assert scores["overall_quality"] >= 0.7, f"Quality score {scores['overall_quality']:.3f} below threshold"
        
        print(f"Quality scores: {scores}")
    
    def test_quality_grader_edge_cases(self):
        """Test quality grader handles edge cases correctly."""
        # Empty response
        scores = self.grader.grade_response("Test query", "", "general")
        assert scores["overall_quality"] == 0.0
        
        # Empty query
        scores = self.grader.grade_response("", "Test response", "general")
        assert scores["overall_quality"] == 0.0
        
        # Very short response
        scores = self.grader.grade_response("How to optimize?", "Use tools.", "optimization")
        assert 0.0 <= scores["overall_quality"] <= 1.0
        
        print("Edge case tests passed")
    
    def test_quality_grader_different_agent_types(self):
        """Test quality grader works for different agent types."""
        test_cases = [
            {
                "agent_type": "optimization",
                "query": "How can I reduce cloud costs?",
                "response": "Optimize instance sizes, use reserved instances, implement monitoring for cost savings.",
                "expected_min_quality": 0.4
            },
            {
                "agent_type": "triage", 
                "query": "What should I prioritize in my system?",
                "response": "Analyze performance metrics first, then address high-impact issues based on business priority.",
                "expected_min_quality": 0.4
            },
            {
                "agent_type": "data",
                "query": "Show me database performance trends.",
                "response": "Query response times have increased 15% over last month. Key bottlenecks are in user_data table.",
                "expected_min_quality": 0.4
            }
        ]
        
        for case in test_cases:
            scores = self.grader.grade_response(
                case["query"], 
                case["response"], 
                case["agent_type"]
            )
            
            assert scores["overall_quality"] >= case["expected_min_quality"], (
                f"{case['agent_type']} agent quality {scores['overall_quality']:.3f} "
                f"below minimum {case['expected_min_quality']}"
            )
            
            print(f"{case['agent_type']}: {scores['overall_quality']:.3f}")
    
    def test_quality_dimensions_scoring(self):
        """Test individual quality dimensions are scored correctly."""
        # High relevance response
        query = "What is AWS EC2?"
        response = "AWS EC2 is Amazon's Elastic Compute Cloud service for virtual servers in the cloud."
        
        scores = self.grader.grade_response(query, response, "general")
        
        # Should have good relevance (matches query keywords)
        assert scores["relevance"] > 0.5, f"Expected high relevance, got {scores['relevance']:.3f}"
        
        # Test actionable response
        action_query = "How do I setup monitoring?"
        action_response = """To setup monitoring:
        1. Install CloudWatch agent
        2. Configure metrics collection  
        3. Create dashboards
        4. Set up alerts
        Use these commands: aws cloudwatch put-metric-data"""
        
        action_scores = self.grader.grade_response(action_query, action_response, "general")
        
        # Should have good actionability (steps, commands)
        assert action_scores["actionability"] >= 0.5, f"Expected high actionability, got {action_scores['actionability']:.3f}"
        
        print("Quality dimension tests passed")