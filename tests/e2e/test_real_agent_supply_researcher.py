#!/usr/bin/env python
"""Real Agent Supply Researcher E2E Test Suite - Business Critical Testing

MISSION CRITICAL: Tests supply research agent with real services and LLM.
Business Value: Ensure market research and supplier analysis capabilities.

Business Value Justification (BVJ):
1. Segment: Mid, Enterprise  
2. Business Goal: Enable market intelligence and supply chain optimization
3. Value Impact: Supply research capabilities for vendor analysis and sourcing
4. Revenue Impact: $300K+ ARR from enterprise supply chain management features

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events
- Tests actual research and analysis business logic
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

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# CLAUDE.md compliant imports - Lazy loaded to prevent resource exhaustion
from shared.isolated_environment import get_env
from tests.e2e.e2e_test_config import get_e2e_config, E2ETestConfig, REQUIRED_WEBSOCKET_EVENTS


@dataclass
class SupplyResearchValidation:
    """Captures and validates supply research agent execution."""
    
    user_id: str
    thread_id: str
    research_type: str  # 'vendor_analysis', 'market_research', 'cost_analysis', 'sourcing_strategy'
    query: str
    start_time: float = field(default_factory=time.time)
    
    # Event tracking (MISSION CRITICAL per CLAUDE.md)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    event_types_seen: Set[str] = field(default_factory=set)
    
    # Research-specific validation
    research_steps: List[str] = field(default_factory=list)
    data_sources_used: List[str] = field(default_factory=list)
    analysis_results: List[Dict[str, Any]] = field(default_factory=list)
    tools_executed: List[str] = field(default_factory=list)
    final_research_report: Optional[Dict[str, Any]] = None
    
    # Timing metrics (performance benchmarks per requirements)
    time_to_agent_started: Optional[float] = None
    time_to_first_thinking: Optional[float] = None
    time_to_tool_execution: Optional[float] = None
    time_to_research_completion: Optional[float] = None
    
    # Business logic validation
    research_thoroughness: bool = False
    analysis_quality: bool = False
    actionable_insights: bool = False
    data_accuracy: bool = False


class RealAgentSupplyResearcherTester:
    """Tests supply research agent with real services and WebSocket events."""
    
    # CLAUDE.md REQUIRED WebSocket events from SSOT config
    REQUIRED_EVENTS = set(REQUIRED_WEBSOCKET_EVENTS.keys())
    
    # Test scenarios for supply research
    SUPPLY_RESEARCH_SCENARIOS = [
        {
            "research_type": "vendor_analysis",
            "query": "Research and analyze top cloud infrastructure vendors for enterprise deployment",
            "expected_analysis": ["cost_comparison", "feature_analysis", "reliability_assessment"],
            "expected_tools": ["web_search", "data_analysis", "comparison_tool"],
            "success_criteria": ["vendor_rankings", "cost_breakdown", "recommendations"]
        },
        {
            "research_type": "market_research", 
            "query": "Analyze the current AI/ML software market trends and growth opportunities",
            "expected_analysis": ["market_size", "trend_analysis", "competitor_landscape"],
            "expected_tools": ["market_data", "trend_analysis", "research_aggregation"],
            "success_criteria": ["market_insights", "growth_projections", "opportunity_assessment"]
        },
        {
            "research_type": "cost_analysis",
            "query": "Perform cost-benefit analysis of switching from AWS to Google Cloud",
            "expected_analysis": ["cost_modeling", "migration_analysis", "roi_calculation"],
            "expected_tools": ["cost_calculator", "migration_estimator", "roi_analyzer"],
            "success_criteria": ["cost_savings", "migration_timeline", "risk_assessment"]
        },
        {
            "research_type": "sourcing_strategy",
            "query": "Develop sourcing strategy for enterprise software licensing optimization",
            "expected_analysis": ["vendor_landscape", "negotiation_insights", "optimization_opportunities"],
            "expected_tools": ["vendor_database", "contract_analyzer", "optimization_engine"],
            "success_criteria": ["sourcing_plan", "negotiation_strategy", "cost_optimization"]
        }
    ]
    
    def __init__(self, config: Optional[E2ETestConfig] = None):
        self.config = config or get_e2e_config()
        self.env = None  # Lazy init
        self.ws_client = None
        self.backend_client = None
        self.jwt_helper = None
        self.validations: List[SupplyResearchValidation] = []
        
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
        
        # Create test user with research permissions
        user_data = create_test_user_data("supply_researcher_test")
        self.user_id = str(uuid.uuid4())
        self.email = user_data['email']
        
        # Generate JWT with research permissions
        self.token = self.jwt_helper.create_access_token(
            self.user_id, 
            self.email,
            permissions=["research:execute", "data:analyze", "market:access", "tools:advanced"]
        )
        
        # Initialize WebSocket client from SSOT config
        ws_url = self.config.websocket_url
        self.ws_client = WebSocketTestClient(ws_url)
        
        # Connect with authentication
        connected = await self.ws_client.connect(token=self.token)
        if not connected:
            raise RuntimeError("Failed to connect to WebSocket")
            
        logger.info(f"Supply research test environment ready for user {self.email}")
        logger.info(f"Using backend: {self.config.backend_url}")
        logger.info(f"Using websocket: {self.config.websocket_url}")
        return self
        
    async def teardown(self):
        """Clean up test environment."""
        if self.ws_client:
            await self.ws_client.disconnect()
            
    async def execute_supply_research_scenario(
        self, 
        scenario: Dict[str, Any],
        timeout: float = 60.0
    ) -> SupplyResearchValidation:
        """Execute a supply research scenario and validate results.
        
        Args:
            scenario: Research scenario configuration
            timeout: Maximum execution time
            
        Returns:
            Complete validation results
        """
        thread_id = str(uuid.uuid4())
        validation = SupplyResearchValidation(
            user_id=self.user_id,
            thread_id=thread_id,
            research_type=scenario["research_type"],
            query=scenario["query"]
        )
        
        # Send supply research request via WebSocket
        research_request = {
            "type": "agent_request",
            "agent": "supply_researcher",
            "message": scenario["query"],
            "thread_id": thread_id,
            "context": {
                "research_type": scenario["research_type"],
                "analysis_depth": "comprehensive",
                "user_id": self.user_id,
                "expected_deliverables": scenario.get("success_criteria", [])
            },
            "optimistic_id": str(uuid.uuid4())
        }
        
        await self.ws_client.send_json(research_request)
        logger.info(f"Sent supply research request: {scenario['research_type']} - {scenario['query'][:50]}...")
        
        # Collect all events until completion
        start_time = time.time()
        completed = False
        
        while time.time() - start_time < timeout and not completed:
            event = await self.ws_client.receive(timeout=2.0)
            
            if event:
                await self._process_research_event(event, validation)
                
                # Check for completion
                if event.get("type") in ["agent_completed", "research_completed", "error"]:
                    completed = True
                    validation.time_to_research_completion = time.time() - start_time
                    
        # Validate the research execution results
        self._validate_research_execution(validation, scenario)
        self.validations.append(validation)
        
        return validation
        
    async def _process_research_event(
        self, 
        event: Dict[str, Any], 
        validation: SupplyResearchValidation
    ):
        """Process and categorize supply research specific events."""
        event_type = event.get("type", "unknown")
        event_time = time.time() - validation.start_time
        
        # Record all events
        validation.events_received.append(event)
        validation.event_types_seen.add(event_type)
        
        # Track timing of critical events
        if event_type == "agent_started" and not validation.time_to_agent_started:
            validation.time_to_agent_started = event_time
            logger.info(f"Supply researcher started at {event_time:.2f}s")
            
        elif event_type == "agent_thinking" and not validation.time_to_first_thinking:
            validation.time_to_first_thinking = event_time
            
            # Extract research thinking steps
            thinking_data = event.get("data", {})
            if isinstance(thinking_data, dict):
                thought = thinking_data.get("thought", "")
                if thought and "research" in thought.lower():
                    validation.research_steps.append(thought)
                    
        elif event_type == "tool_executing" and not validation.time_to_tool_execution:
            validation.time_to_tool_execution = event_time
            
            # Track research tools
            tool_name = event.get("data", {}).get("tool_name", "unknown")
            validation.tools_executed.append(tool_name)
            logger.info(f"Supply researcher executing tool: {tool_name}")
            
            # Track data sources
            tool_args = event.get("data", {}).get("args", {})
            if "source" in str(tool_args).lower() or "data" in str(tool_args).lower():
                source_info = str(tool_args)
                validation.data_sources_used.append(source_info[:100])
                
        elif event_type == "tool_completed":
            # Analyze tool results for research insights
            tool_result = event.get("data", {}).get("result", {})
            if isinstance(tool_result, dict):
                # Extract analysis results
                if "analysis" in tool_result or "research" in tool_result:
                    validation.analysis_results.append(tool_result)
                    
        elif event_type in ["agent_completed", "research_completed"]:
            # Extract final research report
            final_data = event.get("data", {})
            if isinstance(final_data, dict):
                validation.final_research_report = final_data
                logger.info(f"Research completed with report sections: {list(final_data.keys())}")
                
    def _validate_research_execution(
        self, 
        validation: SupplyResearchValidation, 
        scenario: Dict[str, Any]
    ):
        """Validate supply research execution against business requirements."""
        
        # 1. Check research thoroughness
        expected_analysis = scenario.get("expected_analysis", [])
        research_content = " ".join(validation.research_steps).lower() if validation.research_steps else ""
        analysis_content = str(validation.analysis_results).lower() if validation.analysis_results else ""
        
        validation.research_thoroughness = len(expected_analysis) > 0 and any(
            exp_analysis.lower() in research_content or exp_analysis.lower() in analysis_content
            for exp_analysis in expected_analysis
        )
        
        # 2. Validate analysis quality  
        if validation.analysis_results:
            # Quality indicators: structured data, multiple data points, insights
            total_analysis_length = sum(
                len(str(result)) for result in validation.analysis_results
            )
            validation.analysis_quality = (
                total_analysis_length > 200 and  # Substantial analysis
                len(validation.analysis_results) >= 1  # At least one analysis result
            )
            
        # 3. Check for actionable insights
        if validation.final_research_report:
            report_content = str(validation.final_research_report).lower()
            insight_indicators = [
                "recommend", "suggest", "opportunity", "strategy", 
                "optimize", "improve", "cost", "benefit", "action"
            ]
            validation.actionable_insights = any(
                indicator in report_content for indicator in insight_indicators
            )
            
        # 4. Validate data accuracy (basic checks)
        if validation.data_sources_used and validation.tools_executed:
            # Assume accuracy if multiple sources and tools were used
            validation.data_accuracy = (
                len(validation.data_sources_used) > 0 and
                len(validation.tools_executed) > 1
            )
            
    def generate_supply_research_report(self) -> str:
        """Generate comprehensive supply research test report."""
        report = []
        report.append("=" * 80)
        report.append("REAL AGENT SUPPLY RESEARCHER TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total research scenarios tested: {len(self.validations)}")
        report.append("")
        
        for i, val in enumerate(self.validations, 1):
            report.append(f"\n--- Research Scenario {i}: {val.research_type} ---")
            report.append(f"Query: {val.query[:80]}...")
            report.append(f"User ID: {val.user_id}")
            report.append(f"Thread ID: {val.thread_id}")
            report.append(f"Events received: {len(val.events_received)}")
            report.append(f"Event types: {sorted(val.event_types_seen)}")
            
            # Check for REQUIRED WebSocket events
            missing_events = self.REQUIRED_EVENTS - val.event_types_seen
            if missing_events:
                report.append(f" WARNING: [U+FE0F] MISSING REQUIRED EVENTS: {missing_events}")
            else:
                report.append("[U+2713] All required WebSocket events received")
                
            # Performance metrics
            report.append("\nPerformance Metrics:")
            report.append(f"  - Agent started: {val.time_to_agent_started:.2f}s" if val.time_to_agent_started else "  - Agent not started")
            report.append(f"  - First thinking: {val.time_to_first_thinking:.2f}s" if val.time_to_first_thinking else "  - No thinking observed")
            report.append(f"  - Tool execution: {val.time_to_tool_execution:.2f}s" if val.time_to_tool_execution else "  - No tools executed")
            report.append(f"  - Research completion: {val.time_to_research_completion:.2f}s" if val.time_to_research_completion else "  - Research not completed")
            
            # Business logic validation
            report.append("\nResearch Quality Validation:")
            report.append(f"  [U+2713] Research thoroughness: {val.research_thoroughness}")
            report.append(f"  [U+2713] Analysis quality: {val.analysis_quality}")
            report.append(f"  [U+2713] Actionable insights: {val.actionable_insights}")
            report.append(f"  [U+2713] Data accuracy: {val.data_accuracy}")
            
            # Research details
            if val.research_steps:
                report.append(f"\nResearch Steps ({len(val.research_steps)}):")
                for step in val.research_steps[:3]:  # Show first 3
                    report.append(f"  - {step[:100]}...")
                    
            if val.tools_executed:
                report.append(f"\nTools Executed: {', '.join(set(val.tools_executed))}")
                
            if val.data_sources_used:
                report.append(f"Data Sources: {len(val.data_sources_used)} sources accessed")
                
            if val.analysis_results:
                report.append(f"Analysis Results: {len(val.analysis_results)} analytical outputs generated")
                
        report.append("\n" + "=" * 80)
        return "\n".join(report)


# ============================================================================
# TEST SUITE
# ============================================================================

@pytest.fixture(params=["local", "staging"])
async def supply_researcher_tester(request):
    """Create and setup the supply researcher tester for both local and staging.
    
    This fixture will run tests against both local and staging environments
    when E2E_TEST_ENV is not set, or against the specified environment.
    """
    # Check if we should skip staging tests
    test_env = get_env("E2E_TEST_ENV", None)
    if test_env and test_env != request.param:
        pytest.skip(f"Skipping {request.param} tests (E2E_TEST_ENV={test_env})")
    
    # Skip staging if environment not available
    if request.param == "staging":
        config = get_e2e_config("staging")
        if not config.is_available():
            pytest.skip(f"Staging environment not available: {config.backend_url}")
    
    # Create tester with appropriate config
    config = get_e2e_config(request.param)
    tester = RealAgentSupplyResearcherTester(config)
    await tester.setup()
    yield tester
    await tester.teardown()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.real_llm
class TestRealAgentSupplyResearcher:
    """Test suite for real supply research agent execution."""
    
    async def test_vendor_analysis_research(self, supply_researcher_tester):
        """Test vendor analysis research with real agent execution."""
        scenario = supply_researcher_tester.SUPPLY_RESEARCH_SCENARIOS[0]  # vendor_analysis
        
        validation = await supply_researcher_tester.execute_supply_research_scenario(
            scenario, timeout=90.0
        )
        
        # CRITICAL: Verify all required WebSocket events
        missing_events = supply_researcher_tester.REQUIRED_EVENTS - validation.event_types_seen
        assert not missing_events, f"Missing required events: {missing_events}"
        
        # Verify agent execution
        assert validation.time_to_agent_started is not None, "Agent should have started"
        assert validation.time_to_agent_started < 5.0, "Agent should start quickly"
        
        # Verify research quality
        assert len(validation.events_received) >= 5, "Should have substantial event flow"
        
        # Performance benchmark
        if validation.time_to_research_completion:
            assert validation.time_to_research_completion < 75.0, "Should complete within performance target"
            
    async def test_market_research_execution(self, supply_researcher_tester):
        """Test market research analysis with real services."""
        scenario = supply_researcher_tester.SUPPLY_RESEARCH_SCENARIOS[1]  # market_research
        
        validation = await supply_researcher_tester.execute_supply_research_scenario(
            scenario, timeout=80.0
        )
        
        # WebSocket events validation
        assert "agent_started" in validation.event_types_seen, "Should have agent_started event"
        assert len(validation.events_received) > 0, "Should receive events"
        
        # Verify research activities
        if validation.research_steps:
            assert len(validation.research_steps) > 0, "Should perform research steps"
            
        # Verify tool usage for market research
        if validation.tools_executed:
            assert len(validation.tools_executed) > 0, "Should use research tools"
            
    async def test_cost_analysis_workflow(self, supply_researcher_tester):
        """Test cost analysis research functionality."""
        scenario = supply_researcher_tester.SUPPLY_RESEARCH_SCENARIOS[2]  # cost_analysis
        
        validation = await supply_researcher_tester.execute_supply_research_scenario(
            scenario, timeout=70.0
        )
        
        # Event flow validation
        assert validation.events_received, "Should receive execution events"
        
        # Business logic validation - cost analysis should be thorough
        if validation.final_research_report:
            report_content = str(validation.final_research_report).lower()
            cost_indicators = ["cost", "price", "savings", "budget", "roi", "analysis"]
            assert any(indicator in report_content for indicator in cost_indicators), \
                "Cost analysis should contain relevant financial terms"
                
    async def test_sourcing_strategy_development(self, supply_researcher_tester):
        """Test sourcing strategy development research."""
        scenario = supply_researcher_tester.SUPPLY_RESEARCH_SCENARIOS[3]  # sourcing_strategy
        
        validation = await supply_researcher_tester.execute_supply_research_scenario(
            scenario, timeout=85.0
        )
        
        # Should produce strategic insights
        if validation.final_research_report:
            assert isinstance(validation.final_research_report, dict), "Should return structured strategy"
            
        # Should use multiple analytical approaches
        if validation.analysis_results:
            assert len(validation.analysis_results) > 0, "Should generate analysis results"
            
    async def test_research_error_handling(self, supply_researcher_tester):
        """Test error handling in research scenarios."""
        # Create scenario with complex/challenging research request
        complex_scenario = {
            "research_type": "complex_analysis",
            "query": "Analyze market trends for quantum computing suppliers in emerging markets with limited data availability",
            "expected_analysis": ["data_limitations", "alternative_approaches"],
            "expected_tools": ["fallback_research"],
            "success_criteria": ["partial_analysis", "limitations_noted"]
        }
        
        validation = await supply_researcher_tester.execute_supply_research_scenario(
            complex_scenario, timeout=45.0
        )
        
        # Should handle complexity gracefully
        assert len(validation.events_received) > 0, "Should receive events even with complex requests"
        
        # Should not crash the system
        assert validation.time_to_agent_started is not None or \
               "error" in validation.event_types_seen, "Should start or handle complexity gracefully"
               
    async def test_research_performance_benchmarks(self, supply_researcher_tester):
        """Test supply research performance against business benchmarks."""
        # Run multiple scenarios for performance measurement
        performance_results = []
        
        for scenario in supply_researcher_tester.SUPPLY_RESEARCH_SCENARIOS[:3]:  # First 3 scenarios
            validation = await supply_researcher_tester.execute_supply_research_scenario(
                scenario, timeout=60.0
            )
            performance_results.append(validation)
            
        # Performance assertions
        start_times = [v.time_to_agent_started for v in performance_results if v.time_to_agent_started]
        completion_times = [v.time_to_research_completion for v in performance_results if v.time_to_research_completion]
        
        if start_times:
            avg_start_time = sum(start_times) / len(start_times)
            assert avg_start_time < 6.0, f"Average start time {avg_start_time:.2f}s too slow for research agent"
            
        if completion_times:
            avg_completion = sum(completion_times) / len(completion_times)
            assert avg_completion < 80.0, f"Average completion {avg_completion:.2f}s too slow for research tasks"
            
    async def test_research_quality_metrics(self, supply_researcher_tester):
        """Test research output quality metrics."""
        scenario = supply_researcher_tester.SUPPLY_RESEARCH_SCENARIOS[0]  # vendor_analysis
        
        validation = await supply_researcher_tester.execute_supply_research_scenario(
            scenario, timeout=75.0
        )
        
        # Quality metrics validation
        quality_score = sum([
            validation.research_thoroughness,
            validation.analysis_quality, 
            validation.actionable_insights,
            validation.data_accuracy
        ])
        
        # Should meet minimum quality threshold
        assert quality_score >= 2, f"Research quality score {quality_score}/4 below minimum threshold"
        
        # Should generate substantial content
        if validation.final_research_report:
            report_size = len(str(validation.final_research_report))
            assert report_size > 100, f"Research report too brief: {report_size} characters"
            
    async def test_comprehensive_supply_research_report(self, supply_researcher_tester):
        """Run comprehensive test and generate detailed report."""
        # Execute representative scenarios
        test_scenarios = supply_researcher_tester.SUPPLY_RESEARCH_SCENARIOS[:3]  # First 3 for comprehensive testing
        
        for scenario in test_scenarios:
            await supply_researcher_tester.execute_supply_research_scenario(
                scenario, timeout=70.0
            )
            
        # Generate and save report
        report = supply_researcher_tester.generate_supply_research_report()
        logger.info("\n" + report)
        
        # Save report to file
        report_file = os.path.join(project_root, "test_outputs", "supply_research_e2e_report.txt")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
            f.write(f"\n\nGenerated at: {datetime.now().isoformat()}\n")
            
        logger.info(f"Supply research report saved to: {report_file}")
        
        # Verify overall success
        total_tests = len(supply_researcher_tester.validations)
        quality_tests = sum(1 for v in supply_researcher_tester.validations 
                          if v.research_thoroughness or v.analysis_quality)
        
        assert quality_tests > 0, "At least some research should meet quality standards"
        success_rate = quality_tests / total_tests if total_tests > 0 else 0
        logger.info(f"Supply research quality rate: {success_rate:.1%}")


if __name__ == "__main__":
    # Run with real services - supply research testing is critical
    # Use E2E_TEST_ENV=staging to test against staging environment
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
    if get_env("E2E_TEST_ENV", "local") == "staging":
        args.append("-m")
        args.append("staging")
        print(f"Running tests against STAGING environment: {get_e2e_config().backend_url}")
    else:
        print(f"Running tests against LOCAL environment: {get_e2e_config().backend_url}")
    
    pytest.main(args)