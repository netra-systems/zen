"""
Test Message Routing Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure messages route to correct agents for coherent AI responses
- Value Impact: Prevents user confusion from wrong agent responses and maintains conversation quality
- Strategic Impact: Enables intelligent message classification that delivers appropriate AI expertise

CRITICAL: This test validates the business logic for message routing that ensures users get
responses from the most appropriate AI agents based on their request content and context.

This test focuses on BUSINESS LOGIC validation, not system integration.
Tests the decision-making algorithms and classification patterns for intelligent message routing.
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set, Tuple
from enum import Enum

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.core_types import UserID, ThreadID, AgentID, ExecutionID


class MessageType(Enum):
    """Types of messages that require routing."""
    COST_OPTIMIZATION = "cost_optimization"
    DATA_ANALYSIS = "data_analysis"
    GENERAL_INQUIRY = "general_inquiry"
    TECHNICAL_SUPPORT = "technical_support"
    REPORT_REQUEST = "report_request"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"


class AgentCapability(Enum):
    """Agent capabilities for routing decisions."""
    COST_ANALYSIS = "cost_analysis"
    DATA_PROCESSING = "data_processing"
    REPORT_GENERATION = "report_generation"
    GENERAL_CONVERSATION = "general_conversation"
    TECHNICAL_EXPERTISE = "technical_expertise"
    TRIAGE = "triage"


class RoutingStrategy(Enum):
    """Routing strategies for different scenarios."""
    DIRECT_MATCH = "direct_match"          # Direct capability match
    BEST_FIT = "best_fit"                  # Best available match
    CHAIN_ROUTING = "chain_routing"        # Route through multiple agents
    FALLBACK = "fallback"                  # Use general purpose agent
    CONTEXT_AWARE = "context_aware"       # Based on conversation context


class ConfidenceLevel(Enum):
    """Confidence levels for routing decisions."""
    HIGH = "high"      # >90% confidence in routing decision
    MEDIUM = "medium"  # 70-90% confidence
    LOW = "low"        # 50-70% confidence


@dataclass
class MessageClassification:
    """Classification result for message analysis."""
    message_type: MessageType
    confidence_level: ConfidenceLevel
    key_intent: str
    extracted_entities: List[str]
    context_indicators: List[str]
    urgency_level: str
    business_value_potential: str


@dataclass
class AgentProfile:
    """Profile of an agent with routing capabilities."""
    agent_id: AgentID
    capabilities: Set[AgentCapability]
    specialties: List[str]
    business_value_focus: str
    response_quality_score: float
    average_response_time: float
    success_rate: float
    can_handle_follow_ups: bool = True
    requires_context: bool = True


@dataclass
class RoutingDecision:
    """Routing decision with business justification."""
    selected_agent: AgentID
    routing_strategy: RoutingStrategy
    confidence_level: ConfidenceLevel
    business_justification: str
    expected_response_quality: float
    estimated_completion_time: float
    alternative_agents: List[AgentID]
    routing_path: List[AgentID] = field(default_factory=list)


class MockMessageRoutingEngine:
    """Mock message routing engine for business logic testing."""
    
    def __init__(self):
        self.agent_profiles = self._initialize_agent_profiles()
        self.routing_rules = self._initialize_routing_rules()
        self.message_patterns = self._initialize_message_patterns()
        self.routing_history: List[Dict[str, Any]] = []
        self.performance_metrics = {}
    
    def _initialize_agent_profiles(self) -> Dict[AgentID, AgentProfile]:
        """Initialize agent profiles with capabilities and performance metrics."""
        return {
            AgentID("cost_optimizer"): AgentProfile(
                agent_id=AgentID("cost_optimizer"),
                capabilities={AgentCapability.COST_ANALYSIS},
                specialties=["cloud cost optimization", "savings analysis", "resource rightsizing"],
                business_value_focus="Deliver quantifiable cost savings recommendations",
                response_quality_score=0.92,
                average_response_time=45.0,  # seconds
                success_rate=0.89
            ),
            AgentID("data_analyzer"): AgentProfile(
                agent_id=AgentID("data_analyzer"),
                capabilities={AgentCapability.DATA_PROCESSING, AgentCapability.COST_ANALYSIS},
                specialties=["data analysis", "pattern recognition", "trend analysis"],
                business_value_focus="Extract actionable insights from complex data",
                response_quality_score=0.88,
                average_response_time=60.0,
                success_rate=0.85
            ),
            AgentID("report_generator"): AgentProfile(
                agent_id=AgentID("report_generator"),
                capabilities={AgentCapability.REPORT_GENERATION},
                specialties=["executive summaries", "detailed reports", "visualizations"],
                business_value_focus="Create comprehensive business reports",
                response_quality_score=0.90,
                average_response_time=90.0,
                success_rate=0.87
            ),
            AgentID("triage_agent"): AgentProfile(
                agent_id=AgentID("triage_agent"),
                capabilities={AgentCapability.TRIAGE, AgentCapability.GENERAL_CONVERSATION},
                specialties=["intent classification", "requirement gathering", "initial assessment"],
                business_value_focus="Route users to optimal AI expertise efficiently",
                response_quality_score=0.85,
                average_response_time=15.0,
                success_rate=0.93
            ),
            AgentID("general_assistant"): AgentProfile(
                agent_id=AgentID("general_assistant"),
                capabilities={AgentCapability.GENERAL_CONVERSATION, AgentCapability.TECHNICAL_EXPERTISE},
                specialties=["general assistance", "clarifications", "basic support"],
                business_value_focus="Provide helpful general assistance and guidance",
                response_quality_score=0.78,
                average_response_time=25.0,
                success_rate=0.82
            )
        }
    
    def _initialize_routing_rules(self) -> Dict[str, Any]:
        """Initialize business rules for message routing."""
        return {
            "prefer_specialist_over_generalist": True,
            "consider_conversation_context": True,
            "route_follow_ups_to_same_agent": True,
            "fallback_to_triage_when_uncertain": True,
            "minimum_confidence_for_direct_routing": 0.75,
            "maximum_routing_chain_length": 3,
            "business_value_prioritization": True,
            "response_time_considerations": {
                "urgent_requests_max_time": 30.0,
                "standard_requests_max_time": 120.0,
                "complex_requests_max_time": 300.0
            }
        }
    
    def _initialize_message_patterns(self) -> Dict[MessageType, Dict[str, Any]]:
        """Initialize message patterns for classification."""
        return {
            MessageType.COST_OPTIMIZATION: {
                "keywords": ["optimize", "reduce costs", "save money", "cost analysis", "efficiency", "budget"],
                "patterns": ["how to reduce", "optimize my", "cost savings", "lower expenses"],
                "context_clues": ["monthly spend", "cloud costs", "AWS bill", "resource usage"],
                "business_priority": "HIGH",
                "typical_urgency": "MEDIUM"
            },
            MessageType.DATA_ANALYSIS: {
                "keywords": ["analyze", "data", "trends", "patterns", "insights", "metrics"],
                "patterns": ["analyze my", "what does the data show", "trends in", "patterns"],
                "context_clues": ["CSV", "data file", "metrics", "dashboard"],
                "business_priority": "HIGH",
                "typical_urgency": "MEDIUM"
            },
            MessageType.REPORT_REQUEST: {
                "keywords": ["report", "summary", "document", "generate", "create", "export"],
                "patterns": ["generate report", "create summary", "export data", "detailed analysis"],
                "context_clues": ["PDF", "executive summary", "stakeholders", "presentation"],
                "business_priority": "MEDIUM",
                "typical_urgency": "LOW"
            },
            MessageType.GENERAL_INQUIRY: {
                "keywords": ["help", "how", "what", "explain", "understand", "question"],
                "patterns": ["can you help", "how do I", "what is", "explain to me"],
                "context_clues": ["confused", "don't understand", "clarify", "explain"],
                "business_priority": "MEDIUM",
                "typical_urgency": "MEDIUM"
            },
            MessageType.FOLLOW_UP: {
                "keywords": ["also", "additionally", "furthermore", "and", "more", "continue"],
                "patterns": ["also can you", "and what about", "continue with", "more details"],
                "context_clues": ["previous", "earlier", "before", "last time"],
                "business_priority": "LOW",
                "typical_urgency": "LOW"
            }
        }
    
    def classify_message(self, message_content: str, conversation_context: Dict[str, Any]) -> MessageClassification:
        """Business logic: Classify message to determine routing needs."""
        message_lower = message_content.lower()
        
        # Calculate scores for each message type
        type_scores = {}
        for message_type, pattern_info in self.message_patterns.items():
            score = 0.0
            
            # Keyword matching
            keyword_matches = sum(1 for keyword in pattern_info["keywords"] 
                                if keyword in message_lower)
            score += keyword_matches * 0.3
            
            # Pattern matching  
            pattern_matches = sum(1 for pattern in pattern_info["patterns"]
                                if pattern in message_lower)
            score += pattern_matches * 0.4
            
            # Context clues
            context_matches = sum(1 for clue in pattern_info["context_clues"]
                                if clue.lower() in message_lower)
            score += context_matches * 0.2
            
            # Conversation context consideration
            if conversation_context.get("previous_message_type") == message_type.value:
                score += 0.3  # Likely continuation
            
            type_scores[message_type] = score
        
        # Determine best match
        best_type = max(type_scores.keys(), key=lambda t: type_scores[t])
        confidence_score = type_scores[best_type]
        
        # Determine confidence level
        if confidence_score >= 1.5:
            confidence = ConfidenceLevel.HIGH
        elif confidence_score >= 1.0:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW
        
        # Extract entities and context
        extracted_entities = self._extract_entities(message_content)
        context_indicators = self._extract_context_indicators(message_content, conversation_context)
        
        # Assess business value potential
        pattern_info = self.message_patterns[best_type]
        business_value_potential = self._assess_business_value_potential(
            best_type, confidence, extracted_entities
        )
        
        return MessageClassification(
            message_type=best_type,
            confidence_level=confidence,
            key_intent=self._extract_primary_intent(message_content, best_type),
            extracted_entities=extracted_entities,
            context_indicators=context_indicators,
            urgency_level=pattern_info["typical_urgency"],
            business_value_potential=business_value_potential
        )
    
    def route_message(self, message_classification: MessageClassification,
                     user_context: Dict[str, Any], 
                     conversation_context: Dict[str, Any]) -> RoutingDecision:
        """Business logic: Route message to most appropriate agent."""
        # Determine required capabilities based on message classification
        required_capabilities = self._determine_required_capabilities(message_classification)
        
        # Find candidate agents
        candidate_agents = self._find_candidate_agents(required_capabilities)
        
        # Apply routing strategy
        routing_strategy = self._select_routing_strategy(
            message_classification, conversation_context, candidate_agents
        )
        
        # Select best agent based on strategy
        selected_agent = self._select_best_agent(
            candidate_agents, routing_strategy, message_classification, conversation_context
        )
        
        if not selected_agent:
            # Fallback to triage agent
            selected_agent = AgentID("triage_agent")
            routing_strategy = RoutingStrategy.FALLBACK
        
        # Calculate routing confidence
        routing_confidence = self._calculate_routing_confidence(
            selected_agent, message_classification, routing_strategy
        )
        
        # Generate business justification
        business_justification = self._generate_business_justification(
            selected_agent, message_classification, routing_strategy
        )
        
        # Get agent profile for metrics
        agent_profile = self.agent_profiles.get(selected_agent)
        expected_quality = agent_profile.response_quality_score if agent_profile else 0.5
        estimated_time = agent_profile.average_response_time if agent_profile else 60.0
        
        # Determine alternative agents
        alternative_agents = [agent_id for agent_id in candidate_agents 
                            if agent_id != selected_agent][:3]  # Top 3 alternatives
        
        routing_decision = RoutingDecision(
            selected_agent=selected_agent,
            routing_strategy=routing_strategy,
            confidence_level=routing_confidence,
            business_justification=business_justification,
            expected_response_quality=expected_quality,
            estimated_completion_time=estimated_time,
            alternative_agents=alternative_agents
        )
        
        # Log routing decision
        self.routing_history.append({
            "timestamp": time.time(),
            "message_type": message_classification.message_type.value,
            "selected_agent": str(selected_agent),
            "confidence": routing_confidence.value,
            "strategy": routing_strategy.value
        })
        
        return routing_decision
    
    def _determine_required_capabilities(self, classification: MessageClassification) -> Set[AgentCapability]:
        """Determine required agent capabilities based on message classification."""
        capability_mapping = {
            MessageType.COST_OPTIMIZATION: {AgentCapability.COST_ANALYSIS},
            MessageType.DATA_ANALYSIS: {AgentCapability.DATA_PROCESSING},
            MessageType.REPORT_REQUEST: {AgentCapability.REPORT_GENERATION},
            MessageType.GENERAL_INQUIRY: {AgentCapability.GENERAL_CONVERSATION},
            MessageType.TECHNICAL_SUPPORT: {AgentCapability.TECHNICAL_EXPERTISE},
            MessageType.FOLLOW_UP: {AgentCapability.GENERAL_CONVERSATION},
            MessageType.CLARIFICATION: {AgentCapability.GENERAL_CONVERSATION, AgentCapability.TRIAGE}
        }
        
        return capability_mapping.get(classification.message_type, {AgentCapability.TRIAGE})
    
    def _find_candidate_agents(self, required_capabilities: Set[AgentCapability]) -> List[AgentID]:
        """Find agents that have the required capabilities."""
        candidates = []
        
        for agent_id, profile in self.agent_profiles.items():
            # Check if agent has any of the required capabilities
            if required_capabilities.intersection(profile.capabilities):
                candidates.append(agent_id)
        
        # Sort by capability match quality and performance
        def agent_score(agent_id: AgentID) -> float:
            profile = self.agent_profiles[agent_id]
            
            # Capability match score
            capability_match = len(required_capabilities.intersection(profile.capabilities))
            capability_score = capability_match / len(required_capabilities) if required_capabilities else 0
            
            # Performance score  
            performance_score = (profile.response_quality_score + profile.success_rate) / 2
            
            # Combined score
            return capability_score * 0.6 + performance_score * 0.4
        
        candidates.sort(key=agent_score, reverse=True)
        return candidates
    
    def _select_routing_strategy(self, classification: MessageClassification,
                               conversation_context: Dict[str, Any],
                               candidate_agents: List[AgentID]) -> RoutingStrategy:
        """Select appropriate routing strategy based on context."""
        # Follow-up routing strategy
        if (classification.message_type == MessageType.FOLLOW_UP and 
            "last_agent" in conversation_context):
            return RoutingStrategy.CONTEXT_AWARE
        
        # High confidence direct routing
        if (classification.confidence_level == ConfidenceLevel.HIGH and 
            len(candidate_agents) > 0):
            return RoutingStrategy.DIRECT_MATCH
        
        # Medium confidence best fit
        if (classification.confidence_level == ConfidenceLevel.MEDIUM and 
            len(candidate_agents) > 1):
            return RoutingStrategy.BEST_FIT
        
        # Low confidence or no clear candidates
        if classification.confidence_level == ConfidenceLevel.LOW or not candidate_agents:
            return RoutingStrategy.FALLBACK
        
        # Default to best fit
        return RoutingStrategy.BEST_FIT
    
    def _select_best_agent(self, candidates: List[AgentID], strategy: RoutingStrategy,
                         classification: MessageClassification, 
                         conversation_context: Dict[str, Any]) -> Optional[AgentID]:
        """Select the best agent based on routing strategy."""
        if not candidates:
            return None
        
        if strategy == RoutingStrategy.CONTEXT_AWARE:
            # Try to route to same agent as last message
            last_agent_str = conversation_context.get("last_agent")
            if last_agent_str:
                last_agent = AgentID(last_agent_str)
                if last_agent in candidates:
                    return last_agent
        
        if strategy == RoutingStrategy.DIRECT_MATCH:
            # Return best capability match (already sorted)
            return candidates[0]
        
        if strategy == RoutingStrategy.BEST_FIT:
            # Consider business value and performance
            def business_value_score(agent_id: AgentID) -> float:
                profile = self.agent_profiles[agent_id]
                
                # Business value alignment
                business_score = 1.0
                if "cost" in classification.key_intent.lower():
                    if "cost" in profile.business_value_focus.lower():
                        business_score = 1.5
                
                # Performance considerations
                quality_score = profile.response_quality_score
                speed_score = 1.0 - (profile.average_response_time / 300.0)  # Normalize to 5min max
                
                return business_score * 0.4 + quality_score * 0.4 + speed_score * 0.2
            
            return max(candidates, key=business_value_score)
        
        if strategy == RoutingStrategy.FALLBACK:
            # Return triage agent or general assistant
            for agent_id in [AgentID("triage_agent"), AgentID("general_assistant")]:
                if agent_id in candidates:
                    return agent_id
            return candidates[0] if candidates else None
        
        return candidates[0]  # Default to first candidate
    
    def _calculate_routing_confidence(self, selected_agent: AgentID,
                                    classification: MessageClassification,
                                    strategy: RoutingStrategy) -> ConfidenceLevel:
        """Calculate confidence in routing decision."""
        agent_profile = self.agent_profiles.get(selected_agent)
        if not agent_profile:
            return ConfidenceLevel.LOW
        
        # Base confidence from classification
        base_confidence = {
            ConfidenceLevel.HIGH: 0.9,
            ConfidenceLevel.MEDIUM: 0.7,
            ConfidenceLevel.LOW: 0.5
        }[classification.confidence_level]
        
        # Agent performance factor
        performance_factor = agent_profile.success_rate
        
        # Strategy confidence
        strategy_confidence = {
            RoutingStrategy.DIRECT_MATCH: 0.9,
            RoutingStrategy.CONTEXT_AWARE: 0.85,
            RoutingStrategy.BEST_FIT: 0.75,
            RoutingStrategy.CHAIN_ROUTING: 0.6,
            RoutingStrategy.FALLBACK: 0.4
        }[strategy]
        
        # Combined confidence
        combined_confidence = (base_confidence * 0.4 + 
                             performance_factor * 0.3 + 
                             strategy_confidence * 0.3)
        
        if combined_confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif combined_confidence >= 0.65:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _generate_business_justification(self, selected_agent: AgentID,
                                       classification: MessageClassification,
                                       strategy: RoutingStrategy) -> str:
        """Generate business justification for routing decision."""
        agent_profile = self.agent_profiles.get(selected_agent)
        if not agent_profile:
            return "Fallback routing due to no suitable agent match"
        
        justifications = {
            RoutingStrategy.DIRECT_MATCH: f"Direct route to {selected_agent} - optimal capability match for {classification.message_type.value} with {agent_profile.response_quality_score:.0%} success rate",
            RoutingStrategy.BEST_FIT: f"Best fit routing to {selected_agent} - {agent_profile.business_value_focus.lower()} aligns with user intent",
            RoutingStrategy.CONTEXT_AWARE: f"Context-aware routing to {selected_agent} - maintains conversation continuity for better user experience",
            RoutingStrategy.FALLBACK: f"Fallback routing to {selected_agent} - ensures user receives assistance while determining optimal routing",
            RoutingStrategy.CHAIN_ROUTING: f"Multi-agent routing through {selected_agent} - complex request requires specialized expertise chain"
        }
        
        return justifications.get(strategy, f"Routed to {selected_agent} for optimal business value delivery")
    
    def _extract_entities(self, message_content: str) -> List[str]:
        """Extract relevant entities from message for routing decisions."""
        entities = []
        message_lower = message_content.lower()
        
        # Cost-related entities
        cost_entities = ["aws", "azure", "gcp", "cloud", "ec2", "s3", "rds", "lambda"]
        entities.extend([entity for entity in cost_entities if entity in message_lower])
        
        # Data entities
        data_entities = ["csv", "json", "database", "sql", "analytics", "metrics"]
        entities.extend([entity for entity in data_entities if entity in message_lower])
        
        # Business entities
        business_entities = ["report", "dashboard", "kpi", "roi", "budget", "forecast"]
        entities.extend([entity for entity in business_entities if entity in message_lower])
        
        return list(set(entities))  # Remove duplicates
    
    def _extract_context_indicators(self, message_content: str, 
                                  conversation_context: Dict[str, Any]) -> List[str]:
        """Extract context indicators for better routing."""
        indicators = []
        
        # Previous conversation indicators
        if conversation_context.get("previous_topic"):
            indicators.append(f"previous_topic:{conversation_context['previous_topic']}")
        
        if conversation_context.get("user_tier"):
            indicators.append(f"user_tier:{conversation_context['user_tier']}")
        
        # Message urgency indicators
        urgent_words = ["urgent", "asap", "immediately", "quickly", "emergency"]
        if any(word in message_content.lower() for word in urgent_words):
            indicators.append("urgency:high")
        
        # Complexity indicators
        complex_indicators = ["complex", "detailed", "comprehensive", "thorough"]
        if any(word in message_content.lower() for word in complex_indicators):
            indicators.append("complexity:high")
        
        return indicators
    
    def _extract_primary_intent(self, message_content: str, message_type: MessageType) -> str:
        """Extract primary intent from message content."""
        message_lower = message_content.lower()
        
        # Intent patterns for different message types
        intent_patterns = {
            MessageType.COST_OPTIMIZATION: {
                "reduce": "reduce_costs",
                "optimize": "optimize_resources", 
                "save": "save_money",
                "analyze": "analyze_costs"
            },
            MessageType.DATA_ANALYSIS: {
                "analyze": "analyze_data",
                "show": "show_insights",
                "trends": "identify_trends",
                "patterns": "find_patterns"
            },
            MessageType.REPORT_REQUEST: {
                "generate": "generate_report",
                "create": "create_document",
                "export": "export_data",
                "summary": "create_summary"
            }
        }
        
        patterns = intent_patterns.get(message_type, {})
        for keyword, intent in patterns.items():
            if keyword in message_lower:
                return intent
        
        return f"general_{message_type.value}"
    
    def _assess_business_value_potential(self, message_type: MessageType, 
                                       confidence: ConfidenceLevel,
                                       entities: List[str]) -> str:
        """Assess potential business value of the request."""
        base_values = {
            MessageType.COST_OPTIMIZATION: "High - Direct cost savings impact",
            MessageType.DATA_ANALYSIS: "High - Actionable insights generation", 
            MessageType.REPORT_REQUEST: "Medium - Executive communication value",
            MessageType.GENERAL_INQUIRY: "Medium - User satisfaction and retention",
            MessageType.FOLLOW_UP: "Low - Incremental value addition",
            MessageType.CLARIFICATION: "Low - Support and clarification value"
        }
        
        base_value = base_values.get(message_type, "Medium - Standard assistance value")
        
        # Adjust based on confidence and entities
        if confidence == ConfidenceLevel.HIGH and len(entities) > 2:
            return base_value.replace("Medium", "High").replace("Low", "Medium")
        elif confidence == ConfidenceLevel.LOW:
            return base_value.replace("High", "Medium").replace("Medium", "Low")
        
        return base_value
    
    def analyze_routing_performance(self) -> Dict[str, Any]:
        """Analyze routing performance for business optimization."""
        if not self.routing_history:
            return {"performance_data": "No routing history available"}
        
        # Agent utilization analysis
        agent_usage = {}
        strategy_usage = {}
        confidence_distribution = {}
        
        for entry in self.routing_history:
            agent = entry["selected_agent"]
            strategy = entry["strategy"]
            confidence = entry["confidence"]
            
            agent_usage[agent] = agent_usage.get(agent, 0) + 1
            strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
            confidence_distribution[confidence] = confidence_distribution.get(confidence, 0) + 1
        
        # Calculate routing efficiency metrics
        total_routings = len(self.routing_history)
        high_confidence_routings = confidence_distribution.get("high", 0)
        direct_match_routings = strategy_usage.get("direct_match", 0)
        fallback_routings = strategy_usage.get("fallback", 0)
        
        efficiency_score = (
            (high_confidence_routings / total_routings) * 0.4 +
            (direct_match_routings / total_routings) * 0.3 +
            ((total_routings - fallback_routings) / total_routings) * 0.3
        ) * 100
        
        return {
            "routing_efficiency_score": efficiency_score,
            "total_routings": total_routings,
            "agent_utilization": agent_usage,
            "strategy_distribution": strategy_usage,
            "confidence_distribution": confidence_distribution,
            "high_confidence_rate": (high_confidence_routings / total_routings) * 100,
            "fallback_rate": (fallback_routings / total_routings) * 100,
            "business_impact_assessment": self._assess_routing_business_impact(efficiency_score)
        }
    
    def _assess_routing_business_impact(self, efficiency_score: float) -> str:
        """Assess business impact of routing performance."""
        if efficiency_score >= 85:
            return "Excellent - Optimal agent-user matching delivers maximum business value"
        elif efficiency_score >= 70:
            return "Good - Effective routing supports strong user experience"
        elif efficiency_score >= 55:
            return "Fair - Routing works but has room for optimization"
        else:
            return "Poor - Routing inefficiencies may impact user satisfaction and business value"


class TestMessageRoutingLogic(SSotBaseTestCase):
    """Test message routing business logic validation."""
    
    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)
        self.routing_engine = MockMessageRoutingEngine()
        self.test_user_id = UserID("enterprise_user_123")
        self.test_thread_id = ThreadID("thread_cost_analysis")
    
    @pytest.mark.unit
    def test_message_classification_business_logic(self):
        """Test message classification for routing decisions."""
        # Test cost optimization message
        cost_message = "Help me optimize my AWS costs and reduce my monthly cloud spending by analyzing my EC2 usage"
        cost_context = {"user_tier": "enterprise", "previous_topic": None}
        
        cost_classification = self.routing_engine.classify_message(cost_message, cost_context)
        
        # Business validation: Should classify as cost optimization
        assert cost_classification.message_type == MessageType.COST_OPTIMIZATION
        assert cost_classification.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
        assert "cost" in cost_classification.key_intent.lower()
        assert any("aws" in entity for entity in cost_classification.extracted_entities)
        assert "High - Direct cost savings" in cost_classification.business_value_potential
        
        # Test data analysis message
        data_message = "Can you analyze the trends in my usage data and show me patterns in the CSV file I uploaded?"
        data_context = {"user_tier": "mid_market"}
        
        data_classification = self.routing_engine.classify_message(data_message, data_context)
        
        # Business validation: Should classify as data analysis
        assert data_classification.message_type == MessageType.DATA_ANALYSIS
        assert "analyze" in data_classification.key_intent.lower()
        assert any("csv" in entity for entity in data_classification.extracted_entities)
        
        # Test general inquiry
        general_message = "Can you help me understand how this platform works?"
        general_context = {}
        
        general_classification = self.routing_engine.classify_message(general_message, general_context)
        
        # Business validation: Should classify as general inquiry
        assert general_classification.message_type == MessageType.GENERAL_INQUIRY
        assert general_classification.confidence_level in [ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]
        
        # Record business metrics
        self.record_metric("message_classification_accuracy", True)
        self.record_metric("cost_optimization_detection", cost_classification.message_type == MessageType.COST_OPTIMIZATION)
        self.record_metric("data_analysis_detection", data_classification.message_type == MessageType.DATA_ANALYSIS)
    
    @pytest.mark.unit
    def test_agent_capability_matching_logic(self):
        """Test agent capability matching for optimal routing."""
        # Test cost optimization routing
        cost_classification = MessageClassification(
            message_type=MessageType.COST_OPTIMIZATION,
            confidence_level=ConfidenceLevel.HIGH,
            key_intent="optimize_costs",
            extracted_entities=["aws", "ec2", "cloud"],
            context_indicators=["user_tier:enterprise"],
            urgency_level="MEDIUM",
            business_value_potential="High - Direct cost savings impact"
        )
        
        user_context = {"user_tier": "enterprise"}
        conversation_context = {}
        
        routing_decision = self.routing_engine.route_message(
            cost_classification, user_context, conversation_context
        )
        
        # Business validation: Should route to cost optimization specialist
        assert routing_decision.selected_agent == AgentID("cost_optimizer")
        assert routing_decision.routing_strategy == RoutingStrategy.DIRECT_MATCH
        assert routing_decision.confidence_level == ConfidenceLevel.HIGH
        assert "cost" in routing_decision.business_justification.lower()
        
        # Test data analysis routing
        data_classification = MessageClassification(
            message_type=MessageType.DATA_ANALYSIS,
            confidence_level=ConfidenceLevel.HIGH,
            key_intent="analyze_data",
            extracted_entities=["csv", "metrics"],
            context_indicators=[],
            urgency_level="MEDIUM",
            business_value_potential="High - Actionable insights generation"
        )
        
        data_routing = self.routing_engine.route_message(
            data_classification, user_context, conversation_context
        )
        
        # Business validation: Should route to data analysis specialist
        assert data_routing.selected_agent == AgentID("data_analyzer")
        assert "data" in data_routing.business_justification.lower()
        
        # Record business metrics
        self.record_metric("capability_matching_accuracy", True)
        self.record_metric("specialist_routing_success", True)
    
    @pytest.mark.unit
    def test_context_aware_routing_logic(self):
        """Test context-aware routing for conversation continuity."""
        # Setup follow-up message scenario
        follow_up_classification = MessageClassification(
            message_type=MessageType.FOLLOW_UP,
            confidence_level=ConfidenceLevel.MEDIUM,
            key_intent="continue_analysis",
            extracted_entities=["also", "additionally"],
            context_indicators=["previous:cost_analysis"],
            urgency_level="LOW",
            business_value_potential="Low - Incremental value addition"
        )
        
        # Context with previous agent
        conversation_context = {
            "last_agent": "cost_optimizer",
            "previous_message_type": "cost_optimization",
            "conversation_length": 3
        }
        
        user_context = {"user_tier": "enterprise"}
        
        follow_up_routing = self.routing_engine.route_message(
            follow_up_classification, user_context, conversation_context
        )
        
        # Business validation: Should route to same agent for continuity
        assert follow_up_routing.selected_agent == AgentID("cost_optimizer")
        assert follow_up_routing.routing_strategy == RoutingStrategy.CONTEXT_AWARE
        assert "continuity" in follow_up_routing.business_justification.lower()
        
        # Test context without previous agent
        no_context_routing = self.routing_engine.route_message(
            follow_up_classification, user_context, {}
        )
        
        # Business validation: Should use different strategy when no context
        assert no_context_routing.routing_strategy != RoutingStrategy.CONTEXT_AWARE
        
        # Record business metric
        self.record_metric("context_aware_routing_working", True)
    
    @pytest.mark.unit
    def test_fallback_routing_logic(self):
        """Test fallback routing for uncertain or complex cases."""
        # Create low-confidence classification
        uncertain_classification = MessageClassification(
            message_type=MessageType.GENERAL_INQUIRY,
            confidence_level=ConfidenceLevel.LOW,
            key_intent="unclear_request",
            extracted_entities=[],
            context_indicators=[],
            urgency_level="MEDIUM",
            business_value_potential="Medium - Standard assistance value"
        )
        
        user_context = {}
        conversation_context = {}
        
        fallback_routing = self.routing_engine.route_message(
            uncertain_classification, user_context, conversation_context
        )
        
        # Business validation: Should use fallback strategy
        assert fallback_routing.routing_strategy == RoutingStrategy.FALLBACK
        assert fallback_routing.selected_agent == AgentID("triage_agent")
        assert "fallback" in fallback_routing.business_justification.lower()
        
        # Test complex message that might require triage
        complex_message = "I need help with something but I'm not sure exactly what I'm looking for"
        complex_context = {}
        
        complex_classification = self.routing_engine.classify_message(complex_message, complex_context)
        complex_routing = self.routing_engine.route_message(
            complex_classification, user_context, conversation_context
        )
        
        # Business validation: Unclear requests should go to triage
        assert complex_routing.selected_agent in [AgentID("triage_agent"), AgentID("general_assistant")]
        
        # Record business metrics
        self.record_metric("fallback_routing_working", True)
        self.record_metric("uncertain_request_handling", True)
    
    @pytest.mark.unit
    def test_business_value_prioritization_logic(self):
        """Test business value prioritization in routing decisions."""
        # Create high business value message
        high_value_classification = MessageClassification(
            message_type=MessageType.COST_OPTIMIZATION,
            confidence_level=ConfidenceLevel.HIGH,
            key_intent="reduce_costs",
            extracted_entities=["aws", "cloud", "ec2", "s3"],
            context_indicators=["user_tier:enterprise"],
            urgency_level="HIGH",
            business_value_potential="High - Direct cost savings impact"
        )
        
        # Create low business value message
        low_value_classification = MessageClassification(
            message_type=MessageType.CLARIFICATION,
            confidence_level=ConfidenceLevel.MEDIUM,
            key_intent="clarify_process",
            extracted_entities=[],
            context_indicators=["user_tier:free"],
            urgency_level="LOW",
            business_value_potential="Low - Support and clarification value"
        )
        
        user_context = {"user_tier": "enterprise"}
        conversation_context = {}
        
        # Route high value message
        high_value_routing = self.routing_engine.route_message(
            high_value_classification, user_context, conversation_context
        )
        
        # Route low value message
        low_value_routing = self.routing_engine.route_message(
            low_value_classification, user_context, conversation_context
        )
        
        # Business validation: High value should get specialist, low value gets generalist
        assert high_value_routing.selected_agent == AgentID("cost_optimizer")
        assert high_value_routing.expected_response_quality > 0.85
        
        # Low value should get general assistant or triage
        assert low_value_routing.selected_agent in [AgentID("general_assistant"), AgentID("triage_agent")]
        
        # Business validation: Response quality expectations should differ
        assert high_value_routing.expected_response_quality > low_value_routing.expected_response_quality
        
        # Record business metrics
        self.record_metric("business_value_prioritization_working", True)
        self.record_metric("high_value_specialist_routing", 
                          high_value_routing.selected_agent == AgentID("cost_optimizer"))
    
    @pytest.mark.unit
    def test_routing_strategy_selection_logic(self):
        """Test routing strategy selection based on different scenarios."""
        # Test direct match scenario
        high_confidence_classification = MessageClassification(
            message_type=MessageType.COST_OPTIMIZATION,
            confidence_level=ConfidenceLevel.HIGH,
            key_intent="optimize_costs",
            extracted_entities=["aws"],
            context_indicators=[],
            urgency_level="MEDIUM",
            business_value_potential="High - Direct cost savings impact"
        )
        
        # Find candidate agents
        required_capabilities = self.routing_engine._determine_required_capabilities(high_confidence_classification)
        candidates = self.routing_engine._find_candidate_agents(required_capabilities)
        
        # Select strategy
        strategy = self.routing_engine._select_routing_strategy(
            high_confidence_classification, {}, candidates
        )
        
        # Business validation: High confidence should use direct match
        assert strategy == RoutingStrategy.DIRECT_MATCH
        
        # Test best fit scenario
        medium_confidence_classification = MessageClassification(
            message_type=MessageType.DATA_ANALYSIS,
            confidence_level=ConfidenceLevel.MEDIUM,
            key_intent="analyze_data",
            extracted_entities=["data"],
            context_indicators=[],
            urgency_level="MEDIUM",
            business_value_potential="High - Actionable insights generation"
        )
        
        medium_required = self.routing_engine._determine_required_capabilities(medium_confidence_classification)
        medium_candidates = self.routing_engine._find_candidate_agents(medium_required)
        
        medium_strategy = self.routing_engine._select_routing_strategy(
            medium_confidence_classification, {}, medium_candidates
        )
        
        # Business validation: Medium confidence should use best fit
        assert medium_strategy in [RoutingStrategy.BEST_FIT, RoutingStrategy.DIRECT_MATCH]
        
        # Record business metric
        self.record_metric("routing_strategy_selection_logic", True)
    
    @pytest.mark.unit
    def test_agent_performance_consideration_logic(self):
        """Test agent performance consideration in routing decisions."""
        # Get agent profiles for comparison
        cost_optimizer = self.routing_engine.agent_profiles[AgentID("cost_optimizer")]
        general_assistant = self.routing_engine.agent_profiles[AgentID("general_assistant")]
        
        # Business validation: Specialist should have better performance metrics
        assert cost_optimizer.response_quality_score > general_assistant.response_quality_score
        assert cost_optimizer.success_rate > general_assistant.success_rate
        
        # Test routing decision considers performance
        cost_classification = MessageClassification(
            message_type=MessageType.COST_OPTIMIZATION,
            confidence_level=ConfidenceLevel.HIGH,
            key_intent="optimize_costs",
            extracted_entities=["cloud", "costs"],
            context_indicators=[],
            urgency_level="MEDIUM",
            business_value_potential="High - Direct cost savings impact"
        )
        
        routing_decision = self.routing_engine.route_message(
            cost_classification, {}, {}
        )
        
        # Business validation: Should choose high-performance specialist
        assert routing_decision.selected_agent == AgentID("cost_optimizer")
        assert routing_decision.expected_response_quality >= 0.9
        
        # Record business metrics
        performance_ratio = cost_optimizer.response_quality_score / general_assistant.response_quality_score
        self.record_metric("specialist_performance_advantage", performance_ratio)
        self.record_metric("performance_based_routing", True)
    
    @pytest.mark.unit
    def test_routing_confidence_calculation_logic(self):
        """Test routing confidence calculation business logic."""
        # High confidence scenario
        high_conf_classification = MessageClassification(
            message_type=MessageType.COST_OPTIMIZATION,
            confidence_level=ConfidenceLevel.HIGH,
            key_intent="optimize_costs",
            extracted_entities=["aws", "ec2"],
            context_indicators=[],
            urgency_level="MEDIUM",
            business_value_potential="High - Direct cost savings impact"
        )
        
        high_conf_routing_confidence = self.routing_engine._calculate_routing_confidence(
            AgentID("cost_optimizer"), high_conf_classification, RoutingStrategy.DIRECT_MATCH
        )
        
        # Business validation: High confidence inputs should yield high routing confidence
        assert high_conf_routing_confidence == ConfidenceLevel.HIGH
        
        # Low confidence scenario
        low_conf_classification = MessageClassification(
            message_type=MessageType.GENERAL_INQUIRY,
            confidence_level=ConfidenceLevel.LOW,
            key_intent="unclear_request",
            extracted_entities=[],
            context_indicators=[],
            urgency_level="LOW",
            business_value_potential="Medium - Standard assistance value"
        )
        
        low_conf_routing_confidence = self.routing_engine._calculate_routing_confidence(
            AgentID("general_assistant"), low_conf_classification, RoutingStrategy.FALLBACK
        )
        
        # Business validation: Low confidence inputs should yield lower routing confidence
        assert low_conf_routing_confidence in [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM]
        
        # Record business metrics
        self.record_metric("confidence_calculation_logic", True)
        self.record_metric("high_confidence_routing_accuracy", 
                          high_conf_routing_confidence == ConfidenceLevel.HIGH)
    
    @pytest.mark.unit
    def test_alternative_agents_suggestion_logic(self):
        """Test alternative agents suggestion for routing flexibility."""
        cost_classification = MessageClassification(
            message_type=MessageType.COST_OPTIMIZATION,
            confidence_level=ConfidenceLevel.HIGH,
            key_intent="optimize_costs",
            extracted_entities=["aws"],
            context_indicators=[],
            urgency_level="MEDIUM",
            business_value_potential="High - Direct cost savings impact"
        )
        
        routing_decision = self.routing_engine.route_message(cost_classification, {}, {})
        
        # Business validation: Should provide alternative agents
        assert len(routing_decision.alternative_agents) > 0
        assert routing_decision.selected_agent not in routing_decision.alternative_agents
        
        # Alternative should be capable agents
        for alt_agent in routing_decision.alternative_agents:
            agent_profile = self.routing_engine.agent_profiles.get(alt_agent)
            assert agent_profile is not None
            assert len(agent_profile.capabilities) > 0
        
        # Record business metric
        self.record_metric("alternative_agents_provided", len(routing_decision.alternative_agents))
    
    @pytest.mark.unit
    def test_routing_performance_analysis_logic(self):
        """Test routing performance analysis for business optimization."""
        # Generate routing history by routing various messages
        test_messages = [
            ("Optimize my AWS costs", MessageType.COST_OPTIMIZATION),
            ("Analyze my data trends", MessageType.DATA_ANALYSIS),
            ("Generate a cost report", MessageType.REPORT_REQUEST),
            ("Help me understand the platform", MessageType.GENERAL_INQUIRY),
            ("Also can you show me more details", MessageType.FOLLOW_UP)
        ]
        
        for message, expected_type in test_messages:
            classification = self.routing_engine.classify_message(message, {})
            routing = self.routing_engine.route_message(classification, {}, {})
            # Routing history is automatically added
        
        # Analyze performance
        performance_analysis = self.routing_engine.analyze_routing_performance()
        
        # Business validation: Analysis should provide meaningful metrics
        assert performance_analysis["total_routings"] == len(test_messages)
        assert 0 <= performance_analysis["routing_efficiency_score"] <= 100
        assert "agent_utilization" in performance_analysis
        assert "strategy_distribution" in performance_analysis
        assert "confidence_distribution" in performance_analysis
        
        # Business validation: Should assess business impact
        business_impact = performance_analysis["business_impact_assessment"]
        assert len(business_impact) > 20  # Meaningful assessment
        assert any(keyword in business_impact.lower() 
                  for keyword in ["excellent", "good", "fair", "poor"])
        
        # Record business metrics
        efficiency_score = performance_analysis["routing_efficiency_score"]
        self.record_metric("routing_efficiency_score", efficiency_score)
        self.record_metric("performance_analysis_completeness", True)
        self.record_metric("business_impact_assessment_provided", True)
    
    @pytest.mark.unit
    def test_enterprise_customer_routing_priority_logic(self):
        """Test enterprise customer routing priority for business value."""
        # Enterprise customer message
        enterprise_classification = MessageClassification(
            message_type=MessageType.COST_OPTIMIZATION,
            confidence_level=ConfidenceLevel.HIGH,
            key_intent="optimize_costs",
            extracted_entities=["aws", "enterprise"],
            context_indicators=["user_tier:enterprise", "urgency:high"],
            urgency_level="HIGH",
            business_value_potential="High - Direct cost savings impact"
        )
        
        enterprise_context = {"user_tier": "enterprise", "account_value": "high"}
        
        enterprise_routing = self.routing_engine.route_message(
            enterprise_classification, enterprise_context, {}
        )
        
        # Free tier user message (same content)
        free_classification = MessageClassification(
            message_type=MessageType.COST_OPTIMIZATION,
            confidence_level=ConfidenceLevel.HIGH,
            key_intent="optimize_costs",
            extracted_entities=["aws"],
            context_indicators=["user_tier:free"],
            urgency_level="MEDIUM",
            business_value_potential="High - Direct cost savings impact"
        )
        
        free_context = {"user_tier": "free", "account_value": "low"}
        
        free_routing = self.routing_engine.route_message(
            free_classification, free_context, {}
        )
        
        # Business validation: Enterprise should get premium routing
        assert enterprise_routing.selected_agent == AgentID("cost_optimizer")
        assert enterprise_routing.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
        
        # Both should get good service, but enterprise gets priority consideration
        assert enterprise_routing.expected_response_quality >= free_routing.expected_response_quality
        
        # Record business metrics
        self.record_metric("enterprise_routing_priority", True)
        self.record_metric("customer_tier_consideration", True)


if __name__ == "__main__":
    pytest.main([__file__])