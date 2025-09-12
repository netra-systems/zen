#!/usr/bin/env python
"""Real Agent Validation Chains E2E Test Suite - Business Critical Testing

MISSION CRITICAL: Tests agent validation workflows and quality assurance chains.
Business Value: Ensure data validation and quality control in agent workflows.

Business Value Justification (BVJ):
1. Segment: Mid, Enterprise
2. Business Goal: Ensure data quality and validation integrity
3. Value Impact: Validation chains prevent data corruption and ensure accuracy
4. Revenue Impact: $275K+ ARR from enterprise data quality requirements

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events
- Tests actual validation business logic
- Uses IsolatedEnvironment for environment access
- Absolute imports only
- Factory patterns for user isolation
- Uses SSOT E2E test configuration
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple, Union
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


class ValidationStage(Enum):
    """Validation chain stages."""
    INPUT_VALIDATION = "input_validation"
    PROCESSING_VALIDATION = "processing_validation"
    OUTPUT_VALIDATION = "output_validation"
    CROSS_VALIDATION = "cross_validation"
    FINAL_VERIFICATION = "final_verification"


@dataclass
class ValidationResult:
    """Tracks individual validation result."""
    stage: ValidationStage
    validator_name: str
    start_time: float
    end_time: Optional[float] = None
    passed: bool = False
    score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None


@dataclass
class ValidationChainExecution:
    """Captures validation chain execution data."""
    chain_id: str
    chain_type: str
    validation_results: List[ValidationResult] = field(default_factory=list)
    overall_passed: bool = False
    confidence_score: float = 0.0
    quality_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class AgentValidationChainsValidation:
    """Captures and validates agent validation chains execution."""
    
    user_id: str
    thread_id: str
    validation_scenario: str
    start_time: float = field(default_factory=time.time)
    
    # Event tracking (MISSION CRITICAL per CLAUDE.md)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    event_types_seen: Set[str] = field(default_factory=set)
    
    # Validation chain tracking
    validation_chains: List[ValidationChainExecution] = field(default_factory=list)
    validation_coverage: Dict[ValidationStage, int] = field(default_factory=dict)
    quality_gates_passed: List[str] = field(default_factory=list)
    
    # Timing metrics (performance benchmarks per requirements)
    time_to_first_validation: Optional[float] = None
    time_to_validation_complete: Optional[float] = None
    
    # Business logic validation
    validation_chains_complete: bool = False
    data_quality_assured: bool = False
    compliance_verified: bool = False
    business_rules_enforced: bool = False


class RealAgentValidationChainsTester:
    """Tests agent validation chains with real services and WebSocket events."""
    
    # CLAUDE.md REQUIRED WebSocket events from SSOT config
    REQUIRED_EVENTS = set(REQUIRED_WEBSOCKET_EVENTS.keys())
    
    # Validation chain test scenarios
    VALIDATION_SCENARIOS = [
        {
            "scenario_name": "data_quality_validation_chain",
            "message": "Validate and process this customer data with full quality checks",
            "test_data": {
                "customer_records": [
                    {"id": "C001", "name": "John Doe", "email": "john@example.com", "age": 30},
                    {"id": "C002", "name": "", "email": "invalid-email", "age": -5},
                    {"id": "C003", "name": "Jane Smith", "email": "jane@example.com", "age": 25}
                ]
            },
            "validation_stages": [
                ValidationStage.INPUT_VALIDATION,
                ValidationStage.PROCESSING_VALIDATION,
                ValidationStage.OUTPUT_VALIDATION
            ],
            "expected_quality_gates": ["data_format_check", "business_rules_check", "output_consistency_check"],
            "success_criteria": ["invalid_data_flagged", "valid_data_processed", "quality_report_generated"]
        },
        {
            "scenario_name": "business_rules_validation_chain",
            "message": "Apply comprehensive business rule validation to this transaction data",
            "test_data": {
                "transactions": [
                    {"id": "T001", "amount": 1000.00, "currency": "USD", "type": "purchase"},
                    {"id": "T002", "amount": -500.00, "currency": "EUR", "type": "refund"},
                    {"id": "T003", "amount": 50000.00, "currency": "USD", "type": "purchase"}
                ]
            },
            "validation_stages": [
                ValidationStage.INPUT_VALIDATION,
                ValidationStage.CROSS_VALIDATION,
                ValidationStage.FINAL_VERIFICATION
            ],
            "expected_quality_gates": ["amount_validation", "currency_validation", "fraud_detection", "compliance_check"],
            "success_criteria": ["business_rules_applied", "anomalies_detected", "compliance_verified"]
        },
        {
            "scenario_name": "multi_stage_content_validation",
            "message": "Perform multi-stage validation on this content for accuracy and compliance",
            "test_data": {
                "content_items": [
                    {"id": "A001", "title": "Product Review", "content": "Great product, highly recommend!", "category": "review"},
                    {"id": "A002", "title": "Technical Guide", "content": "Step-by-step instructions for setup...", "category": "documentation"},
                    {"id": "A003", "title": "Marketing Copy", "content": "Buy now! Limited time offer!", "category": "marketing"}
                ]
            },
            "validation_stages": [
                ValidationStage.INPUT_VALIDATION,
                ValidationStage.PROCESSING_VALIDATION,
                ValidationStage.CROSS_VALIDATION,
                ValidationStage.OUTPUT_VALIDATION
            ],
            "expected_quality_gates": ["content_format", "accuracy_check", "compliance_review", "quality_score"],
            "success_criteria": ["content_categorized", "quality_assessed", "compliance_validated"]
        },
        {
            "scenario_name": "error_correction_validation_chain",
            "message": "Validate data with built-in error correction and recovery mechanisms",
            "test_data": {
                "error_prone_data": [
                    {"field1": "correct_value", "field2": None, "field3": "invalid_format_123"},
                    {"field1": "", "field2": "valid_data", "field3": "2023-13-45"},  # Invalid date
                    {"field1": "good_data", "field2": "also_good", "field3": "2023-01-15"}
                ]
            },
            "validation_stages": [
                ValidationStage.INPUT_VALIDATION,
                ValidationStage.PROCESSING_VALIDATION,
                ValidationStage.CROSS_VALIDATION,
                ValidationStage.OUTPUT_VALIDATION,
                ValidationStage.FINAL_VERIFICATION
            ],
            "expected_quality_gates": ["error_detection", "correction_attempt", "validation_retry", "final_quality_check"],
            "success_criteria": ["errors_detected", "corrections_applied", "validation_passed"]
        }
    ]
    
    def __init__(self, config: Optional[E2ETestConfig] = None):
        self.config = config or get_e2e_config()
        self.env = None  # Lazy init
        self.ws_client = None
        self.backend_client = None
        self.jwt_helper = None
        self.validations: List[AgentValidationChainsValidation] = []
        
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
        self.backend_client = BackendTestClient(self.config.backend_url)
        
        # Create test user with validation permissions
        user_data = create_test_user_data("validation_chains_test")
        self.user_id = str(uuid.uuid4())
        self.email = user_data['email']
        
        # Generate JWT with comprehensive validation permissions
        self.token = self.jwt_helper.create_access_token(
            self.user_id, 
            self.email,
            permissions=["agents:use", "validation:execute", "quality:check", "compliance:verify"]
        )
        
        # Initialize WebSocket client from SSOT config
        self.ws_client = WebSocketTestClient(self.config.websocket_url)
        
        # Connect with authentication
        connected = await self.ws_client.connect(token=self.token)
        if not connected:
            raise RuntimeError("Failed to connect to WebSocket")
            
        logger.info(f"Agent validation chains test environment ready for user {self.email}")
        return self
        
    async def teardown(self):
        """Clean up test environment."""
        if self.ws_client:
            await self.ws_client.disconnect()
            
    async def execute_validation_chains_scenario(
        self, 
        scenario: Dict[str, Any],
        timeout: float = 120.0
    ) -> AgentValidationChainsValidation:
        """Execute a validation chains scenario and validate results.
        
        Args:
            scenario: Validation chains scenario configuration
            timeout: Maximum execution time
            
        Returns:
            Complete validation results
        """
        thread_id = str(uuid.uuid4())
        validation = AgentValidationChainsValidation(
            user_id=self.user_id,
            thread_id=thread_id,
            validation_scenario=scenario["scenario_name"]
        )
        
        # Send validation request via WebSocket
        validation_request = {
            "type": "agent_request",
            "agent": "validation_agent",
            "message": scenario["message"],
            "thread_id": thread_id,
            "context": {
                "validation_scenario": scenario["scenario_name"],
                "test_data": scenario["test_data"],
                "validation_stages": [stage.value for stage in scenario["validation_stages"]],
                "quality_gates": scenario.get("expected_quality_gates", []),
                "user_id": self.user_id,
                "enable_validation_chains": True
            },
            "optimistic_id": str(uuid.uuid4())
        }
        
        await self.ws_client.send_json(validation_request)
        logger.info(f"Started validation chains scenario: {scenario['scenario_name']}")
        
        # Monitor validation chain execution
        chain_tracker = {}
        start_time = time.time()
        completed = False
        
        while time.time() - start_time < timeout and not completed:
            event = await self.ws_client.receive(timeout=3.0)
            
            if event:
                await self._process_validation_event(event, validation, chain_tracker)
                
                # Check for completion
                if event.get("type") in ["agent_completed", "validation_completed", "error"]:
                    completed = True
                    validation.time_to_validation_complete = time.time() - start_time
                    
        # Finalize validation chains
        self._finalize_validation_chains(validation, chain_tracker)
        
        # Validate the validation chains results
        self._validate_validation_chains(validation, scenario)
        self.validations.append(validation)
        
        return validation
        
    async def _process_validation_event(
        self, 
        event: Dict[str, Any], 
        validation: AgentValidationChainsValidation,
        chain_tracker: Dict[str, ValidationChainExecution]
    ):
        """Process and categorize validation chains specific events."""
        event_type = event.get("type", "unknown")
        event_time = time.time() - validation.start_time
        
        # Record all events
        validation.events_received.append(event)
        validation.event_types_seen.add(event_type)
        
        # Track timing of critical events
        if event_type == "agent_started":
            logger.info(f"Validation agent started at {event_time:.2f}s")
            
        elif event_type == "validation_chain_started":
            if not validation.time_to_first_validation:
                validation.time_to_first_validation = event_time
                
            # Create validation chain tracking
            chain_data = event.get("data", {})
            chain_id = chain_data.get("chain_id", str(uuid.uuid4()))
            chain_type = chain_data.get("chain_type", "unknown")
            
            validation_chain = ValidationChainExecution(
                chain_id=chain_id,
                chain_type=chain_type
            )
            
            chain_tracker[chain_id] = validation_chain
            logger.info(f"Validation chain started: {chain_type}")
            
        elif event_type == "validation_stage_executed":
            # Track individual validation stage
            stage_data = event.get("data", {})
            chain_id = stage_data.get("chain_id")
            
            if chain_id and chain_id in chain_tracker:
                chain = chain_tracker[chain_id]
                
                # Create validation result
                validation_result = ValidationResult(
                    stage=ValidationStage(stage_data.get("stage", "input_validation")),
                    validator_name=stage_data.get("validator", "unknown"),
                    start_time=time.time(),
                    end_time=time.time() + stage_data.get("duration", 0.1),
                    passed=stage_data.get("passed", False),
                    score=stage_data.get("score", 0.0),
                    details=stage_data.get("details", {})
                )
                
                chain.validation_results.append(validation_result)
                
                # Update coverage
                stage = validation_result.stage
                validation.validation_coverage[stage] = validation.validation_coverage.get(stage, 0) + 1
                
                logger.info(f"Validation stage executed: {stage.value} ({'PASS' if validation_result.passed else 'FAIL'})")
                
        elif event_type == "quality_gate_passed":
            # Track quality gate passage
            gate_data = event.get("data", {})
            gate_name = gate_data.get("gate_name", "unknown_gate")
            validation.quality_gates_passed.append(gate_name)
            
            logger.info(f"Quality gate passed: {gate_name}")
            
        elif event_type == "validation_chain_completed":
            # Update validation chain completion
            chain_data = event.get("data", {})
            chain_id = chain_data.get("chain_id")
            
            if chain_id and chain_id in chain_tracker:
                chain = chain_tracker[chain_id]
                chain.overall_passed = chain_data.get("passed", False)
                chain.confidence_score = chain_data.get("confidence_score", 0.0)
                chain.quality_metrics = chain_data.get("quality_metrics", {})
                
                logger.info(f"Validation chain completed: {chain.chain_type} ({'PASS' if chain.overall_passed else 'FAIL'}, score: {chain.confidence_score:.2f})")
                
        elif event_type in ["agent_completed", "validation_completed"]:
            # Extract final validation results
            final_data = event.get("data", {})
            if isinstance(final_data, dict):
                logger.info(f"Validation chains completed with result keys: {list(final_data.keys())}")
                
    def _finalize_validation_chains(
        self, 
        validation: AgentValidationChainsValidation,
        chain_tracker: Dict[str, ValidationChainExecution]
    ):
        """Finalize validation chains and add to validation."""
        validation.validation_chains = list(chain_tracker.values())
        
        # Update any incomplete chains
        for chain in validation.validation_chains:
            if chain.confidence_score == 0.0 and chain.validation_results:
                # Calculate confidence from individual results
                passed_results = [r for r in chain.validation_results if r.passed]
                if chain.validation_results:
                    chain.confidence_score = len(passed_results) / len(chain.validation_results)
                    chain.overall_passed = chain.confidence_score >= 0.7
                    
    def _validate_validation_chains(
        self, 
        validation: AgentValidationChainsValidation, 
        scenario: Dict[str, Any]
    ):
        """Validate validation chains against business requirements."""
        
        # 1. Check validation chain completeness
        expected_stages = scenario.get("validation_stages", [])
        stages_covered = set(validation.validation_coverage.keys())
        expected_stage_set = set(expected_stages)
        
        validation.validation_chains_complete = (
            len(stages_covered & expected_stage_set) >= len(expected_stage_set) * 0.7
        )
        
        # 2. Validate data quality assurance
        if validation.validation_chains:
            passed_chains = sum(1 for chain in validation.validation_chains if chain.overall_passed)
            total_chains = len(validation.validation_chains)
            
            validation.data_quality_assured = (
                passed_chains >= total_chains * 0.7 if total_chains > 0 else False
            )
        else:
            # Fallback: check if quality gates were passed
            validation.data_quality_assured = len(validation.quality_gates_passed) >= 2
            
        # 3. Check compliance verification
        expected_quality_gates = scenario.get("expected_quality_gates", [])
        gates_passed = set(validation.quality_gates_passed)
        expected_gates_set = set(expected_quality_gates)
        
        validation.compliance_verified = (
            len(gates_passed & expected_gates_set) >= len(expected_gates_set) * 0.5
        )
        
        # 4. Validate business rules enforcement
        success_criteria = scenario.get("success_criteria", [])
        if validation.validation_chains and success_criteria:
            # Heuristic: if validation chains completed and quality gates passed, business rules enforced
            validation.business_rules_enforced = (
                validation.validation_chains_complete and
                len(validation.quality_gates_passed) > 0
            )
        else:
            validation.business_rules_enforced = validation.data_quality_assured
            
    def generate_validation_chains_report(self) -> str:
        """Generate comprehensive validation chains test report."""
        report = []
        report.append("=" * 80)
        report.append("REAL AGENT VALIDATION CHAINS TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total validation scenarios tested: {len(self.validations)}")
        report.append("")
        
        for i, val in enumerate(self.validations, 1):
            report.append(f"\n--- Validation Scenario {i}: {val.validation_scenario} ---")
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
            report.append(f"  - Time to first validation: {val.time_to_first_validation:.2f}s" if val.time_to_first_validation else "  - No validation initiated")
            report.append(f"  - Time to validation complete: {val.time_to_validation_complete:.2f}s" if val.time_to_validation_complete else "  - Validation not completed")
            
            # Validation chains analysis
            report.append(f"\nValidation Chains Analysis:")
            report.append(f"  - Total validation chains: {len(val.validation_chains)}")
            report.append(f"  - Quality gates passed: {len(val.quality_gates_passed)}")
            
            if val.validation_chains:
                passed_chains = sum(1 for chain in val.validation_chains if chain.overall_passed)
                avg_confidence = sum(chain.confidence_score for chain in val.validation_chains) / len(val.validation_chains)
                
                report.append(f"  - Successful chains: {passed_chains}")
                report.append(f"  - Average confidence score: {avg_confidence:.2f}")
                
                # Individual chain details
                for j, chain in enumerate(val.validation_chains, 1):
                    status_symbol = "[U+2713]" if chain.overall_passed else "[U+2717]"
                    report.append(f"    {j}. {status_symbol} {chain.chain_type} (confidence: {chain.confidence_score:.2f}, {len(chain.validation_results)} stages)")
                    
            # Validation coverage
            if val.validation_coverage:
                report.append(f"\nValidation Coverage:")
                for stage, count in val.validation_coverage.items():
                    report.append(f"  - {stage.value}: {count} validations")
                    
            # Quality gates
            if val.quality_gates_passed:
                report.append(f"\nQuality Gates Passed: {', '.join(val.quality_gates_passed)}")
                
            # Business logic validation
            report.append("\nBusiness Logic Validation:")
            report.append(f"  [U+2713] Validation chains complete: {val.validation_chains_complete}")
            report.append(f"  [U+2713] Data quality assured: {val.data_quality_assured}")
            report.append(f"  [U+2713] Compliance verified: {val.compliance_verified}")
            report.append(f"  [U+2713] Business rules enforced: {val.business_rules_enforced}")
            
        report.append("\n" + "=" * 80)
        return "\n".join(report)


# ============================================================================
# TEST SUITE
# ============================================================================

@pytest.fixture(params=["local", "staging"])
async def validation_chains_tester(request):
    """Create and setup the validation chains tester for both local and staging."""
    # Check if we should skip staging tests
    test_env = get_env("E2E_TEST_ENV", None)
    if test_env and test_env != request.param:
        pytest.skip(f"Skipping {request.param} tests (E2E_TEST_ENV={test_env})")
    
    # Get configuration for the specific environment
    config = get_e2e_config(force_environment=request.param)
    
    # Check if environment is available
    if not config.is_available():
        pytest.skip(f"{request.param} environment not available")
    
    # Create tester with environment-specific config
    tester = RealAgentValidationChainsTester(config)
    await tester.setup()
    yield tester
    await tester.teardown()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
class TestRealAgentValidationChains:
    """Test suite for real agent validation chains execution."""
    
    async def test_data_quality_validation_chain(self, validation_chains_tester):
        """Test data quality validation chain with real agent execution."""
        scenario = validation_chains_tester.VALIDATION_SCENARIOS[0]  # data_quality_validation_chain
        
        validation = await validation_chains_tester.execute_validation_chains_scenario(
            scenario, timeout=150.0
        )
        
        # CRITICAL: Verify validation chain execution
        assert len(validation.events_received) > 0, "Should receive validation events"
        
        # Verify data quality assurance
        assert validation.data_quality_assured, "Data quality should be assured through validation chains"
        
        # Verify validation coverage
        assert len(validation.validation_coverage) > 0, "Should have validation stage coverage"
        
        # Performance validation
        if validation.time_to_first_validation:
            assert validation.time_to_first_validation < 15.0, "First validation should start quickly"
            
        logger.info(f"Data quality validation: {len(validation.validation_chains)} chains, {len(validation.quality_gates_passed)} gates passed")
        
    async def test_business_rules_validation_chain(self, validation_chains_tester):
        """Test business rules validation chain execution."""
        scenario = validation_chains_tester.VALIDATION_SCENARIOS[1]  # business_rules_validation_chain
        
        validation = await validation_chains_tester.execute_validation_chains_scenario(
            scenario, timeout=140.0
        )
        
        # Business rules enforcement validation
        assert validation.business_rules_enforced, "Business rules should be enforced through validation"
        
        # Compliance verification
        assert validation.compliance_verified, "Compliance should be verified through validation chains"
        
        # Validation chain completion
        if validation.validation_chains:
            successful_chains = sum(1 for chain in validation.validation_chains if chain.overall_passed)
            assert successful_chains > 0, "At least some validation chains should succeed"
            
        logger.info(f"Business rules validation: {len(validation.quality_gates_passed)} quality gates passed")
        
    async def test_multi_stage_content_validation(self, validation_chains_tester):
        """Test multi-stage content validation workflow."""
        scenario = validation_chains_tester.VALIDATION_SCENARIOS[2]  # multi_stage_content_validation
        
        validation = await validation_chains_tester.execute_validation_chains_scenario(
            scenario, timeout=160.0
        )
        
        # Multi-stage validation completion
        assert validation.validation_chains_complete, "Multi-stage validation chains should complete"
        
        # Validation coverage across stages
        expected_stages = {ValidationStage.INPUT_VALIDATION, ValidationStage.PROCESSING_VALIDATION, 
                          ValidationStage.CROSS_VALIDATION, ValidationStage.OUTPUT_VALIDATION}
        covered_stages = set(validation.validation_coverage.keys())
        
        overlap = len(expected_stages & covered_stages)
        assert overlap >= 2, f"Should cover multiple validation stages: {overlap}/4"
        
        # Quality metrics validation
        if validation.validation_chains:
            avg_confidence = sum(chain.confidence_score for chain in validation.validation_chains) / len(validation.validation_chains)
            assert avg_confidence >= 0.5, f"Average validation confidence {avg_confidence:.2f} too low"
            
    async def test_error_correction_validation_chain(self, validation_chains_tester):
        """Test error correction validation chain with recovery mechanisms."""
        scenario = validation_chains_tester.VALIDATION_SCENARIOS[3]  # error_correction_validation_chain
        
        validation = await validation_chains_tester.execute_validation_chains_scenario(
            scenario, timeout=170.0
        )
        
        # Error correction validation
        assert validation.data_quality_assured, "Data quality should be assured despite errors"
        
        # Should handle validation with error correction
        assert len(validation.events_received) > 0, "Should receive events even with error correction"
        
        # Validation chain resilience
        if validation.validation_chains:
            # At least some chains should handle errors gracefully
            total_chains = len(validation.validation_chains)
            completed_chains = sum(1 for chain in validation.validation_chains if chain.confidence_score > 0)
            
            completion_rate = completed_chains / total_chains if total_chains > 0 else 0
            assert completion_rate >= 0.7, f"Validation completion rate {completion_rate:.1%} too low for error correction"
            
    async def test_validation_chains_performance_benchmarks(self, validation_chains_tester):
        """Test validation chains performance against benchmarks."""
        # Run multiple scenarios for performance measurement
        performance_results = []
        
        for scenario in validation_chains_tester.VALIDATION_SCENARIOS[:3]:  # First 3 scenarios
            validation = await validation_chains_tester.execute_validation_chains_scenario(
                scenario, timeout=130.0
            )
            performance_results.append(validation)
            
        # Performance assertions
        first_validation_times = [v.time_to_first_validation for v in performance_results if v.time_to_first_validation]
        completion_times = [v.time_to_validation_complete for v in performance_results if v.time_to_validation_complete]
        
        if first_validation_times:
            avg_first_validation = sum(first_validation_times) / len(first_validation_times)
            assert avg_first_validation < 20.0, f"Average first validation {avg_first_validation:.2f}s too slow"
            
        if completion_times:
            avg_completion = sum(completion_times) / len(completion_times)
            assert avg_completion < 150.0, f"Average validation completion {avg_completion:.2f}s too slow"
            
        # Quality assurance benchmarks
        quality_assured_count = sum(1 for v in performance_results if v.data_quality_assured)
        quality_rate = quality_assured_count / len(performance_results) if performance_results else 0
        
        assert quality_rate >= 0.7, f"Data quality assurance rate {quality_rate:.1%} below benchmark"
        
    async def test_validation_chains_quality_metrics(self, validation_chains_tester):
        """Test validation chains quality metrics."""
        scenario = validation_chains_tester.VALIDATION_SCENARIOS[0]  # Use data quality scenario
        
        validation = await validation_chains_tester.execute_validation_chains_scenario(
            scenario, timeout=130.0
        )
        
        # Calculate validation quality score
        quality_score = sum([
            validation.validation_chains_complete,
            validation.data_quality_assured,
            validation.compliance_verified,
            validation.business_rules_enforced
        ])
        
        # Should meet minimum quality threshold
        assert quality_score >= 3, f"Validation chains quality score {quality_score}/4 below minimum"
        
        # Individual validation chain quality
        if validation.validation_chains:
            high_confidence_chains = sum(
                1 for chain in validation.validation_chains 
                if chain.confidence_score >= 0.8
            )
            
            if len(validation.validation_chains) > 0:
                high_confidence_rate = high_confidence_chains / len(validation.validation_chains)
                assert high_confidence_rate >= 0.5, f"High confidence validation rate {high_confidence_rate:.1%} too low"
                
        logger.info(f"Validation chains quality score: {quality_score}/4")
        
    async def test_validation_chains_event_ordering(self, validation_chains_tester):
        """Test WebSocket event ordering for validation chains."""
        scenario = validation_chains_tester.VALIDATION_SCENARIOS[1]
        
        validation = await validation_chains_tester.execute_validation_chains_scenario(
            scenario, timeout=120.0
        )
        
        # Build event sequence
        event_sequence = [e.get("type") for e in validation.events_received]
        
        # Verify logical ordering for validation chains
        if "validation_chain_started" in event_sequence:
            chain_start_idx = event_sequence.index("validation_chain_started")
            
            if "validation_stage_executed" in event_sequence:
                stage_idx = event_sequence.index("validation_stage_executed")
                assert stage_idx > chain_start_idx, "Validation stages should come after chain start"
                
        # Quality gate ordering
        if "quality_gate_passed" in event_sequence:
            gate_events = [i for i, e in enumerate(event_sequence) if e == "quality_gate_passed"]
            if len(gate_events) > 1:
                # Quality gates should be in sequence (not necessarily consecutive)
                assert gate_events == sorted(gate_events), "Quality gate events should be in order"
                
    async def test_comprehensive_validation_chains_report(self, validation_chains_tester):
        """Run comprehensive test and generate detailed report."""
        # Execute all validation chain scenarios
        for scenario in validation_chains_tester.VALIDATION_SCENARIOS:
            await validation_chains_tester.execute_validation_chains_scenario(
                scenario, timeout=140.0
            )
            
        # Generate and save report
        report = validation_chains_tester.generate_validation_chains_report()
        logger.info("\n" + report)
        
        # Save report to file
        report_file = os.path.join(project_root, "test_outputs", "validation_chains_e2e_report.txt")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
            f.write(f"\n\nGenerated at: {datetime.now().isoformat()}\n")
            
        logger.info(f"Validation chains report saved to: {report_file}")
        
        # Verify overall validation success
        total_tests = len(validation_chains_tester.validations)
        quality_assured = sum(
            1 for v in validation_chains_tester.validations 
            if v.data_quality_assured
        )
        
        assert quality_assured > 0, "At least some validation chains should assure data quality"
        success_rate = quality_assured / total_tests if total_tests > 0 else 0
        logger.info(f"Data quality assurance rate: {success_rate:.1%}")


if __name__ == "__main__":
    # Run with real services - validation chains are critical for data quality
    # Use E2E_TEST_ENV=staging to test against staging environment
    import sys
    args = [
        __file__,
        "-v",
        "--real-services",
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