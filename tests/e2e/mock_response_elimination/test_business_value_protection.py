"""
Business Value Protection Tests

Business Value Justification (BVJ):
- Segment: Enterprise ($500K+ ARR) - Maximum business impact scenarios
- Business Goal: Protect high-value customers from inauthentic AI responses
- Value Impact: Prevent customer churn and reputation damage from mock responses
- Strategic Impact: Platform credibility for highest-paying customers

CRITICAL: These tests focus on the highest business impact scenarios where
mock/fallback responses could cause immediate customer churn, contract
cancellation, or reputation damage among enterprise customers.

Test Status: FAILING (Expected) - Proves enterprise customers can receive mock responses
Fix Required: Enterprise-grade authentic AI or premium error handling only
"""

import asyncio
import pytest
import json
import logging
import time
from typing import Dict, List, Any, Optional
import aiohttp
import websockets

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID

logger = logging.getLogger(__name__)


class TestBusinessValueProtection(BaseE2ETest):
    """
    FAILING TESTS: Prove enterprise customers can receive mock responses
    causing immediate business damage.
    
    These tests target the highest-value customer scenarios where receiving
    mock/fallback responses would have severe business consequences.
    """

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_fortune_500_ceo_never_receives_mock_responses(
        self, real_services_fixture
    ):
        """
        FAILING TEST: Fortune 500 CEO can receive generic fallback responses.
        
        Business Value: $1M+ ARR Fortune 500 CEO using platform for board
        presentations CANNOT receive "I apologize, but I encountered an error"
        without causing immediate contract cancellation.
        
        Expected Failure: CEO receives same generic fallbacks as free users.
        """
        auth_helper = E2EAuthHelper()
        fortune500_ceo = await auth_helper.create_authenticated_user(
            email="ceo@fortune500mega.com",
            subscription_tier="enterprise",
            metadata={
                "arr_value": 1500000,  # $1.5M ARR
                "role": "ceo",
                "company_size": "fortune_500",
                "board_user": True,
                "premium_sla": True,
                "escalation_priority": "immediate"
            }
        )
        
        backend_url = real_services_fixture["backend_url"]
        ws_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=ws_url,
            auth_token=fortune500_ceo.jwt_token
        ) as websocket_client:
            
            # CEO-level critical request for board presentation
            board_presentation_query = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": (
                    "URGENT: Board meeting in 2 hours. Need comprehensive AI analysis "
                    "of our $50M cloud infrastructure spend with specific optimization "
                    "recommendations. This will determine our Q4 technology strategy."
                ),
                "context": {
                    "user_id": str(fortune500_ceo.user_id),
                    "subscription": "enterprise",
                    "arr_value": 1500000,
                    "urgency": "board_presentation",
                    "financial_impact": 50000000,  # $50M infrastructure
                    "role": "ceo",
                    "sla_level": "premium"
                },
                "request_id": f"fortune500_ceo_board_query_{int(time.time())}"
            }
            
            await websocket_client.send_json(board_presentation_query)
            
            events = []
            async for event in websocket_client.receive_events(timeout=60):
                events.append(event)
                if event.get("type") == "agent_completed":
                    break
            
            assert len(events) > 0, "No response to Fortune 500 CEO board query"
            
            completion_event = None
            for event in reversed(events):
                if event.get("type") == "agent_completed":
                    completion_event = event
                    break
            
            assert completion_event is not None, "Board presentation query incomplete"
            
            response_data = completion_event.get("data", {})
            response_content = response_data.get("response", "")
            
            # ⚠️ CRITICAL FORTUNE 500 CEO FAILING ASSERTION ⚠️
            # CEO of $1.5M ARR customer must NEVER receive generic fallback responses
            
            fortune500_forbidden_responses = [
                "i apologize, but i encountered an error",
                "processing completed with fallback response",
                "fallback",
                "generic error",
                "system error",
                "try again later",
                "service unavailable"  # Without premium escalation
            ]
            
            for forbidden_response in fortune500_forbidden_responses:
                assert forbidden_response not in response_content.lower(), (
                    f"FORTUNE 500 CEO RECEIVED GENERIC RESPONSE: CEO of $1.5M ARR "
                    f"customer received '{forbidden_response}' response for board "
                    f"presentation. This causes IMMEDIATE contract cancellation risk. "
                    f"Full response: {response_content[:300]}..."
                )
            
            # For Fortune 500 CEO, response must be either:
            # 1. Comprehensive authentic AI analysis
            # 2. Immediate premium escalation with human expert
            
            if len(response_content) < 1000:  # Short response suspicious
                # Must be premium escalation
                premium_escalation_indicators = [
                    "premium support activated",
                    "human expert assigned", 
                    "immediate escalation",
                    "dedicated specialist",
                    "priority team engaged",
                    "emergency response"
                ]
                
                has_premium_escalation = any(
                    indicator in response_content.lower()
                    for indicator in premium_escalation_indicators
                )
                
                assert has_premium_escalation, (
                    f"SHORT RESPONSE WITHOUT ESCALATION: Fortune 500 CEO received "
                    f"brief response ({len(response_content)} chars) without premium "
                    f"escalation. Must provide either comprehensive analysis or "
                    f"immediate premium support. Response: {response_content}"
                )
            
            else:
                # Long response - must be comprehensive authentic analysis
                comprehensive_analysis_indicators = [
                    "analysis", "optimization", "recommendations", "savings",
                    "infrastructure", "cost breakdown", "strategic", "implementation"
                ]
                
                comprehensive_score = sum(
                    1 for indicator in comprehensive_analysis_indicators
                    if indicator in response_content.lower()
                )
                
                assert comprehensive_score >= 6, (
                    f"INSUFFICIENT ANALYSIS DEPTH: Fortune 500 CEO response lacks "
                    f"comprehensive analysis depth. Score: {comprehensive_score}/8. "
                    f"Board presentation requires detailed strategic analysis."
                )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_cfo_financial_analysis_never_mock_data(
        self, real_services_fixture
    ):
        """
        FAILING TEST: CFO can receive fabricated financial data for critical decisions.
        
        Business Value: CFO of $800K ARR customer making $20M budget decisions
        based on AI analysis CANNOT receive mock financial data without
        causing severe business harm and potential legal liability.
        
        Expected Failure: CFO receives fabricated cost savings or financial metrics.
        """
        auth_helper = E2EAuthHelper()
        enterprise_cfo = await auth_helper.create_authenticated_user(
            email="cfo@enterprise800k.com",
            subscription_tier="enterprise",
            metadata={
                "arr_value": 800000,
                "role": "cfo", 
                "financial_authority": True,
                "budget_responsibility": 20000000,  # $20M budget authority
                "audit_compliance": True,
                "sox_requirements": True  # Sarbanes-Oxley compliance
            }
        )
        
        backend_url = real_services_fixture["backend_url"]
        ws_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=ws_url,
            auth_token=enterprise_cfo.jwt_token
        ) as websocket_client:
            
            # CFO critical financial analysis query
            financial_analysis_query = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": (
                    "CFO CRITICAL: Analyze Q4 infrastructure spend optimization for "
                    "annual budgeting. Need accurate cost savings projections for "
                    "$20M budget allocation. Data will be audited and reported to board."
                ),
                "context": {
                    "user_id": str(enterprise_cfo.user_id),
                    "subscription": "enterprise",
                    "arr_value": 800000,
                    "role": "cfo",
                    "financial_analysis": True,
                    "budget_impact": 20000000,
                    "audit_trail_required": True,
                    "sox_compliance": True
                },
                "request_id": f"cfo_financial_analysis_{int(time.time())}"
            }
            
            await websocket_client.send_json(financial_analysis_query)
            
            events = []
            async for event in websocket_client.receive_events(timeout=90):
                events.append(event)
                if event.get("type") == "agent_completed":
                    break
            
            assert len(events) > 0, "No response to CFO financial analysis"
            
            completion_event = None
            for event in reversed(events):
                if event.get("type") == "agent_completed":
                    completion_event = event
                    break
            
            assert completion_event is not None, "CFO financial analysis incomplete"
            
            response_data = completion_event.get("data", {})
            response_content = response_data.get("response", "")
            
            # Check for financial data in response
            has_financial_data = any(
                indicator in response_content.lower()
                for indicator in [
                    "$", "savings", "cost", "budget", "million", "thousand",
                    "optimization", "reduction", "expense"
                ]
            )
            
            if has_financial_data:
                # ⚠️ CFO FINANCIAL DATA FAILING ASSERTION ⚠️
                # CFO cannot receive fabricated financial data - legal liability risk
                
                fabricated_financial_indicators = [
                    "sample savings",
                    "example cost reduction",
                    "placeholder financial",
                    "mock savings",
                    "generated cost data",
                    "fallback financial",
                    "estimated savings",  # Without real analysis
                    "approximate cost"    # Without data backing
                ]
                
                for fabricated_indicator in fabricated_financial_indicators:
                    assert fabricated_indicator not in response_content.lower(), (
                        f"CFO RECEIVED FABRICATED FINANCIAL DATA: Found '{fabricated_indicator}' "
                        f"in financial analysis for CFO managing $20M budget. This creates "
                        f"legal liability and audit compliance violations. "
                        f"Response excerpt: {response_content[:400]}..."
                    )
                
                # Check for suspiciously round financial numbers (typical of mock data)
                import re
                financial_amounts = re.findall(r'\$[\d,]+\.?\d*[KMB]?', response_content)
                
                for amount in financial_amounts:
                    # Check for suspiciously perfect amounts
                    amount_clean = amount.replace('$', '').replace(',', '')
                    
                    # Extract number and multiplier
                    multiplier = 1
                    if 'K' in amount_clean:
                        multiplier = 1000
                        amount_clean = amount_clean.replace('K', '')
                    elif 'M' in amount_clean:
                        multiplier = 1000000
                        amount_clean = amount_clean.replace('M', '')
                    elif 'B' in amount_clean:
                        multiplier = 1000000000
                        amount_clean = amount_clean.replace('B', '')
                    
                    try:
                        numeric_value = float(amount_clean) * multiplier
                        
                        # Suspiciously round amounts for large financial figures
                        if numeric_value >= 100000:  # $100K+
                            if numeric_value % 100000 == 0:  # Perfect $100K increments
                                assert False, (
                                    f"SUSPICIOUS CFO FINANCIAL AMOUNT: {amount} appears "
                                    f"fabricated - real financial analysis rarely produces "
                                    f"perfect round numbers. CFO needs authentic data."
                                )
                    
                    except ValueError:
                        continue
                
                # Verify financial data has audit trail requirements
                audit_metadata = response_data.get("audit_metadata", {})
                financial_metadata = response_data.get("financial_metadata", {})
                
                if not audit_metadata and not financial_metadata:
                    assert False, (
                        f"MISSING AUDIT METADATA: CFO financial analysis lacks audit "
                        f"trail metadata required for SOX compliance and board reporting."
                    )
            
            else:
                # No financial data provided - must explain why to CFO
                cfo_acceptable_explanations = [
                    "financial data analysis unavailable",
                    "insufficient data for accurate financial projections",
                    "recommend consultation with financial analyst",
                    "data quality insufficient for budget decisions"
                ]
                
                has_cfo_explanation = any(
                    explanation in response_content.lower()
                    for explanation in cfo_acceptable_explanations
                )
                
                assert has_cfo_explanation, (
                    f"NO FINANCIAL DATA WITHOUT CFO EXPLANATION: CFO requested "
                    f"financial analysis for $20M budget but received no financial "
                    f"data and no appropriate explanation. Response: {response_content[:300]}..."
                )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_enterprise_customer_contract_renewal_scenario(
        self, real_services_fixture
    ):
        """
        FAILING TEST: Enterprise customer during contract renewal can receive mock responses.
        
        Business Value: $600K ARR enterprise customer evaluating platform during
        contract renewal period CANNOT receive fallback responses without
        risking non-renewal and competitive evaluation.
        
        Expected Failure: Contract renewal customer receives same fallbacks as regular users.
        """
        auth_helper = E2EAuthHelper()
        renewal_customer = await auth_helper.create_authenticated_user(
            email="vp.procurement@renewal600k.com",
            subscription_tier="enterprise",
            metadata={
                "arr_value": 600000,
                "role": "vp_procurement",
                "contract_status": "renewal_evaluation",
                "renewal_date": "2024-12-31",
                "competitive_evaluation": True,
                "renewal_at_risk": True
            }
        )
        
        backend_url = real_services_fixture["backend_url"]
        ws_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=ws_url,
            auth_token=renewal_customer.jwt_token
        ) as websocket_client:
            
            # Contract renewal evaluation query
            renewal_evaluation_query = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": (
                    "Contract renewal evaluation: Demonstrate platform value with "
                    "comprehensive analysis of our infrastructure optimization. "
                    "VP Procurement evaluating against competitors. Show ROI justification."
                ),
                "context": {
                    "user_id": str(renewal_customer.user_id),
                    "subscription": "enterprise",
                    "arr_value": 600000,
                    "contract_evaluation": True,
                    "renewal_at_risk": True,
                    "competitive_analysis": True,
                    "roi_demonstration": True
                },
                "request_id": f"contract_renewal_eval_{int(time.time())}"
            }
            
            await websocket_client.send_json(renewal_evaluation_query)
            
            events = []
            async for event in websocket_client.receive_events(timeout=75):
                events.append(event)
                if event.get("type") == "agent_completed":
                    break
            
            assert len(events) > 0, "No response to contract renewal evaluation"
            
            completion_event = None
            for event in reversed(events):
                if event.get("type") == "agent_completed":
                    completion_event = event
                    break
            
            assert completion_event is not None, "Contract evaluation incomplete"
            
            response_data = completion_event.get("data", {})
            response_content = response_data.get("response", "")
            
            # ⚠️ CONTRACT RENEWAL RISK FAILING ASSERTION ⚠️
            # Renewal customers must receive premium experience to prevent churn
            
            renewal_risk_responses = [
                "i apologize, but i encountered an error",
                "processing completed with fallback",
                "system error",
                "try again later",
                "service temporarily unavailable",
                "generic response",
                "fallback mode"
            ]
            
            for risk_response in renewal_risk_responses:
                assert risk_response not in response_content.lower(), (
                    f"CONTRACT RENEWAL RISK: $600K ARR customer in renewal evaluation "
                    f"received '{risk_response}' response. This directly contributes to "
                    f"non-renewal risk and competitive disadvantage. "
                    f"Full response: {response_content[:400]}..."
                )
            
            # Renewal evaluation requires demonstration of platform value
            value_demonstration_indicators = [
                "optimization", "savings", "efficiency", "roi", "return on investment",
                "cost reduction", "performance improvement", "competitive advantage"
            ]
            
            value_score = sum(
                1 for indicator in value_demonstration_indicators
                if indicator in response_content.lower()
            )
            
            assert value_score >= 4, (
                f"INSUFFICIENT VALUE DEMONSTRATION: Contract renewal customer "
                f"received response with only {value_score} value indicators out of 8. "
                f"Renewal evaluation requires strong ROI demonstration."
            )
            
            # Check for competitive positioning (renewal customers are comparing)
            competitive_positioning = response_data.get("competitive_analysis", {})
            platform_advantages = response_data.get("platform_advantages", [])
            
            if not competitive_positioning and not platform_advantages:
                logger.warning(
                    "Renewal customer response lacks competitive positioning - "
                    "missed opportunity to demonstrate platform superiority"
                )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_public_company_earnings_call_preparation(
        self, real_services_fixture
    ):
        """
        FAILING TEST: Public company executive preparing for earnings call can receive mock data.
        
        Business Value: Public company executive ($1.2M ARR) using platform for
        earnings call preparation CANNOT receive fabricated data without
        creating SEC compliance risk and potential stock price impact.
        
        Expected Failure: Public company executive receives mock financial data.
        """
        auth_helper = E2EAuthHelper()
        public_company_exec = await auth_helper.create_authenticated_user(
            email="cfo@publiccompany1m2.com", 
            subscription_tier="enterprise",
            metadata={
                "arr_value": 1200000,
                "role": "cfo",
                "company_type": "public",
                "sec_reporting": True,
                "earnings_call_prep": True,
                "investor_relations": True,
                "stock_ticker": "PUBCO"
            }
        )
        
        backend_url = real_services_fixture["backend_url"]
        ws_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=ws_url,
            auth_token=public_company_exec.jwt_token
        ) as websocket_client:
            
            # Public company earnings call preparation query
            earnings_call_query = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": (
                    "EARNINGS CALL PREPARATION: Analyze Q3 cloud infrastructure efficiency "
                    "and cost optimization achievements. Data will be referenced in "
                    "public earnings call and SEC filings. Need precise metrics."
                ),
                "context": {
                    "user_id": str(public_company_exec.user_id),
                    "subscription": "enterprise",
                    "arr_value": 1200000,
                    "company_type": "public",
                    "earnings_call": True,
                    "sec_compliance": True,
                    "public_disclosure": True,
                    "investor_impact": True
                },
                "request_id": f"earnings_call_prep_{int(time.time())}"
            }
            
            await websocket_client.send_json(earnings_call_query)
            
            events = []
            async for event in websocket_client.receive_events(timeout=90):
                events.append(event)
                if event.get("type") == "agent_completed":
                    break
            
            assert len(events) > 0, "No response to earnings call preparation"
            
            completion_event = None
            for event in reversed(events):
                if event.get("type") == "agent_completed":
                    completion_event = event
                    break
            
            assert completion_event is not None, "Earnings call preparation incomplete"
            
            response_data = completion_event.get("data", {})
            response_content = response_data.get("response", "")
            
            # Check for financial metrics in response
            has_financial_metrics = any(
                metric in response_content.lower()
                for metric in [
                    "efficiency", "cost", "savings", "optimization", 
                    "reduction", "improvement", "metrics", "performance"
                ]
            )
            
            if has_financial_metrics:
                # ⚠️ PUBLIC COMPANY SEC COMPLIANCE FAILING ASSERTION ⚠️
                # Public company data for SEC filings cannot be fabricated
                
                public_company_forbidden_data = [
                    "sample efficiency",
                    "example cost savings", 
                    "placeholder metrics",
                    "mock performance data",
                    "generated efficiency",
                    "fallback metrics",
                    "estimated improvements",  # Without backing data
                    "approximate savings"     # For SEC filing use
                ]
                
                for forbidden_data in public_company_forbidden_data:
                    assert forbidden_data not in response_content.lower(), (
                        f"PUBLIC COMPANY RECEIVED MOCK DATA: Found '{forbidden_data}' "
                        f"in earnings call preparation for $1.2M ARR public company. "
                        f"This creates SEC compliance risk and potential investor fraud. "
                        f"Response excerpt: {response_content[:400]}..."
                    )
                
                # Public companies need verifiable data with sources
                sec_compliance_metadata = response_data.get("sec_compliance", {})
                data_verification = response_data.get("data_verification", {})
                
                if not sec_compliance_metadata and not data_verification:
                    assert False, (
                        f"MISSING SEC COMPLIANCE METADATA: Public company earnings "
                        f"call data lacks verification metadata required for SEC "
                        f"compliance and public disclosure."
                    )
                
                # Check for auditable data trails
                if data_verification:
                    required_verification_fields = [
                        "data_sources_verified",
                        "calculation_methodology",
                        "audit_trail_available", 
                        "third_party_validation"
                    ]
                    
                    missing_verification = [
                        field for field in required_verification_fields
                        if not data_verification.get(field)
                    ]
                    
                    assert len(missing_verification) <= 1, (
                        f"INSUFFICIENT DATA VERIFICATION: Public company data missing "
                        f"verification fields for SEC compliance: {missing_verification}"
                    )
            
            else:
                # No financial metrics - must provide SEC-appropriate explanation
                sec_appropriate_explanations = [
                    "insufficient data for sec reporting standards",
                    "data verification in progress",
                    "recommend third-party audit for public disclosure",
                    "compliance review required before reporting"
                ]
                
                has_sec_explanation = any(
                    explanation in response_content.lower()
                    for explanation in sec_appropriate_explanations
                )
                
                assert has_sec_explanation, (
                    f"NO METRICS WITHOUT SEC EXPLANATION: Public company preparing "
                    f"earnings call received no metrics without appropriate SEC "
                    f"compliance explanation. Response: {response_content[:300]}..."
                )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_enterprise_platform_demonstration_no_mock_responses(
        self, real_services_fixture
    ):
        """
        FAILING TEST: Enterprise platform demonstration can include mock responses.
        
        Business Value: Enterprise prospects ($500K+ potential ARR) receiving
        platform demonstrations CANNOT see fallback/mock responses without
        losing competitive deals and sales opportunities.
        
        Expected Failure: Demo environment shows generic fallbacks to prospects.
        """
        auth_helper = E2EAuthHelper()
        enterprise_prospect = await auth_helper.create_authenticated_user(
            email="cto@prospect750k.com",
            subscription_tier="enterprise", 
            metadata={
                "arr_potential": 750000,
                "role": "cto",
                "evaluation_stage": "final_demo",
                "competitive_evaluation": True,
                "decision_maker": True,
                "demo_environment": True
            }
        )
        
        backend_url = real_services_fixture["backend_url"]
        ws_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=ws_url,
            auth_token=enterprise_prospect.jwt_token
        ) as websocket_client:
            
            # Enterprise demo showcase query
            demo_showcase_query = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": (
                    "Platform demonstration: Show comprehensive AI-powered cost "
                    "optimization analysis for enterprise infrastructure. CTO "
                    "evaluating against 3 competitors for $750K annual contract."
                ),
                "context": {
                    "user_id": str(enterprise_prospect.user_id),
                    "subscription": "enterprise",
                    "prospect_value": 750000,
                    "demo_showcase": True,
                    "competitive_evaluation": True,
                    "final_decision": True,
                    "sales_critical": True
                },
                "request_id": f"enterprise_demo_{int(time.time())}"
            }
            
            await websocket_client.send_json(demo_showcase_query)
            
            events = []
            async for event in websocket_client.receive_events(timeout=60):
                events.append(event)
                if event.get("type") == "agent_completed":
                    break
            
            assert len(events) > 0, "No response to enterprise demo showcase"
            
            completion_event = None
            for event in reversed(events):
                if event.get("type") == "agent_completed":
                    completion_event = event
                    break
            
            assert completion_event is not None, "Enterprise demo incomplete"
            
            response_data = completion_event.get("data", {})
            response_content = response_data.get("response", "")
            
            # ⚠️ SALES CRITICAL DEMO FAILING ASSERTION ⚠️
            # Enterprise prospects must never see fallback responses during demos
            
            demo_killing_responses = [
                "i apologize, but i encountered an error",
                "processing completed with fallback",
                "system error occurred",
                "try again later",
                "service unavailable",
                "technical difficulty",
                "fallback mode",
                "generic response"
            ]
            
            for demo_killer in demo_killing_responses:
                assert demo_killer not in response_content.lower(), (
                    f"SALES DEMO FAILURE: $750K prospect CTO received '{demo_killer}' "
                    f"during final platform demonstration. This immediately eliminates "
                    f"competitive advantage and likely results in lost sale. "
                    f"Full response: {response_content[:400]}..."
                )
            
            # Demo must showcase platform capabilities impressively
            impressive_capabilities = [
                "comprehensive analysis",
                "advanced optimization", 
                "intelligent recommendations",
                "automated insights",
                "predictive analytics",
                "machine learning",
                "ai-powered"
            ]
            
            capability_score = sum(
                1 for capability in impressive_capabilities
                if capability in response_content.lower()
            )
            
            assert capability_score >= 5, (
                f"UNIMPRESSIVE DEMO CONTENT: Enterprise demo only showcased "
                f"{capability_score} capabilities out of 7. Competitive demos "
                f"require impressive capability demonstration."
            )
            
            # Demo should highlight competitive advantages
            competitive_advantages = response_data.get("competitive_advantages", [])
            platform_differentiators = response_data.get("platform_differentiators", [])
            
            total_advantages = len(competitive_advantages) + len(platform_differentiators)
            
            assert total_advantages >= 3, (
                f"INSUFFICIENT COMPETITIVE POSITIONING: Demo showed only "
                f"{total_advantages} competitive advantages. $750K prospect "
                f"evaluating 3 competitors needs strong differentiation."
            )
            
            # Verify demo quality metadata
            demo_metadata = response_data.get("demo_metadata", {})
            if demo_metadata:
                demo_quality_score = demo_metadata.get("quality_score", 0)
                assert demo_quality_score >= 8.5, (
                    f"LOW DEMO QUALITY SCORE: Enterprise demo quality score "
                    f"{demo_quality_score} insufficient for $750K prospect."
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])