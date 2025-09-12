"""Validation script for Agent Response Quality Grading

This script validates that the quality grading system works correctly.
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from tests.e2e.integration.test_agent_response_quality_grading import EnterpriseAgentQualityEvaluator


async def validate_quality_grader():
    """Validate the quality grader functionality."""
    print("\n" + "="*60)
    print("AGENT RESPONSE QUALITY GRADER VALIDATION")
    print("="*60)
    
    grader = EnterpriseAgentQualityEvaluator()
    
    # Test case 1: High-quality optimization response
    print("\n[TEST 1] High-Quality Optimization Response")
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
    
    scores = await grader.evaluate_response_quality(query, response, "optimization")
    
    print(f"  Query: {query[:50]}...")
    print(f"  Response length: {len(response)} chars")
    print(f"\n  Quality Scores:")
    print(f"    Raw result: {scores}")
    
    # Extract the actual scores from the result
    overall_quality = scores.get('overall_quality', 0.0)
    business_value = scores.get('business_value_score', 0.0)
    technical_accuracy = scores.get('technical_accuracy_score', 0.0)
    user_experience = scores.get('user_experience_score', 0.0)
    
    print(f"    - Business Value:    {business_value:.3f}")
    print(f"    - Technical Accuracy: {technical_accuracy:.3f}")
    print(f"    - User Experience:   {user_experience:.3f}")
    print(f"    - Overall Quality:   {overall_quality:.3f}")
    print(f"\n  Meets 0.8 threshold: {'[U+2713] YES' if overall_quality >= 0.8 else '[U+2717] NO'}")
    
    # Test case 2: Low-quality response
    print("\n[TEST 2] Low-Quality Response")
    query2 = "How do I improve performance?"
    response2 = "Make it faster."
    
    scores2 = await grader.evaluate_response_quality(query2, response2, "general")
    
    print(f"  Query: {query2}")
    print(f"  Response: {response2}")
    print(f"\n  Quality Scores:")
    
    overall_quality2 = scores2.get('overall_quality', 0.0)
    business_value2 = scores2.get('business_value_score', 0.0)
    technical_accuracy2 = scores2.get('technical_accuracy_score', 0.0)
    user_experience2 = scores2.get('user_experience_score', 0.0)
    
    print(f"    - Business Value:    {business_value2:.3f}")
    print(f"    - Technical Accuracy: {technical_accuracy2:.3f}")
    print(f"    - User Experience:   {user_experience2:.3f}")
    print(f"    - Overall Quality:   {overall_quality2:.3f}")
    print(f"\n  Meets 0.8 threshold: {'[U+2713] YES' if overall_quality2 >= 0.8 else '[U+2717] NO'}")
    
    # Test case 3: Different agent types
    print("\n[TEST 3] Different Agent Types")
    test_cases = [
        ("triage", "What's wrong with my system?", "Check CPU usage, memory leaks, and database connections."),
        ("data", "Show me metrics", "CPU: 85%, Memory: 2GB/4GB, Requests: 1000/min"),
        ("optimization", "Optimize this", "Reduce complexity, cache results, use indexes")
    ]
    
    for agent_type, q, r in test_cases:
        s = await grader.evaluate_response_quality(q, r, agent_type)
        print(f"  {agent_type.upper():12} - Quality: {s['overall_quality']:.3f}")
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    if overall_quality >= 0.8:
        print("[U+2713] Quality grader correctly identifies high-quality responses")
    else:
        print("[U+2717] Quality grader failed to identify high-quality response")
    
    if overall_quality2 < 0.8:
        print("[U+2713] Quality grader correctly identifies low-quality responses")
    else:
        print("[U+2717] Quality grader failed to identify low-quality response")
    
    print("\n[U+2713] Quality grading system is operational")
    print("="*60 + "\n")
    
    return overall_quality >= 0.8 and overall_quality2 < 0.8


if __name__ == "__main__":
    success = asyncio.run(validate_quality_grader())
    sys.exit(0 if success else 1)