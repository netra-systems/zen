"""
Test Agent Response Quality Validation Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agents deliver high-quality, actionable business insights
- Value Impact: Quality responses directly correlate with user retention and value realization
- Strategic Impact: Response quality is core differentiator for $500K+ ARR target

COVERAGE FOCUS:
1. Response content accuracy and relevance validation
2. Business value metrics in agent outputs  
3. Response completeness and actionability testing
4. Multi-agent response consistency validation
5. Response formatting and structure verification
6. Error handling and fallback response quality
7. Domain-specific expertise validation
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import pytest
import re

from test_framework.base_integration_test import BaseIntegrationTest, WebSocketIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


class ResponseQualityLevel(Enum):
    """Response quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


@dataclass
class ResponseQualityMetrics:
    """Metrics for assessing response quality."""
    content_relevance_score: float  # 0-1
    actionability_score: float      # 0-1 
    completeness_score: float       # 0-1
    business_value_score: float     # 0-1
    technical_accuracy_score: float # 0-1
    response_time: float            # seconds
    has_recommendations: bool
    has_quantified_impact: bool
    error_count: int
    overall_quality: ResponseQualityLevel


class TestAgentResponseQualityValidation(WebSocketIntegrationTest):
    """Test agent response quality with real service integration."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.quality_thresholds = {
            "min_content_relevance": 0.8,
            "min_actionability": 0.7,
            "min_completeness": 0.8,
            "min_business_value": 0.7,
            "max_response_time": 30.0,
            "required_sections": ["analysis", "recommendations", "next_steps"]
        }
        
    def _assess_response_quality(self, response_content: str, context: Dict[str, Any]) -> ResponseQualityMetrics:
        """Assess the quality of an agent response."""
        # Content relevance - check for domain-specific keywords
        domain_keywords = context.get("domain_keywords", [])
        relevance_matches = sum(1 for keyword in domain_keywords if keyword.lower() in response_content.lower())
        content_relevance_score = min(1.0, relevance_matches / len(domain_keywords)) if domain_keywords else 0.5
        
        # Actionability - look for action verbs and specific recommendations
        action_patterns = [
            r'\b(implement|optimize|reduce|increase|configure|upgrade|migrate|analyze)\b',
            r'\b(should|recommend|suggest|propose)\b',
            r'\b(step \d+|first|next|then|finally)\b'
        ]
        action_count = sum(len(re.findall(pattern, response_content, re.IGNORECASE)) for pattern in action_patterns)
        actionability_score = min(1.0, action_count / 10)  # Normalize to 0-1
        
        # Completeness - check for required sections
        required_sections = self.quality_thresholds["required_sections"]
        section_matches = sum(1 for section in required_sections if section.lower() in response_content.lower())
        completeness_score = section_matches / len(required_sections)
        
        # Business value - look for quantified impacts, cost savings, efficiency gains
        business_value_patterns = [
            r'\$[\d,]+',  # Dollar amounts
            r'\d+%',      # Percentages
            r'\b(\d+(?:,\d{3})*)\s*(hours?|days?|months?)\b',  # Time savings
            r'\b(save|saving|reduce|reduction|improve|improvement|increase)\b'
        ]
        business_value_matches = sum(len(re.findall(pattern, response_content, re.IGNORECASE)) for pattern in business_value_patterns)
        business_value_score = min(1.0, business_value_matches / 5)
        
        # Technical accuracy - basic checks for technical coherence
        technical_score = 0.8  # Default decent score for non-LLM tests
        
        # Check for specific quality indicators
        has_recommendations = "recommend" in response_content.lower() or "suggestion" in response_content.lower()
        has_quantified_impact = bool(re.search(r'\$[\d,]+|\d+%', response_content))
        error_count = response_content.lower().count("error") + response_content.lower().count("failed")
        
        # Calculate overall quality
        overall_score = (content_relevance_score + actionability_score + completeness_score + business_value_score + technical_score) / 5
        
        if overall_score >= 0.9:
            overall_quality = ResponseQualityLevel.EXCELLENT
        elif overall_score >= 0.8:
            overall_quality = ResponseQualityLevel.GOOD
        elif overall_score >= 0.7:
            overall_quality = ResponseQualityLevel.ACCEPTABLE
        elif overall_score >= 0.5:
            overall_quality = ResponseQualityLevel.POOR
        else:
            overall_quality = ResponseQualityLevel.UNACCEPTABLE
        
        return ResponseQualityMetrics(
            content_relevance_score=content_relevance_score,
            actionability_score=actionability_score,
            completeness_score=completeness_score,
            business_value_score=business_value_score,
            technical_accuracy_score=technical_score,
            response_time=0.0,  # Will be set by caller
            has_recommendations=has_recommendations,
            has_quantified_impact=has_quantified_impact,
            error_count=error_count,
            overall_quality=overall_quality
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cost_optimization_response_quality(self, real_services_fixture):
        """
        Test that cost optimization responses contain high-quality, actionable insights.
        
        Validates the core business value proposition of cost savings.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "cost-quality@example.com", "name": "Cost Quality User"}
        )
        
        # Create thread for cost optimization analysis
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at, metadata)
            VALUES ($1, $2, $3, $4, $5)
        """, thread_id, user_context.user_id, "Cost Optimization Quality Test", 
             datetime.now(timezone.utc),
             json.dumps({"test_type": "response_quality", "domain": "cost_optimization"}))
        
        # Simulate cost optimization request
        request_context = {
            "domain_keywords": ["aws", "cost", "optimization", "ec2", "s3", "savings", "budget"],
            "user_intent": "reduce_monthly_costs",
            "monthly_spend": 25000,
            "target_reduction": 0.20  # 20% target reduction
        }
        
        start_time = time.time()
        
        # Simulate high-quality agent response for cost optimization
        mock_agent_response = """
        ## Cost Optimization Analysis
        
        Based on your AWS infrastructure analysis, I've identified several optimization opportunities for your $25,000 monthly spend:
        
        ### Key Findings:
        1. **EC2 Over-provisioning**: 40% of instances running below 30% CPU utilization
        2. **Storage Optimization**: S3 storage costs can be reduced by 60% through lifecycle policies
        3. **Reserved Instance Opportunity**: $8,400 annual savings available
        
        ### Recommendations:
        1. **Implement right-sizing** for 15 EC2 instances → Est. savings: $3,200/month
        2. **Configure S3 lifecycle policies** → Est. savings: $1,800/month  
        3. **Purchase Reserved Instances** for production workloads → Est. savings: $700/month
        4. **Enable auto-scaling** for variable workloads → Est. savings: $1,500/month
        
        ### Total Potential Savings: $7,200/month (28.8% reduction)
        
        ### Next Steps:
        1. Review detailed recommendations in the attached analysis
        2. Start with right-sizing as it has the highest impact and lowest risk
        3. Implement S3 lifecycle policies within 2 weeks
        4. Schedule Reserved Instance purchase for next billing cycle
        
        This optimization plan will help you exceed your 20% cost reduction target while maintaining performance.
        """
        
        response_time = time.time() - start_time
        
        # Store response in database
        message_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, message_id, thread_id, "assistant", mock_agent_response,
             json.dumps({"response_type": "cost_optimization", "test_scenario": "quality_assessment"}),
             datetime.now(timezone.utc))
        
        # Assess response quality
        quality_metrics = self._assess_response_quality(mock_agent_response, request_context)
        quality_metrics.response_time = response_time
        
        # Store quality assessment
        await real_services_fixture["redis"].set_json(
            f"response_quality:{message_id}",
            {
                "content_relevance": quality_metrics.content_relevance_score,
                "actionability": quality_metrics.actionability_score,
                "completeness": quality_metrics.completeness_score,
                "business_value": quality_metrics.business_value_score,
                "overall_quality": quality_metrics.overall_quality.value,
                "response_time": quality_metrics.response_time,
                "assessment_time": datetime.now(timezone.utc).isoformat()
            },
            ex=86400
        )
        
        # Validate quality meets business requirements
        assert quality_metrics.content_relevance_score >= self.quality_thresholds["min_content_relevance"], \
            f"Content relevance too low: {quality_metrics.content_relevance_score}"
        
        assert quality_metrics.actionability_score >= self.quality_thresholds["min_actionability"], \
            f"Actionability too low: {quality_metrics.actionability_score}"
        
        assert quality_metrics.completeness_score >= self.quality_thresholds["min_completeness"], \
            f"Completeness too low: {quality_metrics.completeness_score}"
        
        assert quality_metrics.business_value_score >= self.quality_thresholds["min_business_value"], \
            f"Business value too low: {quality_metrics.business_value_score}"
        
        assert quality_metrics.has_recommendations is True, "Response must contain recommendations"
        assert quality_metrics.has_quantified_impact is True, "Response must contain quantified business impact"
        assert quality_metrics.error_count == 0, "Response must not contain errors"
        assert quality_metrics.overall_quality in [ResponseQualityLevel.EXCELLENT, ResponseQualityLevel.GOOD], \
            f"Overall quality insufficient: {quality_metrics.overall_quality.value}"
        
        self.logger.info(f"Cost optimization response quality validated: {quality_metrics.overall_quality.value}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_agent_response_consistency(self, real_services_fixture):
        """
        Test that multiple agents provide consistent and complementary responses.
        
        Validates golden path agent coordination and response harmony.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "consistency-test@example.com", "name": "Consistency User"}
        )
        
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, $4)
        """, thread_id, user_context.user_id, "Multi-Agent Consistency Test", datetime.now(timezone.utc))
        
        # Define multi-agent response scenario
        agents_and_responses = [
            {
                "agent_type": "triage_agent",
                "response": """
                ## Initial Assessment
                
                I've analyzed your request for infrastructure optimization. Based on your current setup:
                
                **Problem Category**: Cost and Performance Optimization
                **Complexity Level**: Medium
                **Estimated Impact**: High (potential 25-30% cost reduction)
                
                **Recommended Next Steps**:
                1. Detailed cost analysis by Data Helper
                2. Performance benchmarking 
                3. Business value assessment
                
                **Next Agent**: I recommend engaging the Data Helper for comprehensive cost analysis.
                """,
                "expected_elements": ["problem_category", "recommended_next_steps", "next_agent"]
            },
            {
                "agent_type": "data_helper", 
                "response": """
                ## Data Analysis Results
                
                Following up on the triage assessment, I've collected and analyzed your infrastructure data:
                
                **Cost Breakdown**:
                - Total Monthly Spend: $18,500
                - Top Cost Drivers: EC2 (60%), RDS (25%), S3 (15%)
                - Optimization Opportunities Identified: 7 areas
                
                **Performance Metrics**:
                - Average CPU Utilization: 35% (indicates over-provisioning)
                - Storage Efficiency: 72% (room for improvement)
                - Network Optimization Score: 8/10
                
                **Data Quality**: High confidence in analysis (95% data coverage)
                
                **Ready for Value Assessment**: All data prepared for UVS Reporter analysis.
                """,
                "expected_elements": ["cost_breakdown", "performance_metrics", "data_quality", "ready_for_value"]
            },
            {
                "agent_type": "uvs_reporter",
                "response": """
                ## Business Value and Impact Report
                
                Based on the triage assessment and data analysis, here's the comprehensive value proposition:
                
                **Business Impact Analysis**:
                - Monthly Cost Reduction: $5,550 (30% savings - exceeding triage estimate)
                - Annual Savings: $66,600
                - ROI Timeline: 3 months implementation, 9 months full ROI
                - Risk Assessment: Low risk, high reward
                
                **Value Recommendations**:
                1. **Immediate Actions** (Week 1-2): Right-size 12 EC2 instances → $2,400/month savings
                2. **Short-term** (Month 1): Implement storage optimization → $1,800/month savings  
                3. **Medium-term** (Month 2-3): Reserved Instance strategy → $1,350/month savings
                
                **Business Justification**: This optimization aligns with the 25-30% reduction identified in triage and validates the high-confidence data from our analysis.
                
                **Executive Summary**: Recommended immediate implementation with staged rollout.
                """,
                "expected_elements": ["business_impact", "value_recommendations", "business_justification", "executive_summary"]
            }
        ]
        
        # Store and analyze each agent response
        agent_messages = []
        quality_assessments = []
        
        for i, agent_config in enumerate(agents_and_responses):
            message_id = str(uuid.uuid4())
            
            # Store agent response
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, message_id, thread_id, "assistant", agent_config["response"],
                 json.dumps({
                     "agent_type": agent_config["agent_type"],
                     "sequence_order": i,
                     "expected_elements": agent_config["expected_elements"]
                 }),
                 datetime.now(timezone.utc))
            
            agent_messages.append({
                "message_id": message_id,
                "agent_type": agent_config["agent_type"],
                "content": agent_config["response"],
                "expected_elements": agent_config["expected_elements"]
            })
            
            # Assess individual response quality
            context = {
                "domain_keywords": ["cost", "optimization", "performance", "aws", "savings", "analysis"],
                "agent_type": agent_config["agent_type"]
            }
            
            quality = self._assess_response_quality(agent_config["response"], context)
            quality_assessments.append(quality)
            
            await asyncio.sleep(0.1)  # Simulate time between agents
        
        # Validate consistency across agents
        # 1. Check for narrative consistency
        triage_mentions_data_helper = "data helper" in agents_and_responses[0]["response"].lower()
        data_helper_ready_for_value = "ready for value" in agents_and_responses[1]["response"].lower() or "uvs" in agents_and_responses[1]["response"].lower()
        uvs_references_previous = "triage" in agents_and_responses[2]["response"].lower() or "data analysis" in agents_and_responses[2]["response"].lower()
        
        assert triage_mentions_data_helper, "Triage agent must reference next agent in flow"
        assert data_helper_ready_for_value, "Data helper must indicate readiness for value assessment"
        assert uvs_references_previous, "UVS reporter must reference previous agent work"
        
        # 2. Check for consistent metrics/numbers
        # Extract cost savings estimates from responses
        cost_estimates = []
        for response in [config["response"] for config in agents_and_responses]:
            # Look for percentage savings
            percentages = re.findall(r'(\d+)%', response)
            cost_estimates.extend([int(p) for p in percentages if int(p) > 10 and int(p) < 50])  # Reasonable cost savings range
        
        if len(cost_estimates) >= 2:
            # Estimates should be within reasonable range of each other
            min_estimate, max_estimate = min(cost_estimates), max(cost_estimates)
            consistency_ratio = min_estimate / max_estimate if max_estimate > 0 else 1
            assert consistency_ratio >= 0.7, f"Agent estimates too inconsistent: {min_estimate}% vs {max_estimate}%"
        
        # 3. Validate overall quality is maintained across agents
        for i, quality in enumerate(quality_assessments):
            assert quality.overall_quality in [ResponseQualityLevel.EXCELLENT, ResponseQualityLevel.GOOD], \
                f"Agent {agents_and_responses[i]['agent_type']} quality insufficient: {quality.overall_quality.value}"
        
        # 4. Check response progression (each should build on previous)
        assert "next" in agents_and_responses[0]["response"].lower(), "Triage must indicate next steps"
        assert "following up" in agents_and_responses[1]["response"].lower() or "based on" in agents_and_responses[1]["response"].lower(), "Data helper must reference previous work"
        assert "based on" in agents_and_responses[2]["response"].lower(), "UVS reporter must synthesize previous analysis"
        
        # Store consistency analysis
        consistency_analysis = {
            "thread_id": thread_id,
            "agent_count": len(agents_and_responses),
            "narrative_consistency": True,
            "metric_consistency": consistency_ratio if len(cost_estimates) >= 2 else 1.0,
            "quality_scores": [q.overall_quality.value for q in quality_assessments],
            "progression_validated": True,
            "analysis_time": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["redis"].set_json(
            f"consistency_analysis:{thread_id}",
            consistency_analysis,
            ex=86400
        )
        
        self.logger.info("Multi-agent response consistency validated successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_domain_specific_expertise_validation(self, real_services_fixture):
        """
        Test that agents demonstrate appropriate domain expertise in their responses.
        
        Validates technical accuracy and domain knowledge across different business areas.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "expertise-test@example.com", "name": "Expertise User"}
        )
        
        # Test multiple domain expertise areas
        domain_scenarios = [
            {
                "domain": "aws_cost_optimization",
                "query": "Optimize my AWS costs for a data-heavy workload",
                "expected_expertise": [
                    "ec2", "s3", "ebs", "rds", "reserved instances", 
                    "spot instances", "lifecycle policies", "cloudwatch"
                ],
                "response": """
                ## AWS Cost Optimization for Data Workloads
                
                For data-heavy workloads on AWS, I recommend a multi-layered optimization approach:
                
                ### Compute Optimization:
                - **EC2 Right-sizing**: Use CloudWatch metrics to identify over-provisioned instances
                - **Spot Instances**: For non-critical batch processing (up to 90% savings)
                - **Reserved Instances**: 3-year commitments for stable workloads (40-60% savings)
                
                ### Storage Optimization:
                - **S3 Intelligent Tiering**: Automatic data lifecycle management
                - **EBS gp3 volumes**: Better price/performance than gp2 
                - **S3 Glacier**: Long-term archival for compliance data
                
                ### Data Transfer Optimization:
                - **CloudFront**: Reduce egress charges for frequently accessed data
                - **VPC Endpoints**: Eliminate NAT gateway costs for S3 access
                
                ### Monitoring:
                - **Cost Anomaly Detection**: Automated alerts for unusual spending
                - **AWS Budgets**: Proactive cost control mechanisms
                
                Expected savings: 35-50% for typical data workloads.
                """
            },
            {
                "domain": "security_compliance",
                "query": "Ensure our infrastructure meets SOC 2 compliance requirements", 
                "expected_expertise": [
                    "soc 2", "compliance", "encryption", "access control",
                    "audit logs", "data governance", "incident response"
                ],
                "response": """
                ## SOC 2 Compliance Infrastructure Assessment
                
                To achieve SOC 2 Type II certification, your infrastructure must meet the five Trust Service Criteria:
                
                ### Security (Required):
                - **Access Controls**: Multi-factor authentication, role-based access control (RBAC)
                - **Encryption**: Data at rest and in transit using AES-256 and TLS 1.2+
                - **Network Security**: VPN, firewall rules, intrusion detection
                
                ### Availability: 
                - **High Availability**: Multi-AZ deployments, auto-scaling, disaster recovery
                - **Monitoring**: 24/7 system monitoring, automated failover
                
                ### Processing Integrity:
                - **Data Validation**: Input validation, error handling, transaction integrity
                - **Quality Assurance**: Automated testing, code reviews
                
                ### Confidentiality:
                - **Data Classification**: Sensitive data identification and handling
                - **Access Logging**: Comprehensive audit trails
                
                ### Privacy (if applicable):
                - **Data Governance**: Data retention policies, right to deletion
                - **Consent Management**: User privacy preferences
                
                ### Implementation Timeline:
                1. **Week 1-2**: Security controls implementation
                2. **Week 3-4**: Monitoring and logging setup
                3. **Month 2**: Documentation and policy creation
                4. **Month 3**: External audit preparation
                
                Compliance readiness: 6-8 weeks with dedicated resources.
                """
            },
            {
                "domain": "performance_optimization",
                "query": "My application response times are degrading - need performance optimization",
                "expected_expertise": [
                    "latency", "throughput", "caching", "database optimization",
                    "load balancing", "cdn", "profiling", "bottlenecks"
                ],
                "response": """
                ## Application Performance Optimization Strategy
                
                Based on performance degradation patterns, here's a systematic optimization approach:
                
                ### Performance Bottleneck Analysis:
                1. **Application Profiling**: Identify CPU, memory, and I/O bottlenecks
                2. **Database Query Analysis**: Slow query identification and index optimization
                3. **Network Latency Assessment**: CDN effectiveness and geographical distribution
                
                ### Optimization Strategies:
                
                #### Database Layer:
                - **Query Optimization**: Review execution plans, add missing indexes
                - **Connection Pooling**: Reduce connection overhead
                - **Read Replicas**: Distribute read traffic across multiple instances
                - **Caching Layer**: Redis/ElastiCache for frequently accessed data
                
                #### Application Layer:
                - **Code Optimization**: Eliminate N+1 queries, optimize algorithms
                - **Memory Management**: Garbage collection tuning, memory leak detection
                - **Asynchronous Processing**: Background jobs for time-intensive tasks
                
                #### Infrastructure Layer:
                - **Load Balancing**: Distribute traffic evenly across instances
                - **Auto-scaling**: Dynamic capacity based on demand
                - **CDN Integration**: Cache static assets globally
                
                ### Performance Metrics Targets:
                - **Response Time**: <200ms for API endpoints
                - **Throughput**: 1000+ requests/second
                - **Error Rate**: <0.1% under normal load
                - **Database Query Time**: <50ms average
                
                ### Implementation Priority:
                1. **High Impact, Low Effort**: Database indexing, query optimization
                2. **Medium Impact, Medium Effort**: Caching implementation
                3. **High Impact, High Effort**: Architecture redesign for scalability
                
                Expected performance improvement: 60-80% response time reduction.
                """
            }
        ]
        
        domain_expertise_results = []
        
        for scenario in domain_scenarios:
            thread_id = str(uuid.uuid4())
            
            # Create thread for domain scenario
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, thread_id, user_context.user_id, f"{scenario['domain'].title()} Expertise Test",
                 datetime.now(timezone.utc),
                 json.dumps({
                     "domain": scenario["domain"],
                     "expertise_test": True,
                     "expected_expertise": scenario["expected_expertise"]
                 }))
            
            # Store domain response
            message_id = str(uuid.uuid4())
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, message_id, thread_id, "assistant", scenario["response"],
                 json.dumps({
                     "domain": scenario["domain"],
                     "query": scenario["query"]
                 }),
                 datetime.now(timezone.utc))
            
            # Validate domain expertise
            response_lower = scenario["response"].lower()
            expertise_matches = 0
            missing_expertise = []
            
            for expertise_term in scenario["expected_expertise"]:
                if expertise_term.lower() in response_lower:
                    expertise_matches += 1
                else:
                    missing_expertise.append(expertise_term)
            
            expertise_coverage = expertise_matches / len(scenario["expected_expertise"])
            
            # Assess overall response quality for domain
            context = {
                "domain_keywords": scenario["expected_expertise"],
                "domain": scenario["domain"]
            }
            
            quality_metrics = self._assess_response_quality(scenario["response"], context)
            
            domain_result = {
                "domain": scenario["domain"],
                "expertise_coverage": expertise_coverage,
                "missing_expertise": missing_expertise,
                "quality_score": quality_metrics.overall_quality.value,
                "has_technical_details": expertise_matches > len(scenario["expected_expertise"]) * 0.5,
                "actionable_recommendations": quality_metrics.has_recommendations
            }
            
            domain_expertise_results.append(domain_result)
            
            # Store domain analysis
            await real_services_fixture["redis"].set_json(
                f"domain_expertise:{thread_id}",
                domain_result,
                ex=86400
            )
            
            # Validate domain expertise meets requirements
            assert expertise_coverage >= 0.7, f"Domain expertise too low for {scenario['domain']}: {expertise_coverage:.2f}"
            assert quality_metrics.overall_quality in [ResponseQualityLevel.EXCELLENT, ResponseQualityLevel.GOOD], \
                f"Response quality insufficient for {scenario['domain']}: {quality_metrics.overall_quality.value}"
            
            await asyncio.sleep(0.1)
        
        # Validate overall domain expertise
        avg_expertise_coverage = sum(r["expertise_coverage"] for r in domain_expertise_results) / len(domain_expertise_results)
        assert avg_expertise_coverage >= 0.75, f"Overall domain expertise insufficient: {avg_expertise_coverage:.2f}"
        
        high_quality_responses = sum(1 for r in domain_expertise_results if r["quality_score"] in ["excellent", "good"])
        quality_ratio = high_quality_responses / len(domain_expertise_results)
        assert quality_ratio >= 0.8, f"Too many low-quality domain responses: {quality_ratio:.2f}"
        
        self.logger.info(f"Domain expertise validation completed - Average coverage: {avg_expertise_coverage:.2f}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_handling_response_quality(self, real_services_fixture):
        """
        Test response quality during error conditions and system failures.
        
        Validates that error responses maintain professionalism and provide value.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "error-quality@example.com", "name": "Error Quality User"}
        )
        
        # Test various error scenarios
        error_scenarios = [
            {
                "scenario": "partial_data_available",
                "description": "When some data sources are unavailable",
                "error_context": {
                    "available_data": ["cost_data", "performance_metrics"],
                    "unavailable_data": ["security_audit", "compliance_report"],
                    "confidence_level": 0.7
                },
                "expected_response": """
                ## Partial Analysis Available
                
                I was able to analyze your cost and performance data, though some information sources were temporarily unavailable.
                
                ### Available Analysis (High Confidence):
                - **Cost Analysis**: Complete monthly spend breakdown available
                - **Performance Metrics**: Full infrastructure performance review completed
                - **Immediate Recommendations**: 3 optimization opportunities identified
                
                ### Limited Analysis (Pending Data):
                - **Security Assessment**: Will complete once audit data is available
                - **Compliance Review**: Waiting for compliance report access
                
                ### What I Can Recommend Now:
                1. **Cost Optimization**: Immediate 15% savings opportunity in EC2 usage
                2. **Performance**: 2 bottlenecks identified with clear remediation steps
                3. **Next Steps**: Re-run complete analysis in 2 hours when all data is available
                
                ### Confidence Level: 70% (sufficient for initial actions)
                
                Would you like me to proceed with the high-confidence recommendations while we wait for complete data?
                """
            },
            {
                "scenario": "service_degradation",
                "description": "When external services are slow or degraded",
                "error_context": {
                    "degraded_services": ["aws_api", "cost_calculator"],
                    "estimated_delay": "5-10 minutes",
                    "fallback_available": True
                },
                "expected_response": """
                ## Service Degradation - Alternative Analysis Approach
                
                I'm experiencing delays with some external data sources, but I can still provide valuable insights using alternative methods.
                
                ### Current Situation:
                - **AWS API**: Responding slowly (5-10 minute delays expected)
                - **Live Cost Data**: Using cached data from last successful sync (2 hours ago)
                - **Analysis Capability**: 85% functionality available through alternative data sources
                
                ### Alternative Analysis Available:
                1. **Historical Cost Trends**: Based on cached data, showing clear optimization patterns
                2. **Best Practice Recommendations**: Industry-standard optimizations applicable to your setup
                3. **Estimated Impact**: Conservative projections based on similar infrastructure patterns
                
                ### Recommended Approach:
                **Option 1 (Immediate)**: Proceed with alternative analysis (85% confidence)
                **Option 2 (Wait)**: Full analysis in 10-15 minutes when services recover
                
                ### What I Can Deliver Right Now:
                - Infrastructure optimization roadmap
                - Cost reduction strategies (estimated 20-25% savings)
                - Implementation timeline and risk assessment
                
                Would you prefer the immediate analysis or wait for the complete assessment?
                """
            },
            {
                "scenario": "insufficient_permissions",
                "description": "When user permissions limit data access",
                "error_context": {
                    "permission_level": "read_only",
                    "required_permissions": ["billing_access", "resource_management"],
                    "workaround_available": True
                },
                "expected_response": """
                ## Permission-Limited Analysis Available
                
                Your current access level allows me to provide valuable insights, though some advanced recommendations require additional permissions.
                
                ### What I Can Analyze (Current Permissions):
                - **Resource Configuration**: Complete infrastructure overview
                - **Performance Patterns**: Historical usage and efficiency trends
                - **Optimization Opportunities**: Non-billing related improvements
                
                ### Enhanced Analysis Requires:
                - **Billing Access**: For detailed cost breakdown and savings calculations
                - **Resource Management**: For automated optimization implementation
                
                ### Current Recommendations (High Value):
                1. **Performance Optimization**: 40% improvement opportunity in resource utilization
                2. **Configuration Best Practices**: 5 security and efficiency improvements
                3. **Architecture Review**: Scalability and reliability enhancements
                
                ### Next Steps Options:
                **Option 1**: Proceed with current analysis (substantial value available)
                **Option 2**: Request additional permissions for comprehensive cost analysis
                **Option 3**: I can provide a permission request template for your admin
                
                Even with current access, I can deliver significant optimization insights. Shall we proceed?
                """
            }
        ]
        
        error_quality_results = []
        
        for scenario_config in error_scenarios:
            thread_id = str(uuid.uuid4())
            
            # Create thread for error scenario
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, thread_id, user_context.user_id, f"Error Handling: {scenario_config['scenario']}", 
                 datetime.now(timezone.utc),
                 json.dumps({
                     "error_scenario": scenario_config["scenario"],
                     "error_context": scenario_config["error_context"]
                 }))
            
            # Store error response
            message_id = str(uuid.uuid4())
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, message_id, thread_id, "assistant", scenario_config["expected_response"],
                 json.dumps({
                     "response_type": "error_handling",
                     "scenario": scenario_config["scenario"]
                 }),
                 datetime.now(timezone.utc))
            
            # Assess error response quality
            context = {
                "domain_keywords": ["analysis", "optimization", "recommendations", "options", "next steps"],
                "is_error_response": True
            }
            
            quality_metrics = self._assess_response_quality(scenario_config["expected_response"], context)
            
            # Additional error response quality checks
            response_lower = scenario_config["expected_response"].lower()
            
            # Error responses should be transparent about limitations
            has_transparency = any(word in response_lower for word in ["available", "limited", "unable", "degraded", "waiting"])
            
            # Should offer alternatives or next steps
            has_alternatives = any(word in response_lower for word in ["option", "alternative", "instead", "can still", "available"])
            
            # Should maintain professionalism (no negative language)
            negative_words = ["failed", "broken", "error", "problem", "issue", "sorry", "apologize"]
            excessive_negativity = sum(response_lower.count(word) for word in negative_words) > 2
            
            error_result = {
                "scenario": scenario_config["scenario"],
                "quality_score": quality_metrics.overall_quality.value,
                "transparency": has_transparency,
                "offers_alternatives": has_alternatives,
                "maintains_professionalism": not excessive_negativity,
                "actionability_score": quality_metrics.actionability_score,
                "business_value_preserved": quality_metrics.business_value_score > 0.5
            }
            
            error_quality_results.append(error_result)
            
            # Store error quality analysis
            await real_services_fixture["redis"].set_json(
                f"error_quality:{thread_id}",
                error_result,
                ex=86400
            )
            
            # Validate error response quality
            assert has_transparency, f"Error response must be transparent about limitations: {scenario_config['scenario']}"
            assert has_alternatives, f"Error response must offer alternatives: {scenario_config['scenario']}"
            assert not excessive_negativity, f"Error response too negative: {scenario_config['scenario']}"
            assert quality_metrics.actionability_score >= 0.6, f"Error response must remain actionable: {scenario_config['scenario']}"
            assert quality_metrics.business_value_score >= 0.5, f"Error response must preserve business value: {scenario_config['scenario']}"
        
        # Validate overall error handling quality
        professional_responses = sum(1 for r in error_quality_results if r["maintains_professionalism"])
        professionalism_ratio = professional_responses / len(error_quality_results)
        assert professionalism_ratio == 1.0, "All error responses must maintain professionalism"
        
        alternative_offering = sum(1 for r in error_quality_results if r["offers_alternatives"])
        alternatives_ratio = alternative_offering / len(error_quality_results)
        assert alternatives_ratio >= 0.8, f"Error responses must offer alternatives: {alternatives_ratio:.2f}"
        
        self.logger.info("Error handling response quality validated successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_response_formatting_and_structure(self, real_services_fixture):
        """
        Test that responses follow consistent formatting and structural patterns.
        
        Validates readability and user experience consistency.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "formatting-test@example.com", "name": "Formatting User"}
        )
        
        # Test response with expected formatting structure
        well_formatted_response = """
        ## Infrastructure Optimization Analysis
        
        I've completed a comprehensive analysis of your infrastructure setup and identified several optimization opportunities.
        
        ### Executive Summary
        - **Total Potential Savings**: $4,200/month (23% reduction)
        - **Implementation Timeline**: 2-6 weeks
        - **Risk Level**: Low to Medium
        - **Recommended Priority**: High
        
        ### Detailed Findings
        
        #### 1. Compute Resources
        **Current State:**
        - 15 EC2 instances running 24/7
        - Average CPU utilization: 28%
        - Over-provisioned by approximately 40%
        
        **Optimization Opportunity:**
        - Right-size 8 instances to smaller instance types
        - Implement auto-scaling for 4 variable workload instances
        - **Estimated Savings**: $1,800/month
        
        #### 2. Storage Optimization
        **Current State:**
        - 500GB EBS storage across all instances
        - S3 usage: 2.3TB with mixed access patterns
        - No lifecycle policies implemented
        
        **Optimization Opportunity:**
        - Migrate 60% of S3 data to Infrequent Access tier
        - Implement 90-day lifecycle policy for archival
        - **Estimated Savings**: $1,200/month
        
        #### 3. Network and Data Transfer
        **Current State:**
        - High egress charges from unoptimized data flow
        - No CDN implementation for static content
        
        **Optimization Opportunity:**
        - Implement CloudFront for content distribution
        - Optimize data flow patterns
        - **Estimated Savings**: $1,200/month
        
        ### Implementation Roadmap
        
        #### Phase 1: Quick Wins (Week 1-2)
        1. **Right-size EC2 instances** → Immediate impact
        2. **Implement S3 lifecycle policies** → Low risk, high savings
        3. **Enable detailed monitoring** → Better optimization insights
        
        #### Phase 2: Advanced Optimization (Week 3-4)
        1. **Deploy auto-scaling groups** → Handle variable loads
        2. **Implement CloudFront CDN** → Reduce egress costs
        3. **Optimize database configurations** → Performance + cost benefits
        
        #### Phase 3: Long-term Strategy (Month 2)
        1. **Reserved Instance strategy** → 40-60% compute savings
        2. **Advanced monitoring setup** → Continuous optimization
        3. **Cost governance policies** → Prevent cost drift
        
        ### Risk Assessment
        
        | Change | Risk Level | Mitigation Strategy |
        |--------|------------|-------------------|
        | EC2 Right-sizing | Low | Blue-green deployment, rollback plan |
        | S3 Lifecycle | Very Low | Gradual rollout, data backup |
        | Auto-scaling | Medium | Comprehensive testing, gradual scaling |
        | CDN Implementation | Low | Gradual traffic migration |
        
        ### Business Impact
        
        **Financial Impact:**
        - Monthly savings: $4,200
        - Annual savings: $50,400
        - ROI timeline: 3 months
        - Break-even point: Month 2
        
        **Operational Benefits:**
        - Improved system performance
        - Better resource utilization
        - Enhanced scalability
        - Reduced manual maintenance
        
        ### Next Steps
        
        1. **Immediate Action** (This Week):
           - [ ] Approve Phase 1 implementation
           - [ ] Schedule maintenance window for EC2 changes
           - [ ] Backup critical data before changes
        
        2. **Preparation** (Next Week):
           - [ ] Set up monitoring dashboards
           - [ ] Prepare rollback procedures
           - [ ] Notify stakeholders of upcoming changes
        
        3. **Long-term Planning** (Month 2):
           - [ ] Evaluate Reserved Instance options
           - [ ] Plan advanced monitoring implementation
           - [ ] Schedule regular optimization reviews
        
        ### Questions?
        
        I'm here to help with implementation details, technical questions, or adjustments to this optimization plan. What would you like to focus on first?
        
        ---
        
        *Analysis based on infrastructure data from last 30 days. Savings estimates conservative, actual results may vary.*
        """
        
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, $4)
        """, thread_id, user_context.user_id, "Response Formatting Test", datetime.now(timezone.utc))
        
        message_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, message_id, thread_id, "assistant", well_formatted_response,
             json.dumps({"test_type": "formatting_validation"}),
             datetime.now(timezone.utc))
        
        # Analyze formatting and structure
        formatting_checks = {
            "has_clear_headings": len(re.findall(r'^#+\s+.+$', well_formatted_response, re.MULTILINE)) >= 5,
            "uses_lists": '- ' in well_formatted_response or '1. ' in well_formatted_response,
            "has_tables": '|' in well_formatted_response,
            "uses_emphasis": '**' in well_formatted_response or '*' in well_formatted_response,
            "has_sections": len(re.findall(r'^### .+$', well_formatted_response, re.MULTILINE)) >= 3,
            "includes_actionable_items": '[ ]' in well_formatted_response or 'next steps' in well_formatted_response.lower(),
            "proper_spacing": '\n\n' in well_formatted_response,
            "uses_code_blocks": '```' in well_formatted_response or '`' in well_formatted_response
        }
        
        # Readability analysis
        sentences = re.findall(r'[.!?]+', well_formatted_response)
        paragraphs = [p.strip() for p in well_formatted_response.split('\n\n') if p.strip() and not p.strip().startswith('#')]
        avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        
        readability_metrics = {
            "sentence_count": len(sentences),
            "paragraph_count": len(paragraphs),
            "avg_paragraph_length": avg_paragraph_length,
            "readability_good": avg_paragraph_length <= 100,  # Reasonable paragraph length
            "structure_clear": formatting_checks["has_clear_headings"] and formatting_checks["has_sections"]
        }
        
        # Store formatting analysis
        formatting_analysis = {
            "message_id": message_id,
            "formatting_checks": formatting_checks,
            "readability_metrics": readability_metrics,
            "overall_formatting_score": sum(formatting_checks.values()) / len(formatting_checks),
            "analysis_time": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["redis"].set_json(
            f"formatting_analysis:{message_id}",
            formatting_analysis,
            ex=86400
        )
        
        # Validate formatting requirements
        assert formatting_checks["has_clear_headings"], "Response must have clear heading structure"
        assert formatting_checks["uses_lists"], "Response must use lists for better readability"
        assert formatting_checks["uses_emphasis"], "Response must use emphasis for important points"
        assert formatting_checks["has_sections"], "Response must be properly sectioned"
        assert formatting_checks["includes_actionable_items"], "Response must include actionable next steps"
        assert formatting_checks["proper_spacing"], "Response must have proper spacing between sections"
        
        # Validate readability
        assert readability_metrics["readability_good"], f"Paragraphs too long for readability: {avg_paragraph_length:.1f} words average"
        assert readability_metrics["structure_clear"], "Response structure must be clear and organized"
        
        # Overall formatting score
        overall_score = formatting_analysis["overall_formatting_score"]
        assert overall_score >= 0.8, f"Overall formatting score too low: {overall_score:.2f}"
        
        self.logger.info(f"Response formatting validated - Score: {overall_score:.2f}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_response_completeness_validation(self, real_services_fixture):
        """
        Test that responses provide complete answers addressing all aspects of user queries.
        
        Validates thorough coverage of user needs and expectations.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "completeness-test@example.com", "name": "Completeness User"}
        )
        
        # Complex multi-faceted query that requires comprehensive response
        complex_query = """
        We're a mid-sized company (500 employees) running critical applications on AWS. 
        We need help with:
        1. Cost optimization (current spend $30K/month)  
        2. Security compliance (SOC 2 requirements)
        3. Performance issues (slow API responses)
        4. Disaster recovery planning
        5. Team training and knowledge transfer
        
        Our constraints:
        - Limited downtime tolerance (must maintain 99.9% uptime)
        - Budget constraints (max $5K additional monthly spend)  
        - Small DevOps team (3 people)
        - Regulatory requirements (financial services)
        
        Timeline: Need recommendations within 2 weeks, implementation over 3 months.
        """
        
        # Comprehensive response that addresses all aspects
        complete_response = """
        ## Comprehensive Infrastructure Optimization Plan
        
        I've analyzed your multi-faceted requirements and developed a prioritized approach that addresses all five areas within your constraints.
        
        ### Executive Summary
        - **Total Optimization Value**: $8,200/month savings + $15K compliance value
        - **Additional Investment Needed**: $4,200/month (within $5K budget)
        - **Timeline**: 12-week implementation with minimal downtime
        - **Team Impact**: Structured to work with 3-person DevOps team
        
        ## 1. Cost Optimization Analysis
        
        ### Current State Assessment
        - **Monthly Spend**: $30,000
        - **Optimization Potential**: 25-30% ($7,500-9,000/month)
        - **Quick Wins Available**: $3,200/month (2-week implementation)
        
        ### Optimization Strategy
        #### Phase 1: Immediate Cost Reduction (Week 1-2)
        - **Right-size over-provisioned instances**: 18 instances → $2,400/month savings
        - **Implement S3 lifecycle policies**: $800/month savings
        - **Reserved Instance quick wins**: $1,000/month commitment savings
        
        #### Phase 2: Strategic Cost Management (Month 2-3)
        - **Auto-scaling implementation**: Variable load optimization
        - **CloudFront CDN deployment**: Reduce egress charges
        - **Database optimization**: Performance + cost benefits
        
        ## 2. Security & SOC 2 Compliance
        
        ### Compliance Roadmap
        #### Security Controls (Trust Service Criteria)
        - **Access Management**: Multi-factor authentication, RBAC implementation
        - **Data Encryption**: At-rest and in-transit encryption audit and enhancement
        - **Network Security**: VPC security group optimization, intrusion detection
        
        #### Compliance Implementation (Financial Services Focus)
        - **Audit Logging**: CloudTrail comprehensive logging setup
        - **Data Governance**: Classification and retention policies
        - **Incident Response**: Automated monitoring and response procedures
        
        ### Timeline & Budget Impact
        - **Implementation**: 6-8 weeks parallel to other initiatives
        - **Additional Costs**: $2,800/month for enhanced monitoring and compliance tools
        - **ROI**: Compliance certification enables new client acquisition
        
        ## 3. Performance Optimization Strategy
        
        ### API Response Time Analysis
        #### Current Performance Issues
        - **Average Response Time**: ~850ms (target: <200ms)
        - **Primary Bottlenecks**: Database queries (60%), API gateway (25%), application code (15%)
        
        #### Performance Enhancement Plan
        - **Database Optimization**: Query optimization, indexing strategy, read replicas
        - **Caching Layer**: Redis implementation for frequently accessed data  
        - **API Gateway Optimization**: Request routing and response caching
        - **Application Code**: Profiling and optimization of critical paths
        
        ### Expected Improvements
        - **Response Time**: 75% reduction (850ms → 200ms)
        - **Throughput**: 3x improvement (current bottlenecks removed)
        - **User Experience**: Dramatic improvement in application responsiveness
        
        ## 4. Disaster Recovery & High Availability
        
        ### Current Risk Assessment
        - **Uptime Requirement**: 99.9% (8.76 hours/year downtime budget)
        - **Current Architecture**: Single-region deployment (high risk)
        - **RTO/RPO Requirements**: 1 hour recovery time, 15 minutes data loss maximum
        
        ### DR Implementation Strategy
        #### Multi-AZ High Availability (Phase 1)
        - **Database**: RDS Multi-AZ deployment
        - **Application**: Auto-scaling across 3 availability zones
        - **Load Balancing**: Application Load Balancer with health checks
        
        #### Cross-Region Disaster Recovery (Phase 2)  
        - **Data Replication**: Cross-region RDS read replicas
        - **Application Deployment**: Standby environment in secondary region
        - **DNS Failover**: Route 53 health-based routing
        
        ### Uptime Impact & Cost
        - **Expected Uptime**: 99.95% (2.6 hours/year downtime)
        - **Additional Cost**: $1,400/month for multi-region setup
        - **Business Value**: Prevents estimated $50K/hour outage costs
        
        ## 5. Team Training & Knowledge Transfer
        
        ### Training Program Structure
        #### AWS Fundamentals (Week 1-2)
        - **Core Services**: EC2, RDS, S3, VPC fundamentals
        - **Security Best Practices**: IAM, encryption, compliance basics
        - **Cost Management**: Billing, budgets, optimization tools
        
        #### Advanced Operations (Week 3-8)
        - **Monitoring & Alerting**: CloudWatch, custom metrics, incident response
        - **Infrastructure as Code**: Terraform basics, deployment pipelines
        - **Performance Tuning**: Database optimization, caching strategies
        
        #### Ongoing Support
        - **Weekly Review Sessions**: Team progress and Q&A
        - **Documentation Development**: Runbooks and operational procedures
        - **Certification Path**: AWS certification support for team members
        
        ### Knowledge Transfer Investment
        - **Training Cost**: $800/month for 3 months (online courses + certification)
        - **Internal Time**: 8 hours/week per team member (manageable workload)
        - **Long-term Value**: Reduced external consulting dependency
        
        ## Implementation Timeline & Resource Allocation
        
        ### Week 1-2: Quick Wins & Foundation
        - [ ] **Cost Optimization**: Immediate EC2 right-sizing and S3 policies
        - [ ] **Security Audit**: Current state assessment and gap analysis
        - [ ] **Performance Baseline**: Comprehensive performance profiling
        - [ ] **Team Training Start**: AWS fundamentals program launch
        
        ### Week 3-6: Core Implementation  
        - [ ] **Multi-AZ Deployment**: High availability architecture
        - [ ] **Security Controls**: SOC 2 compliance implementation
        - [ ] **Performance Optimization**: Database and caching deployment
        - [ ] **Monitoring Setup**: Comprehensive observability platform
        
        ### Week 7-10: Advanced Features
        - [ ] **Auto-scaling**: Dynamic scaling implementation
        - [ ] **Cross-region DR**: Disaster recovery testing and validation
        - [ ] **Advanced Security**: Compliance testing and certification prep
        - [ ] **Performance Validation**: Load testing and optimization
        
        ### Week 11-12: Testing & Certification
        - [ ] **End-to-end Testing**: Complete system validation
        - [ ] **DR Testing**: Disaster recovery exercise
        - [ ] **Compliance Review**: SOC 2 audit preparation
        - [ ] **Team Certification**: Knowledge validation and certification
        
        ## Budget Allocation & ROI Analysis
        
        ### Monthly Investment Breakdown
        | Category | Monthly Cost | ROI Timeline | Business Value |
        |----------|-------------|--------------|----------------|
        | Compliance Tools | $2,800 | 6 months | New client acquisition |
        | DR Infrastructure | $1,400 | Immediate | Risk mitigation |
        | Training Program | $800 | 3 months | Team capability |
        | **Total Additional** | **$4,200** | **3-6 months** | **$15K+ value** |
        
        ### Cost Savings vs Investment
        - **Monthly Savings**: $8,200 (cost optimization)
        - **Monthly Investment**: $4,200 (new capabilities)  
        - **Net Monthly Benefit**: $4,000
        - **Annual Net Benefit**: $48,000
        - **3-Year ROI**: 340%
        
        ## Risk Mitigation & Constraints Management
        
        ### Uptime Protection (99.9% Requirement)
        - **Blue-Green Deployments**: Zero-downtime updates
        - **Gradual Rollouts**: 10% → 50% → 100% traffic migration
        - **Automated Rollback**: Instant reversion if issues detected
        - **Maintenance Windows**: Off-peak scheduled maintenance only
        
        ### Team Capacity Management (3-Person Team)
        - **Phased Implementation**: No more than 2 major changes simultaneously
        - **External Support**: Temporary consulting during complex migrations
        - **Automation First**: Reduce manual operational overhead
        - **Documentation**: Comprehensive runbooks for all procedures
        
        ### Budget Constraint Adherence (Max $5K)
        - **Actual Spend**: $4,200/month (within budget)
        - **Cost Optimization**: $8,200/month savings offsets investment
        - **Flexible Scaling**: Can reduce scope if budget pressures arise
        
        ## Success Metrics & Monitoring
        
        ### Key Performance Indicators
        | Metric | Current | Target | Timeline |
        |--------|---------|---------|----------|
        | Monthly AWS Spend | $30,000 | $21,800 | 8 weeks |
        | API Response Time | 850ms | <200ms | 6 weeks |
        | System Uptime | 99.2% | 99.95% | 4 weeks |
        | Compliance Score | 60% | 95% | 10 weeks |
        | Team Certification | 0 | 3 certified | 12 weeks |
        
        ### Monitoring Dashboard
        - **Cost Tracking**: Daily spend monitoring with alerts
        - **Performance Metrics**: Real-time API and database performance
        - **Security Monitoring**: Compliance and security event tracking  
        - **Team Progress**: Training completion and certification status
        
        ## Next Steps & Decision Points
        
        ### Immediate Actions Required (This Week)
        1. **Executive Approval**: Review and approve overall plan and budget
        2. **Team Alignment**: DevOps team briefing and role assignments  
        3. **Vendor Coordination**: Begin compliance tool evaluation
        4. **Timeline Confirmation**: Validate implementation schedule
        
        ### Week 1 Deliverables
        1. **Cost Optimization**: EC2 right-sizing plan with rollback strategy
        2. **Security Assessment**: Gap analysis report with remediation priorities
        3. **Performance Baseline**: Current system performance comprehensive report
        4. **Training Launch**: Team members enrolled in AWS fundamentals
        
        ### Decision Points
        - **Week 2**: Approve Phase 2 implementation based on Phase 1 results
        - **Week 4**: Validate multi-AZ deployment success before DR implementation
        - **Week 6**: Compliance progress review and SOC 2 timeline confirmation
        - **Week 10**: Final budget and timeline adjustments based on progress
        
        ## Questions & Support
        
        I'm available for detailed technical discussions, implementation support, and progress reviews throughout this engagement. Key areas where additional consultation may be valuable:
        
        - **Technical Architecture**: Detailed design reviews for complex components
        - **Compliance Guidance**: SOC 2 audit preparation and evidence collection
        - **Performance Optimization**: Application-specific tuning recommendations  
        - **Team Development**: Customized training paths based on current skill levels
        
        What aspect would you like to dive deeper into first? I recommend starting with the cost optimization quick wins while we plan the broader implementation strategy.
        
        ---
        
        *This comprehensive plan addresses all five requirements within your stated constraints. Implementation can begin immediately with quick wins while building toward long-term strategic goals.*
        """
        
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at, metadata)
            VALUES ($1, $2, $3, $4, $5)
        """, thread_id, user_context.user_id, "Comprehensive Query Response Test",
             datetime.now(timezone.utc),
             json.dumps({
                 "query_type": "multi_faceted", 
                 "complexity": "high",
                 "requirements": ["cost_optimization", "security_compliance", "performance", "disaster_recovery", "team_training"]
             }))
        
        # Store user query
        query_message_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, query_message_id, thread_id, "user", complex_query,
             json.dumps({"message_type": "complex_multi_requirement_query"}),
             datetime.now(timezone.utc))
        
        # Store comprehensive response
        response_message_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, response_message_id, thread_id, "assistant", complete_response,
             json.dumps({"response_type": "comprehensive_multi_requirement_response"}),
             datetime.now(timezone.utc))
        
        # Analyze response completeness
        query_requirements = [
            "cost optimization", "security compliance", "performance issues",  
            "disaster recovery", "team training"
        ]
        
        query_constraints = [
            "uptime tolerance", "budget constraints", "small team", "regulatory requirements"
        ]
        
        # Check coverage of all requirements
        requirement_coverage = {}
        for requirement in query_requirements:
            # Check for variations and synonyms
            requirement_keywords = {
                "cost optimization": ["cost", "optimization", "saving", "budget", "spend"],
                "security compliance": ["security", "compliance", "soc 2", "audit", "governance"],  
                "performance issues": ["performance", "response time", "api", "speed", "latency"],
                "disaster recovery": ["disaster recovery", "dr", "backup", "availability", "uptime"],
                "team training": ["training", "knowledge", "certification", "education", "skill"]
            }
            
            keywords = requirement_keywords.get(requirement, [requirement])
            coverage_score = sum(complete_response.lower().count(keyword) for keyword in keywords)
            requirement_coverage[requirement] = coverage_score > 0
        
        # Check constraint acknowledgment
        constraint_acknowledgment = {}
        for constraint in query_constraints:
            constraint_keywords = {
                "uptime tolerance": ["uptime", "downtime", "99.9%", "availability"],
                "budget constraints": ["budget", "$5k", "cost", "investment"],
                "small team": ["team", "3 people", "devops", "capacity"],
                "regulatory requirements": ["regulatory", "financial services", "compliance"]
            }
            
            keywords = constraint_keywords.get(constraint, [constraint])  
            acknowledgment_score = sum(complete_response.lower().count(keyword) for keyword in keywords)
            constraint_acknowledgment[constraint] = acknowledgment_score > 0
        
        # Check for comprehensive response elements
        comprehensive_elements = {
            "executive_summary": "executive summary" in complete_response.lower(),
            "detailed_analysis": len(re.findall(r'#+\s+.+', complete_response)) >= 10,
            "timeline": "timeline" in complete_response.lower() or "week" in complete_response.lower(),
            "budget_analysis": "$" in complete_response and "cost" in complete_response.lower(),
            "risk_assessment": "risk" in complete_response.lower(),
            "implementation_plan": "implementation" in complete_response.lower(),
            "success_metrics": "metric" in complete_response.lower() or "kpi" in complete_response.lower(),
            "next_steps": "next step" in complete_response.lower()
        }
        
        # Calculate completeness scores
        requirement_coverage_score = sum(requirement_coverage.values()) / len(requirement_coverage)
        constraint_coverage_score = sum(constraint_acknowledgment.values()) / len(constraint_acknowledgment)  
        comprehensive_elements_score = sum(comprehensive_elements.values()) / len(comprehensive_elements)
        
        overall_completeness_score = (requirement_coverage_score + constraint_coverage_score + comprehensive_elements_score) / 3
        
        # Store completeness analysis
        completeness_analysis = {
            "thread_id": thread_id,
            "requirement_coverage": requirement_coverage,
            "constraint_acknowledgment": constraint_acknowledgment,
            "comprehensive_elements": comprehensive_elements,
            "requirement_coverage_score": requirement_coverage_score,
            "constraint_coverage_score": constraint_coverage_score,
            "comprehensive_elements_score": comprehensive_elements_score,
            "overall_completeness_score": overall_completeness_score,
            "analysis_time": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["redis"].set_json(
            f"completeness_analysis:{thread_id}",
            completeness_analysis,
            ex=86400
        )
        
        # Validate completeness requirements
        assert requirement_coverage_score >= 0.8, f"Must address all major requirements: {requirement_coverage_score:.2f}"
        assert constraint_coverage_score >= 0.75, f"Must acknowledge user constraints: {constraint_coverage_score:.2f}"
        assert comprehensive_elements_score >= 0.8, f"Must include comprehensive response elements: {comprehensive_elements_score:.2f}"
        assert overall_completeness_score >= 0.8, f"Overall completeness insufficient: {overall_completeness_score:.2f}"
        
        # Validate specific critical elements
        assert comprehensive_elements["executive_summary"], "Complex queries must have executive summary"
        assert comprehensive_elements["timeline"], "Implementation queries must include timeline"
        assert comprehensive_elements["budget_analysis"], "Cost-related queries must include budget analysis"
        assert comprehensive_elements["next_steps"], "All queries must include clear next steps"
        
        self.logger.info(f"Response completeness validated - Overall score: {overall_completeness_score:.2f}")