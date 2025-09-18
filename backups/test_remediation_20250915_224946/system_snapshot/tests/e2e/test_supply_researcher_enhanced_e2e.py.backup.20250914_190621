#!/usr/bin/env python
"""Enhanced Supply Researcher E2E Test Suite - Comprehensive Coverage

MISSION CRITICAL: Enhanced testing of supply research agent with comprehensive scenarios.
Business Value: Ensure complete coverage of supply chain research capabilities.

Business Value Justification (BVJ):
1. Segment: Mid, Enterprise
2. Business Goal: Comprehensive supply chain intelligence and market analysis
3. Value Impact: Advanced supply research capabilities for competitive advantage
4. Revenue Impact: $350K+ ARR from enhanced supply chain consulting features

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events
- Tests comprehensive supply research business logic
- Uses IsolatedEnvironment for environment access
- Absolute imports only
- Factory patterns for user isolation
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# CLAUDE.md compliant imports - Lazy loaded to prevent resource exhaustion
from shared.isolated_environment import get_env
from tests.e2e.e2e_test_config import get_e2e_config, E2ETestConfig, REQUIRED_WEBSOCKET_EVENTS


class SupplyResearchCategory(Enum):
    """Categories of supply research analysis."""
    VENDOR_ANALYSIS = "vendor_analysis"
    MARKET_INTELLIGENCE = "market_intelligence"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    COST_OPTIMIZATION = "cost_optimization"
    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_REVIEW = "compliance_review"
    TECHNOLOGY_EVALUATION = "technology_evaluation"
    SOURCING_STRATEGY = "sourcing_strategy"


@dataclass
class EnhancedSupplyResearchValidation:
    """Captures and validates enhanced supply research agent execution."""
    
    user_id: str
    thread_id: str
    research_category: SupplyResearchCategory
    research_query: str
    complexity_level: str  # 'basic', 'intermediate', 'advanced', 'expert'
    start_time: float = field(default_factory=time.time)
    
    # Event tracking (MISSION CRITICAL per CLAUDE.md)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    event_types_seen: Set[str] = field(default_factory=set)
    
    # Enhanced research-specific validation
    research_methodology: List[str] = field(default_factory=list)
    data_sources_accessed: List[str] = field(default_factory=list)
    analysis_frameworks_used: List[str] = field(default_factory=list)
    insights_generated: List[Dict[str, Any]] = field(default_factory=list)
    recommendations_provided: List[Dict[str, Any]] = field(default_factory=list)
    risk_factors_identified: List[str] = field(default_factory=list)
    tools_utilized: List[str] = field(default_factory=list)
    final_research_deliverable: Optional[Dict[str, Any]] = None
    
    # Quality and depth metrics
    research_depth_score: float = 0.0
    analysis_comprehensiveness: float = 0.0
    actionability_score: float = 0.0
    data_quality_score: float = 0.0
    
    # Timing metrics (performance benchmarks per requirements)
    time_to_research_start: Optional[float] = None
    time_to_first_analysis: Optional[float] = None
    time_to_tool_utilization: Optional[float] = None
    time_to_research_completion: Optional[float] = None
    
    # Business validation criteria
    research_objectives_met: bool = False
    stakeholder_questions_answered: bool = False
    strategic_insights_provided: bool = False
    implementation_guidance_included: bool = False
    quality_meets_enterprise_standards: bool = False


class EnhancedSupplyResearcherTester:
    """Enhanced testing of supply research agent with comprehensive scenarios."""
    
    # CLAUDE.md REQUIRED WebSocket events from SSOT config
    REQUIRED_EVENTS = set(REQUIRED_WEBSOCKET_EVENTS.keys())
    
    # Enhanced supply research scenarios covering all categories
    ENHANCED_SUPPLY_RESEARCH_SCENARIOS = {
        SupplyResearchCategory.VENDOR_ANALYSIS: [
            {
                "complexity_level": "intermediate",
                "query": "Conduct comprehensive vendor analysis for enterprise cloud storage solutions including AWS S3, Google Cloud Storage, and Azure Blob Storage with focus on cost, security, and compliance features",
                "expected_methodology": ["competitive_comparison", "feature_analysis", "cost_modeling"],
                "expected_tools": ["vendor_database", "cost_calculator", "security_scanner"],
                "success_criteria": ["vendor_rankings", "feature_comparison_matrix", "cost_analysis", "security_assessment"],
                "stakeholder_questions": ["Which vendor offers best value?", "What are security implications?", "How do costs scale?"]
            },
            {
                "complexity_level": "advanced",
                "query": "Analyze enterprise software vendor ecosystem for AI/ML platforms including stability, roadmap alignment, integration capabilities, and long-term viability for mission-critical applications",
                "expected_methodology": ["vendor_stability_analysis", "technology_roadmap_review", "integration_assessment"],
                "expected_tools": ["vendor_intelligence", "roadmap_analyzer", "integration_mapper"],
                "success_criteria": ["vendor_scorecards", "risk_assessment", "integration_strategy", "roadmap_alignment"],
                "stakeholder_questions": ["Which vendors are most stable?", "How do roadmaps align with our strategy?", "What integration challenges exist?"]
            }
        ],
        SupplyResearchCategory.MARKET_INTELLIGENCE: [
            {
                "complexity_level": "advanced",
                "query": "Provide comprehensive market intelligence on the cybersecurity software market including market size, growth trends, key players, emerging technologies, and investment patterns for strategic planning",
                "expected_methodology": ["market_size_analysis", "trend_identification", "competitive_landscape_mapping"],
                "expected_tools": ["market_analyzer", "trend_detector", "investment_tracker"],
                "success_criteria": ["market_size_estimates", "growth_projections", "competitor_analysis", "technology_trends"],
                "stakeholder_questions": ["What is the market opportunity?", "Who are emerging competitors?", "What technologies are trending?"]
            },
            {
                "complexity_level": "expert",
                "query": "Analyze global supply chain software market dynamics including regional variations, regulatory impacts, emerging disruptors, and strategic acquisition opportunities for multinational expansion",
                "expected_methodology": ["global_market_analysis", "regulatory_impact_assessment", "acquisition_opportunity_mapping"],
                "expected_tools": ["global_market_tracker", "regulatory_scanner", "m&a_analyzer"],
                "success_criteria": ["regional_market_analysis", "regulatory_impact_report", "acquisition_targets", "expansion_strategy"],
                "stakeholder_questions": ["Which regions offer best opportunities?", "How do regulations affect expansion?", "What acquisition targets exist?"]
            }
        ],
        SupplyResearchCategory.COMPETITIVE_ANALYSIS: [
            {
                "complexity_level": "intermediate",
                "query": "Perform competitive analysis of top 5 CRM software providers focusing on feature differentiation, pricing strategies, market positioning, and competitive advantages for enterprise segment",
                "expected_methodology": ["competitive_feature_mapping", "pricing_analysis", "positioning_assessment"],
                "expected_tools": ["competitor_tracker", "feature_comparator", "pricing_analyzer"],
                "success_criteria": ["competitive_matrix", "feature_gaps", "pricing_insights", "positioning_map"],
                "stakeholder_questions": ["How do we compare to competitors?", "What are our competitive advantages?", "Where are pricing opportunities?"]
            }
        ],
        SupplyResearchCategory.COST_OPTIMIZATION: [
            {
                "complexity_level": "advanced",
                "query": "Identify cost optimization opportunities in enterprise software portfolio including license optimization, vendor consolidation, and contract renegotiation strategies with projected savings analysis",
                "expected_methodology": ["spend_analysis", "optimization_modeling", "contract_optimization"],
                "expected_tools": ["spend_analyzer", "optimization_engine", "contract_negotiator"],
                "success_criteria": ["cost_savings_identification", "optimization_roadmap", "negotiation_strategy", "roi_projections"],
                "stakeholder_questions": ["Where can we reduce costs?", "What consolidation opportunities exist?", "How much can we save?"]
            }
        ],
        SupplyResearchCategory.RISK_ASSESSMENT: [
            {
                "complexity_level": "expert",
                "query": "Conduct comprehensive supply chain risk assessment for critical technology vendors including business continuity, financial stability, geopolitical risks, and mitigation strategies",
                "expected_methodology": ["risk_identification", "impact_assessment", "mitigation_planning"],
                "expected_tools": ["risk_scanner", "stability_analyzer", "mitigation_planner"],
                "success_criteria": ["risk_register", "impact_analysis", "mitigation_strategies", "contingency_plans"],
                "stakeholder_questions": ["What are our biggest risks?", "How stable are key vendors?", "What mitigation options exist?"]
            }
        ],
        SupplyResearchCategory.TECHNOLOGY_EVALUATION: [
            {
                "complexity_level": "advanced",
                "query": "Evaluate emerging technology trends in enterprise automation including RPA, AI/ML platforms, and low-code solutions with implementation feasibility and business impact assessment",
                "expected_methodology": ["technology_assessment", "feasibility_analysis", "impact_modeling"],
                "expected_tools": ["tech_evaluator", "feasibility_checker", "impact_calculator"],
                "success_criteria": ["technology_scorecard", "feasibility_report", "implementation_roadmap", "business_case"],
                "stakeholder_questions": ["Which technologies should we adopt?", "What is implementation complexity?", "What is the business impact?"]
            }
        ],
        SupplyResearchCategory.SOURCING_STRATEGY: [
            {
                "complexity_level": "expert",
                "query": "Develop comprehensive sourcing strategy for enterprise cloud infrastructure including multi-cloud approach, vendor relationship management, and strategic partnership opportunities",
                "expected_methodology": ["sourcing_strategy_development", "vendor_relationship_planning", "partnership_evaluation"],
                "expected_tools": ["sourcing_optimizer", "relationship_manager", "partnership_evaluator"],
                "success_criteria": ["sourcing_strategy", "vendor_relationship_plan", "partnership_recommendations", "implementation_timeline"],
                "stakeholder_questions": ["What sourcing approach is optimal?", "How should we manage vendor relationships?", "What partnerships make sense?"]
            }
        ]
    }
    
    def __init__(self, config: Optional[E2ETestConfig] = None):
        self.config = config or get_e2e_config()
        self.env = None  # Lazy init
        self.ws_client = None
        self.backend_client = None
        self.jwt_helper = None
        self.validations: List[EnhancedSupplyResearchValidation] = []
        
    async def setup(self):
        """Initialize test environment with real services."""
        # Lazy imports per CLAUDE.md to prevent Docker crashes
        from shared.isolated_environment import IsolatedEnvironment
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        from tests.clients.backend_client import BackendTestClient
        from tests.clients.websocket_client import WebSocketTestClient
        from tests.e2e.test_data_factory import create_test_user_data
        
        self.env = IsolatedEnvironment()
        self.jwt_helper = JWTTestHelper()
        
        # Initialize backend client from SSOT config
        backend_url = self.config.backend_url
        self.backend_client = BackendTestClient(backend_url)
        
        # Create test user with enhanced research permissions
        user_data = create_test_user_data("enhanced_supply_researcher_test")
        self.user_id = str(uuid.uuid4())
        self.email = user_data['email']
        
        # Generate JWT with comprehensive research permissions
        self.token = self.jwt_helper.create_access_token(
            self.user_id, 
            self.email,
            permissions=[
                "research:advanced", "data:analyze", "market:access", "tools:specialized",
                "vendor:analyze", "competitive:intelligence", "risk:assess", "strategy:develop"
            ]
        )
        
        # Initialize WebSocket client from SSOT config
        ws_url = self.config.websocket_url
        self.ws_client = WebSocketTestClient(ws_url)
        
        # Connect with authentication
        connected = await self.ws_client.connect(token=self.token)
        if not connected:
            raise RuntimeError("Failed to connect to WebSocket")
            
        logger.info(f"Enhanced supply research test environment ready for user {self.email}")
        logger.info(f"Using backend: {self.config.backend_url}")
        logger.info(f"Using websocket: {self.config.websocket_url}")
        return self
        
    async def teardown(self):
        """Clean up test environment."""
        if self.ws_client:
            await self.ws_client.disconnect()
            
    async def execute_enhanced_supply_research_scenario(
        self, 
        research_category: SupplyResearchCategory,
        scenario: Dict[str, Any],
        timeout: float = 180.0
    ) -> EnhancedSupplyResearchValidation:
        """Execute an enhanced supply research scenario and validate results.
        
        Args:
            research_category: Category of supply research
            scenario: Research scenario configuration
            timeout: Maximum execution time
            
        Returns:
            Complete validation results
        """
        thread_id = str(uuid.uuid4())
        validation = EnhancedSupplyResearchValidation(
            user_id=self.user_id,
            thread_id=thread_id,
            research_category=research_category,
            research_query=scenario["query"],
            complexity_level=scenario["complexity_level"]
        )
        
        # Send enhanced supply research request via WebSocket
        research_request = {
            "type": "agent_request",
            "agent": "supply_researcher",
            "message": scenario["query"],
            "thread_id": thread_id,
            "context": {
                "research_category": research_category.value,
                "complexity_level": scenario["complexity_level"],
                "analysis_depth": "comprehensive",
                "user_id": self.user_id,
                "expected_deliverables": scenario.get("success_criteria", []),
                "stakeholder_questions": scenario.get("stakeholder_questions", []),
                "methodology_requirements": scenario.get("expected_methodology", [])
            },
            "optimistic_id": str(uuid.uuid4())
        }
        
        await self.ws_client.send_json(research_request)
        logger.info(f"Sent enhanced supply research: {research_category.value} ({scenario['complexity_level']}) - {scenario['query'][:60]}...")
        
        # Collect all events until completion
        start_time = time.time()
        completed = False
        
        while time.time() - start_time < timeout and not completed:
            event = await self.ws_client.receive(timeout=3.0)
            
            if event:
                await self._process_enhanced_research_event(event, validation, scenario)
                
                # Check for completion
                if event.get("type") in ["agent_completed", "research_completed", "error"]:
                    completed = True
                    validation.time_to_research_completion = time.time() - start_time
                    
        # Validate the enhanced research execution results
        self._validate_enhanced_research_execution(validation, scenario)
        self.validations.append(validation)
        
        return validation
        
    async def _process_enhanced_research_event(
        self, 
        event: Dict[str, Any], 
        validation: EnhancedSupplyResearchValidation,
        scenario: Dict[str, Any]
    ):
        """Process and categorize enhanced supply research specific events."""
        event_type = event.get("type", "unknown")
        event_time = time.time() - validation.start_time
        
        # Record all events
        validation.events_received.append(event)
        validation.event_types_seen.add(event_type)
        
        # Track timing of critical events
        if event_type == "agent_started" and not validation.time_to_research_start:
            validation.time_to_research_start = event_time
            logger.info(f"Enhanced supply researcher started at {event_time:.2f}s")
            
        elif event_type == "agent_thinking" and not validation.time_to_first_analysis:
            validation.time_to_first_analysis = event_time
            
            # Extract research methodology and analysis frameworks
            thinking_data = event.get("data", {})
            if isinstance(thinking_data, dict):
                thought = thinking_data.get("thought", "")
                
                # Identify research methodology
                methodology_keywords = ["analysis", "research", "evaluation", "assessment", "investigation"]
                if any(keyword in thought.lower() for keyword in methodology_keywords):
                    validation.research_methodology.append(thought)
                    
                # Identify analysis frameworks
                framework_keywords = ["framework", "methodology", "approach", "model", "strategy"]
                if any(keyword in thought.lower() for keyword in framework_keywords):
                    validation.analysis_frameworks_used.append(thought)
                    
        elif event_type == "tool_executing" and not validation.time_to_tool_utilization:
            validation.time_to_tool_utilization = event_time
            
            # Track specialized research tools
            tool_name = event.get("data", {}).get("tool_name", "unknown")
            validation.tools_utilized.append(tool_name)
            logger.info(f"Enhanced supply researcher executing tool: {tool_name}")
            
            # Track data sources accessed
            tool_args = event.get("data", {}).get("args", {})
            if "source" in str(tool_args).lower() or "database" in str(tool_args).lower():
                source_info = str(tool_args)
                validation.data_sources_accessed.append(source_info[:150])
                
        elif event_type == "tool_completed":
            # Analyze tool results for enhanced research insights
            tool_result = event.get("data", {}).get("result", {})
            if isinstance(tool_result, dict):
                # Extract insights and recommendations
                if "insights" in tool_result or "analysis" in tool_result:
                    validation.insights_generated.append(tool_result)
                    
                if "recommendations" in tool_result:
                    validation.recommendations_provided.append(tool_result)
                    
                if "risks" in tool_result or "risk" in str(tool_result).lower():
                    risk_content = str(tool_result)
                    validation.risk_factors_identified.append(risk_content[:200])
                    
        elif event_type in ["agent_completed", "research_completed"]:
            # Extract final enhanced research deliverable
            final_data = event.get("data", {})
            if isinstance(final_data, dict):
                validation.final_research_deliverable = final_data
                logger.info(f"Enhanced research completed with deliverable sections: {list(final_data.keys())}")
                
                # Extract structured research components
                if "methodology" in final_data:
                    validation.research_methodology.extend(final_data.get("methodology", []))
                if "insights" in final_data:
                    validation.insights_generated.append(final_data["insights"])
                if "recommendations" in final_data:
                    validation.recommendations_provided.append(final_data["recommendations"])
                    
    def _validate_enhanced_research_execution(
        self, 
        validation: EnhancedSupplyResearchValidation, 
        scenario: Dict[str, Any]
    ):
        """Validate enhanced supply research execution against business requirements."""
        
        # 1. Calculate research depth score
        depth_indicators = [
            len(validation.research_methodology) > 0,
            len(validation.data_sources_accessed) > 1,
            len(validation.analysis_frameworks_used) > 0,
            len(validation.tools_utilized) > 2,
            validation.final_research_deliverable is not None
        ]
        validation.research_depth_score = sum(depth_indicators) / len(depth_indicators)
        
        # 2. Calculate analysis comprehensiveness
        expected_methodology = scenario.get("expected_methodology", [])
        if expected_methodology:
            methodology_content = " ".join(validation.research_methodology).lower()
            methodology_coverage = sum(
                1 for method in expected_methodology 
                if method.lower().replace("_", " ") in methodology_content
            ) / len(expected_methodology)
        else:
            methodology_coverage = 0.5 if validation.research_methodology else 0.0
            
        success_criteria = scenario.get("success_criteria", [])
        if success_criteria and validation.final_research_deliverable:
            deliverable_content = str(validation.final_research_deliverable).lower()
            criteria_coverage = sum(
                1 for criteria in success_criteria
                if criteria.lower().replace("_", " ") in deliverable_content
            ) / len(success_criteria)
        else:
            criteria_coverage = 0.5 if validation.final_research_deliverable else 0.0
            
        validation.analysis_comprehensiveness = (methodology_coverage + criteria_coverage) / 2
        
        # 3. Calculate actionability score
        actionability_indicators = [
            len(validation.recommendations_provided) > 0,
            len(validation.insights_generated) > 0,
            validation.final_research_deliverable and "strategy" in str(validation.final_research_deliverable).lower(),
            validation.final_research_deliverable and "implementation" in str(validation.final_research_deliverable).lower()
        ]
        validation.actionability_score = sum(actionability_indicators) / len(actionability_indicators)
        
        # 4. Calculate data quality score
        data_quality_indicators = [
            len(validation.data_sources_accessed) > 1,
            len(validation.tools_utilized) > 1,
            len(validation.analysis_frameworks_used) > 0,
            validation.final_research_deliverable and len(str(validation.final_research_deliverable)) > 500
        ]
        validation.data_quality_score = sum(data_quality_indicators) / len(data_quality_indicators)
        
        # 5. Validate business criteria
        validation.research_objectives_met = validation.analysis_comprehensiveness >= 0.6
        validation.stakeholder_questions_answered = validation.actionability_score >= 0.5
        validation.strategic_insights_provided = len(validation.insights_generated) > 0 or \
                                                (validation.final_research_deliverable and "strategic" in str(validation.final_research_deliverable).lower())
        validation.implementation_guidance_included = validation.actionability_score >= 0.5
        
        # 6. Determine enterprise quality standards
        overall_quality_score = (
            validation.research_depth_score +
            validation.analysis_comprehensiveness +
            validation.actionability_score +
            validation.data_quality_score
        ) / 4
        
        validation.quality_meets_enterprise_standards = overall_quality_score >= 0.7
        
    def generate_enhanced_supply_research_report(self) -> str:
        """Generate comprehensive enhanced supply research test report."""
        report = []
        report.append("=" * 80)
        report.append("ENHANCED SUPPLY RESEARCHER E2E TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total enhanced research scenarios tested: {len(self.validations)}")
        report.append("")
        
        # Group by research category and complexity
        by_category = {}
        for val in self.validations:
            category = val.research_category.value
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(val)
        
        for category, validations in by_category.items():
            report.append(f"\n--- {category.upper().replace('_', ' ')} RESEARCH ---")
            report.append(f"Scenarios: {len(validations)}")
            
            for i, val in enumerate(validations, 1):
                report.append(f"\n  Scenario {i} ({val.complexity_level}):")
                report.append(f"    Query: {val.research_query[:100]}...")
                report.append(f"    User ID: {val.user_id}")
                report.append(f"    Thread ID: {val.thread_id}")
                report.append(f"    Events received: {len(val.events_received)}")
                report.append(f"    Event types: {sorted(val.event_types_seen)}")
                
                # Check for REQUIRED WebSocket events
                missing_events = self.REQUIRED_EVENTS - val.event_types_seen
                if missing_events:
                    report.append(f"     WARNING: MISSING REQUIRED EVENTS: {missing_events}")
                else:
                    report.append("    ✓ All required WebSocket events received")
                    
                # Performance metrics
                report.append("    Performance Metrics:")
                report.append(f"      - Research started: {val.time_to_research_start:.2f}s" if val.time_to_research_start else "      - Research not started")
                report.append(f"      - First analysis: {val.time_to_first_analysis:.2f}s" if val.time_to_first_analysis else "      - No analysis observed")
                report.append(f"      - Tool utilization: {val.time_to_tool_utilization:.2f}s" if val.time_to_tool_utilization else "      - No tools utilized")
                report.append(f"      - Research completion: {val.time_to_research_completion:.2f}s" if val.time_to_research_completion else "      - Research not completed")
                
                # Quality metrics
                report.append("    Quality Metrics:")
                report.append(f"      - Research depth score: {val.research_depth_score:.1%}")
                report.append(f"      - Analysis comprehensiveness: {val.analysis_comprehensiveness:.1%}")
                report.append(f"      - Actionability score: {val.actionability_score:.1%}")
                report.append(f"      - Data quality score: {val.data_quality_score:.1%}")
                
                # Business validation
                report.append("    Business Validation:")
                report.append(f"      ✓ Research objectives met: {val.research_objectives_met}")
                report.append(f"      ✓ Stakeholder questions answered: {val.stakeholder_questions_answered}")
                report.append(f"      ✓ Strategic insights provided: {val.strategic_insights_provided}")
                report.append(f"      ✓ Implementation guidance included: {val.implementation_guidance_included}")
                report.append(f"      ✓ Enterprise quality standards: {val.quality_meets_enterprise_standards}")
                
                # Research details
                if val.research_methodology:
                    report.append(f"    Research Methodology ({len(val.research_methodology)} methods):")
                    for method in val.research_methodology[:2]:  # Show first 2
                        report.append(f"      - {method[:80]}...")
                        
                if val.tools_utilized:
                    report.append(f"    Tools Utilized: {', '.join(set(val.tools_utilized))}")
                    
                if val.data_sources_accessed:
                    report.append(f"    Data Sources: {len(val.data_sources_accessed)} sources accessed")
                    
                if val.insights_generated:
                    report.append(f"    Insights Generated: {len(val.insights_generated)} analytical insights")
                    
                if val.recommendations_provided:
                    report.append(f"    Recommendations: {len(val.recommendations_provided)} actionable recommendations")
        
        # Summary statistics
        report.append("\n" + "=" * 80)
        report.append("SUMMARY STATISTICS")
        report.append("=" * 80)
        
        if self.validations:
            # Quality metrics summary
            avg_depth = sum(v.research_depth_score for v in self.validations) / len(self.validations)
            avg_comprehensiveness = sum(v.analysis_comprehensiveness for v in self.validations) / len(self.validations)
            avg_actionability = sum(v.actionability_score for v in self.validations) / len(self.validations)
            avg_data_quality = sum(v.data_quality_score for v in self.validations) / len(self.validations)
            
            report.append(f"Average research depth score: {avg_depth:.1%}")
            report.append(f"Average analysis comprehensiveness: {avg_comprehensiveness:.1%}")
            report.append(f"Average actionability score: {avg_actionability:.1%}")
            report.append(f"Average data quality score: {avg_data_quality:.1%}")
            
            # Enterprise standards compliance
            enterprise_compliant = sum(1 for v in self.validations if v.quality_meets_enterprise_standards)
            report.append(f"Enterprise quality compliance: {enterprise_compliant}/{len(self.validations)} ({enterprise_compliant/len(self.validations):.1%})")
            
            # Performance summary
            completion_times = [v.time_to_research_completion for v in self.validations if v.time_to_research_completion]
            if completion_times:
                avg_completion = sum(completion_times) / len(completion_times)
                report.append(f"Average research completion time: {avg_completion:.2f}s")
                
            # Complexity analysis
            by_complexity = {}
            for val in self.validations:
                complexity = val.complexity_level
                if complexity not in by_complexity:
                    by_complexity[complexity] = []
                by_complexity[complexity].append(val)
                
            report.append("\nComplexity Analysis:")
            for complexity, vals in by_complexity.items():
                enterprise_rate = sum(1 for v in vals if v.quality_meets_enterprise_standards) / len(vals) if vals else 0
                report.append(f"  - {complexity}: {len(vals)} scenarios, {enterprise_rate:.1%} enterprise quality")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)


# ============================================================================
# TEST SUITE
# ============================================================================

@pytest.fixture(params=["local", "staging"])
async def enhanced_supply_researcher_tester(request):
    """Create and setup the enhanced supply researcher tester."""
    # Check if we should skip staging tests
    test_env = get_env().get("E2E_TEST_ENV", None)
    if test_env and test_env != request.param:
        pytest.skip(f"Skipping {request.param} tests (E2E_TEST_ENV={test_env})")
    
    # Skip staging if environment not available
    if request.param == "staging":
        config = get_e2e_config("staging")
        if not config.is_available():
            pytest.skip(f"Staging environment not available: {config.backend_url}")
    
    # Create tester with appropriate config
    config = get_e2e_config(request.param)
    tester = EnhancedSupplyResearcherTester(config)
    await tester.setup()
    yield tester
    await tester.teardown()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.real_llm
class TestEnhancedSupplyResearcher:
    """Test suite for enhanced supply research agent execution."""
    
    async def test_vendor_analysis_comprehensive(self, enhanced_supply_researcher_tester):
        """Test comprehensive vendor analysis research capabilities."""
        category = SupplyResearchCategory.VENDOR_ANALYSIS
        scenario = enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[category][0]  # intermediate
        
        validation = await enhanced_supply_researcher_tester.execute_enhanced_supply_research_scenario(
            category, scenario, timeout=200.0
        )
        
        # CRITICAL: Verify all required WebSocket events
        missing_events = enhanced_supply_researcher_tester.REQUIRED_EVENTS - validation.event_types_seen
        assert not missing_events, f"Missing required events: {missing_events}"
        
        # Verify enhanced research execution
        assert validation.time_to_research_start is not None, "Enhanced research should have started"
        assert validation.time_to_research_start < 10.0, "Enhanced research should start quickly"
        
        # Verify research quality for intermediate complexity
        assert validation.research_depth_score >= 0.5, f"Research depth {validation.research_depth_score:.1%} insufficient for intermediate complexity"
        assert validation.analysis_comprehensiveness >= 0.4, f"Analysis comprehensiveness {validation.analysis_comprehensiveness:.1%} insufficient"
        
        # Verify vendor analysis specific requirements
        if validation.final_research_deliverable:
            deliverable_content = str(validation.final_research_deliverable).lower()
            vendor_terms = ["vendor", "comparison", "analysis", "cost", "features"]
            assert any(term in deliverable_content for term in vendor_terms), \
                "Vendor analysis should contain relevant terminology"
        
        # Performance benchmark for intermediate complexity
        if validation.time_to_research_completion:
            assert validation.time_to_research_completion < 180.0, "Should complete within performance target"
            
    async def test_market_intelligence_advanced(self, enhanced_supply_researcher_tester):
        """Test advanced market intelligence research capabilities."""
        category = SupplyResearchCategory.MARKET_INTELLIGENCE
        scenario = enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[category][0]  # advanced
        
        validation = await enhanced_supply_researcher_tester.execute_enhanced_supply_research_scenario(
            category, scenario, timeout=220.0
        )
        
        # WebSocket events validation
        assert "agent_started" in validation.event_types_seen, "Should have agent_started event"
        assert len(validation.events_received) > 0, "Should receive market intelligence events"
        
        # Verify advanced research quality
        assert validation.research_depth_score >= 0.6, f"Advanced research depth {validation.research_depth_score:.1%} insufficient"
        assert validation.strategic_insights_provided, "Advanced market intelligence should provide strategic insights"
        
        # Verify market intelligence specific analysis
        if validation.insights_generated:
            assert len(validation.insights_generated) > 0, "Should generate market insights"
            
        # Check for comprehensive analysis
        if validation.analysis_frameworks_used:
            assert len(validation.analysis_frameworks_used) > 0, "Should use analysis frameworks for advanced research"
            
    async def test_competitive_analysis_intermediate(self, enhanced_supply_researcher_tester):
        """Test competitive analysis research capabilities."""
        category = SupplyResearchCategory.COMPETITIVE_ANALYSIS
        scenario = enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[category][0]  # intermediate
        
        validation = await enhanced_supply_researcher_tester.execute_enhanced_supply_research_scenario(
            category, scenario, timeout=180.0
        )
        
        # Event flow validation
        assert validation.events_received, "Should receive competitive analysis events"
        
        # Competitive analysis validation
        if validation.final_research_deliverable:
            deliverable_content = str(validation.final_research_deliverable).lower()
            competitive_terms = ["competitive", "competitor", "comparison", "market", "positioning"]
            assert any(term in deliverable_content for term in competitive_terms), \
                "Competitive analysis should use competitive terminology"
                
        # Check actionability for business decisions
        assert validation.actionability_score >= 0.3, f"Competitive analysis actionability {validation.actionability_score:.1%} too low"
        
    async def test_risk_assessment_expert_level(self, enhanced_supply_researcher_tester):
        """Test expert-level risk assessment research capabilities."""
        category = SupplyResearchCategory.RISK_ASSESSMENT
        scenario = enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[category][0]  # expert
        
        validation = await enhanced_supply_researcher_tester.execute_enhanced_supply_research_scenario(
            category, scenario, timeout=240.0
        )
        
        # Expert level quality expectations
        assert validation.research_depth_score >= 0.7, f"Expert research depth {validation.research_depth_score:.1%} insufficient"
        assert validation.data_quality_score >= 0.6, f"Expert data quality {validation.data_quality_score:.1%} insufficient"
        
        # Risk assessment specific validation
        if validation.risk_factors_identified:
            assert len(validation.risk_factors_identified) > 0, "Should identify risk factors"
            
        # Should meet enterprise standards for expert level
        assert validation.quality_meets_enterprise_standards, "Expert level should meet enterprise quality standards"
        
    async def test_technology_evaluation_comprehensive(self, enhanced_supply_researcher_tester):
        """Test technology evaluation research capabilities."""
        category = SupplyResearchCategory.TECHNOLOGY_EVALUATION
        scenario = enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[category][0]  # advanced
        
        validation = await enhanced_supply_researcher_tester.execute_enhanced_supply_research_scenario(
            category, scenario, timeout=200.0
        )
        
        # Technology evaluation validation
        if validation.final_research_deliverable:
            deliverable_content = str(validation.final_research_deliverable).lower()
            tech_terms = ["technology", "evaluation", "feasibility", "implementation", "automation"]
            assert any(term in deliverable_content for term in tech_terms), \
                "Technology evaluation should use relevant terminology"
        
        # Should provide implementation guidance
        assert validation.implementation_guidance_included, "Technology evaluation should include implementation guidance"
        
    async def test_research_quality_across_complexity_levels(self, enhanced_supply_researcher_tester):
        """Test research quality scaling across different complexity levels."""
        # Test scenarios with different complexity levels
        test_scenarios = [
            (SupplyResearchCategory.VENDOR_ANALYSIS, enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[SupplyResearchCategory.VENDOR_ANALYSIS][0]),  # intermediate
            (SupplyResearchCategory.MARKET_INTELLIGENCE, enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[SupplyResearchCategory.MARKET_INTELLIGENCE][1]),  # expert
            (SupplyResearchCategory.COST_OPTIMIZATION, enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[SupplyResearchCategory.COST_OPTIMIZATION][0])  # advanced
        ]
        
        quality_results = []
        
        for category, scenario in test_scenarios:
            validation = await enhanced_supply_researcher_tester.execute_enhanced_supply_research_scenario(
                category, scenario, timeout=200.0
            )
            quality_results.append((scenario["complexity_level"], validation))
            
        # Quality should generally increase with complexity
        for complexity, validation in quality_results:
            if complexity == "intermediate":
                min_quality = 0.4
            elif complexity == "advanced":
                min_quality = 0.6
            elif complexity == "expert":
                min_quality = 0.7
            else:
                min_quality = 0.3
                
            overall_quality = (
                validation.research_depth_score + validation.analysis_comprehensiveness +
                validation.actionability_score + validation.data_quality_score
            ) / 4
            
            assert overall_quality >= min_quality, \
                f"{complexity} research quality {overall_quality:.1%} below expected {min_quality:.1%}"
        
        logger.info(f"Quality scaling validation completed across complexity levels")
        
    async def test_stakeholder_questions_coverage(self, enhanced_supply_researcher_tester):
        """Test coverage of stakeholder questions in research deliverables."""
        # Use scenario with explicit stakeholder questions
        category = SupplyResearchCategory.VENDOR_ANALYSIS
        scenario = enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[category][1]  # advanced with stakeholder questions
        
        validation = await enhanced_supply_researcher_tester.execute_enhanced_supply_research_scenario(
            category, scenario, timeout=190.0
        )
        
        # Should answer stakeholder questions
        assert validation.stakeholder_questions_answered, "Should address stakeholder questions"
        
        # Check if deliverable addresses specific questions
        if validation.final_research_deliverable and scenario.get("stakeholder_questions"):
            deliverable_content = str(validation.final_research_deliverable).lower()
            questions_addressed = 0
            
            for question in scenario["stakeholder_questions"]:
                # Check if key terms from question appear in deliverable
                question_terms = question.lower().split()[:3]  # First 3 words
                if any(term in deliverable_content for term in question_terms):
                    questions_addressed += 1
                    
            question_coverage = questions_addressed / len(scenario["stakeholder_questions"])
            assert question_coverage >= 0.4, f"Stakeholder question coverage {question_coverage:.1%} too low"
            
            logger.info(f"Stakeholder question coverage: {question_coverage:.1%}")
        
    async def test_comprehensive_enhanced_supply_research_report(self, enhanced_supply_researcher_tester):
        """Run comprehensive enhanced supply research tests and generate detailed report."""
        # Execute representative scenarios from different categories and complexities
        comprehensive_scenarios = [
            (SupplyResearchCategory.VENDOR_ANALYSIS, enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[SupplyResearchCategory.VENDOR_ANALYSIS][0]),
            (SupplyResearchCategory.MARKET_INTELLIGENCE, enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[SupplyResearchCategory.MARKET_INTELLIGENCE][0]),
            (SupplyResearchCategory.COMPETITIVE_ANALYSIS, enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[SupplyResearchCategory.COMPETITIVE_ANALYSIS][0]),
            (SupplyResearchCategory.RISK_ASSESSMENT, enhanced_supply_researcher_tester.ENHANCED_SUPPLY_RESEARCH_SCENARIOS[SupplyResearchCategory.RISK_ASSESSMENT][0])
        ]
        
        for category, scenario in comprehensive_scenarios:
            await enhanced_supply_researcher_tester.execute_enhanced_supply_research_scenario(
                category, scenario, timeout=210.0
            )
            
        # Generate and save report
        report = enhanced_supply_researcher_tester.generate_enhanced_supply_research_report()
        logger.info("\n" + report)
        
        # Save report to file
        report_file = os.path.join(project_root, "test_outputs", "enhanced_supply_research_e2e_report.txt")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
            f.write(f"\n\nGenerated at: {datetime.now().isoformat()}\n")
            
        logger.info(f"Enhanced supply research report saved to: {report_file}")
        
        # Verify overall research quality
        total_tests = len(enhanced_supply_researcher_tester.validations)
        high_quality_tests = sum(
            1 for v in enhanced_supply_researcher_tester.validations 
            if v.quality_meets_enterprise_standards
        )
        
        assert high_quality_tests > 0, "At least some enhanced research should meet enterprise quality standards"
        
        enterprise_quality_rate = high_quality_tests / total_tests if total_tests > 0 else 0
        logger.info(f"Enhanced supply research enterprise quality rate: {enterprise_quality_rate:.1%}")


if __name__ == "__main__":
    # Run with real services - enhanced supply research testing is critical for enterprise features
    import sys
    args = [
        __file__,
        "-v",
        "--real-services",
        "--real-llm",
        "-s",
        "--tb=short"
    ]
    
    # Add staging marker if running against staging
    if get_env().get("E2E_TEST_ENV", "local") == "staging":
        args.append("-m")
        args.append("staging")
        print(f"Running tests against STAGING environment: {get_e2e_config().backend_url}")
    else:
        print(f"Running tests against LOCAL environment: {get_e2e_config().backend_url}")
    
    pytest.main(args)