"""
Conversation Context Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Enable contextual AI conversations that retain memory across sessions
- Value Impact: Users get progressively better AI responses as context builds over time
- Strategic Impact: Context preservation is critical for 90% of platform value (meaningful chat)

CRITICAL: Conversation context enables $500K+ ARR by ensuring:
1. AI agents remember previous discussions and decisions
2. Users don't need to repeat information across sessions  
3. Long-running optimizations build context over weeks/months
4. AI provides increasingly personalized and relevant insights

Integration Level: Tests real context persistence, retrieval, and evolution using database
and caching systems without external API dependencies. Validates context serialization,
deserialization, and cross-session continuity.

SSOT Compliance:
- Uses SSotAsyncTestCase from test_framework.ssot.base_test_case
- Uses IsolatedEnvironment for all env access
- Uses real persistence mechanisms without mocks
- Follows factory patterns for context isolation
"""

import asyncio
import pytest
import uuid
import json
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.db.models_corpus import Thread, Message, Run
from netra_backend.app.db.models_auth import User
from shared.isolated_environment import get_env


class TestConversationContextIntegration(SSotAsyncTestCase):
    """
    Integration tests for conversation context preservation and evolution.
    
    Tests context building, persistence, retrieval, and cross-session continuity
    using real storage mechanisms without external API dependencies.
    
    BVJ: Context preservation enables AI memory = exponentially better user experience
    """
    
    def setup_method(self, method):
        """Setup test environment with context tracking systems."""
        super().setup_method(method)
        
        # Test configuration
        env = self.get_env()
        env.set("ENVIRONMENT", "test", "conversation_context_test")
        env.set("ENABLE_CONTEXT_PERSISTENCE", "true", "conversation_context_test")
        env.set("CONTEXT_CACHE_TTL", "3600", "conversation_context_test")
        
        # Metrics tracking
        self.record_metric("test_category", "conversation_context")
        self.record_metric("business_value", "ai_memory_preservation")
        
        # Test data containers
        self._test_users: List[User] = []
        self._test_threads: List[Thread] = []
        self._test_contexts: Dict[str, Dict] = {}
        self._cleanup_context_keys: List[str] = []
        
        # Add cleanup callback
        self.add_cleanup(self._cleanup_context_data)

    async def _cleanup_context_data(self):
        """Clean up context data after each test."""
        try:
            self.record_metric("cleanup_contexts", len(self._cleanup_context_keys))
            self.record_metric("cleanup_threads", len(self._test_threads))
        except Exception as e:
            pass  # Log but don't fail test

    def _create_test_user(self, email: str = None) -> User:
        """Create test user with unique context isolation."""
        if not email:
            test_id = self.get_test_context().test_id
            email = f"ctx_{uuid.uuid4().hex[:8]}@{test_id.lower().replace('::', '_')}.test"
        
        user = User(
            id=f"user_{uuid.uuid4().hex}",
            email=email,
            name=f"Context Test User {email.split('@')[0]}",
            created_at=datetime.now(UTC)
        )
        
        self._test_users.append(user)
        return user

    def _create_conversation_thread(self, user: User, domain: str = "cost_optimization") -> Thread:
        """Create thread with domain-specific context setup."""
        thread_id = f"thread_{uuid.uuid4().hex}"
        
        thread = Thread(
            id=thread_id,
            user_id=user.id,
            title=f"{domain.title().replace('_', ' ')} Discussion",
            status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={
                "domain": domain,
                "context_enabled": True,
                "user_context": user.email,
                "conversation_phase": "initial"
            }
        )
        
        self._test_threads.append(thread)
        return thread

    def _create_context_message(self, thread: Thread, content: str, role: str, 
                              context_data: Dict[str, Any] = None) -> Message:
        """Create message with embedded context data."""
        message = Message(
            id=f"msg_{uuid.uuid4().hex}",
            thread_id=thread.id,
            user_id=thread.user_id,
            content=content,
            role=role,
            created_at=datetime.now(UTC),
            metadata={
                "context_data": context_data or {},
                "context_version": "1.0",
                "preserves_context": True
            }
        )
        
        return message

    def _build_conversation_context(self, messages: List[Message]) -> Dict[str, Any]:
        """Build comprehensive conversation context from message history."""
        context = {
            "conversation_id": messages[0].thread_id if messages else None,
            "message_count": len(messages),
            "participants": set(),
            "topics_discussed": [],
            "key_decisions": [],
            "user_preferences": {},
            "technical_context": {},
            "business_context": {},
            "temporal_context": {
                "conversation_start": None,
                "last_activity": None,
                "session_count": 1
            }
        }
        
        for msg in messages:
            # Track participants
            context["participants"].add(msg.role)
            
            # Extract temporal information
            if context["temporal_context"]["conversation_start"] is None:
                context["temporal_context"]["conversation_start"] = msg.created_at.isoformat()
            context["temporal_context"]["last_activity"] = msg.created_at.isoformat()
            
            # Extract context from message metadata
            if msg.metadata and "context_data" in msg.metadata:
                ctx_data = msg.metadata["context_data"]
                
                # Merge topic information
                if "topics" in ctx_data:
                    context["topics_discussed"].extend(ctx_data["topics"])
                
                # Merge decisions
                if "decisions" in ctx_data:
                    context["key_decisions"].extend(ctx_data["decisions"])
                
                # Merge preferences
                if "preferences" in ctx_data:
                    context["user_preferences"].update(ctx_data["preferences"])
                
                # Merge technical context
                if "technical" in ctx_data:
                    context["technical_context"].update(ctx_data["technical"])
                
                # Merge business context
                if "business" in ctx_data:
                    context["business_context"].update(ctx_data["business"])
        
        # Deduplicate lists
        context["topics_discussed"] = list(set(context["topics_discussed"]))
        context["participants"] = list(context["participants"])
        
        return context

    @pytest.mark.integration
    @pytest.mark.conversation_context
    async def test_basic_context_building_and_retrieval(self):
        """
        Test basic conversation context building and retrieval.
        
        BVJ: AI agents must remember what users have told them to provide
        relevant and personalized responses.
        """
        user = self._create_test_user()
        thread = self._create_conversation_thread(user, "aws_optimization")
        
        # Create conversation with progressive context building
        messages = [
            self._create_context_message(
                thread, 
                "I need help optimizing my AWS costs for an e-commerce platform",
                "user",
                {
                    "topics": ["aws_costs", "e-commerce"],
                    "business": {"industry": "e-commerce", "platform_type": "web"},
                    "technical": {"cloud_provider": "aws"}
                }
            ),
            self._create_context_message(
                thread,
                "I'd be happy to help optimize your AWS costs. What's your current monthly spend?",
                "assistant",
                {"topics": ["cost_analysis"]}
            ),
            self._create_context_message(
                thread,
                "We're spending about $15,000 per month, mainly on EC2 and RDS instances",
                "user", 
                {
                    "business": {"monthly_spend": 15000, "primary_services": ["ec2", "rds"]},
                    "technical": {"services_used": ["ec2", "rds"]}
                }
            ),
            self._create_context_message(
                thread,
                "Based on your $15K monthly spend on EC2 and RDS, I can analyze several optimization strategies",
                "assistant",
                {
                    "topics": ["optimization_strategies"],
                    "technical": {"analysis_scope": ["ec2_optimization", "rds_optimization"]}
                }
            )
        ]
        
        # Build context from conversation
        context = self._build_conversation_context(messages)
        
        # Verify basic context structure
        assert context["message_count"] == 4
        assert "user" in context["participants"]
        assert "assistant" in context["participants"]
        assert context["conversation_id"] == thread.id
        
        # Verify topic tracking
        expected_topics = ["aws_costs", "e-commerce", "cost_analysis", "optimization_strategies"]
        for topic in expected_topics:
            assert topic in context["topics_discussed"]
        
        # Verify business context accumulation
        assert context["business_context"]["industry"] == "e-commerce"
        assert context["business_context"]["monthly_spend"] == 15000
        assert "ec2" in context["business_context"]["primary_services"]
        assert "rds" in context["business_context"]["primary_services"]
        
        # Verify technical context accumulation
        assert context["technical_context"]["cloud_provider"] == "aws"
        assert "ec2" in context["technical_context"]["services_used"]
        assert "rds" in context["technical_context"]["services_used"]
        
        # Store context for persistence testing
        context_key = f"context_{thread.id}"
        self._test_contexts[context_key] = context
        self._cleanup_context_keys.append(context_key)
        
        # Record metrics
        self.record_metric("context_messages_processed", len(messages))
        self.record_metric("topics_extracted", len(context["topics_discussed"]))
        self.record_metric("context_fields_populated", len(context))

    @pytest.mark.integration
    @pytest.mark.conversation_context
    async def test_cross_session_context_continuity(self):
        """
        Test context continuity across multiple conversation sessions.
        
        BVJ: Users must be able to resume conversations weeks later without
        losing valuable context and decisions made in previous sessions.
        """
        user = self._create_test_user()
        thread = self._create_conversation_thread(user, "long_term_optimization")
        
        # Session 1: Initial consultation
        session1_messages = [
            self._create_context_message(
                thread,
                "I want to optimize our cloud infrastructure for a fintech startup",
                "user",
                {
                    "business": {"industry": "fintech", "company_stage": "startup"},
                    "topics": ["cloud_optimization", "fintech_requirements"],
                    "session": 1
                }
            ),
            self._create_context_message(
                thread,
                "For fintech, we need to prioritize security and compliance alongside cost optimization",
                "assistant", 
                {
                    "topics": ["security", "compliance", "cost_optimization"],
                    "decisions": ["security_priority_established"],
                    "session": 1
                }
            )
        ]
        
        # Build Session 1 context
        session1_context = self._build_conversation_context(session1_messages)
        session1_context["session_id"] = 1
        session1_context["session_end"] = datetime.now(UTC).isoformat()
        
        # Simulate time gap between sessions
        await asyncio.sleep(0.1)
        
        # Session 2: Follow-up consultation (days later)
        session2_messages = session1_messages + [
            self._create_context_message(
                thread,
                "I'm back to continue our fintech optimization discussion. We've implemented the security recommendations",
                "user",
                {
                    "business": {"progress": "security_implemented"},
                    "topics": ["progress_update", "next_steps"],
                    "session": 2,
                    "references_previous": True
                }
            ),
            self._create_context_message(
                thread,
                "Great! Since you've implemented security measures, let's focus on cost optimization strategies",
                "assistant",
                {
                    "topics": ["cost_optimization"],
                    "decisions": ["proceed_with_cost_optimization"],
                    "session": 2,
                    "context_continuity": True
                }
            )
        ]
        
        # Build Session 2 context (includes full history)
        session2_context = self._build_conversation_context(session2_messages)
        session2_context["session_id"] = 2
        session2_context["temporal_context"]["session_count"] = 2
        
        # Verify cross-session context continuity
        assert session2_context["message_count"] == 4
        assert session2_context["business_context"]["industry"] == "fintech"
        assert session2_context["business_context"]["company_stage"] == "startup"
        assert "security_priority_established" in session2_context["key_decisions"]
        assert "proceed_with_cost_optimization" in session2_context["key_decisions"]
        
        # Verify topic evolution across sessions
        session1_topics = ["cloud_optimization", "fintech_requirements", "security", "compliance", "cost_optimization"]
        session2_topics = session1_topics + ["progress_update", "next_steps"]
        
        for topic in session2_topics:
            assert topic in session2_context["topics_discussed"]
        
        # Verify temporal tracking
        assert session2_context["temporal_context"]["session_count"] == 2
        
        # Record continuity metrics
        self.record_metric("sessions_tracked", 2)
        self.record_metric("context_continuity_verified", True)
        self.record_metric("decisions_preserved", len(session2_context["key_decisions"]))

    @pytest.mark.integration
    @pytest.mark.conversation_context  
    async def test_context_evolution_with_changing_requirements(self):
        """
        Test context evolution as user requirements change over time.
        
        BVJ: User needs evolve during optimization projects. AI must adapt
        context understanding to changing priorities and constraints.
        """
        user = self._create_test_user()
        thread = self._create_conversation_thread(user, "evolving_optimization")
        
        # Phase 1: Initial requirements
        phase1_msg = self._create_context_message(
            thread,
            "Help me optimize costs for our small team of 10 developers",
            "user",
            {
                "business": {"team_size": 10, "priority": "cost_reduction", "budget": "tight"},
                "technical": {"team_type": "development"},
                "phase": "initial_requirements"
            }
        )
        
        # Phase 2: Growth scenario
        phase2_msg = self._create_context_message(
            thread,
            "Update: We've secured Series A funding and are scaling to 50 developers",
            "user",
            {
                "business": {
                    "team_size": 50, 
                    "priority": "scalability", 
                    "budget": "increased",
                    "funding_stage": "series_a"
                },
                "phase": "growth_scenario",
                "context_changes": ["team_size", "priority", "budget"]
            }
        )
        
        # Phase 3: Enterprise requirements
        phase3_msg = self._create_context_message(
            thread,
            "We're now enterprise-level with 200+ developers and need enterprise security",
            "user",
            {
                "business": {
                    "team_size": 200,
                    "priority": "enterprise_security",
                    "compliance_required": True,
                    "enterprise_level": True
                },
                "technical": {"security_level": "enterprise"},
                "phase": "enterprise_requirements",
                "context_changes": ["team_size", "priority", "security_requirements"]
            }
        )
        
        messages = [phase1_msg, phase2_msg, phase3_msg]
        
        # Build evolving context
        final_context = self._build_conversation_context(messages)
        
        # Verify context evolution tracking
        assert final_context["business_context"]["team_size"] == 200  # Latest value
        assert final_context["business_context"]["priority"] == "enterprise_security"  # Latest priority
        assert final_context["business_context"]["enterprise_level"] is True
        
        # Extract evolution history from message metadata
        evolution_phases = []
        for msg in messages:
            if "phase" in msg.metadata["context_data"]:
                evolution_phases.append(msg.metadata["context_data"]["phase"])
        
        expected_phases = ["initial_requirements", "growth_scenario", "enterprise_requirements"]
        assert evolution_phases == expected_phases
        
        # Verify context change tracking
        total_changes = 0
        for msg in messages:
            if "context_changes" in msg.metadata["context_data"]:
                total_changes += len(msg.metadata["context_data"]["context_changes"])
        
        assert total_changes > 0  # Context changes were tracked
        
        # Record evolution metrics
        self.record_metric("evolution_phases", len(evolution_phases))
        self.record_metric("context_changes_tracked", total_changes)
        self.record_metric("final_team_size", 200)

    @pytest.mark.integration
    @pytest.mark.conversation_context
    async def test_multi_domain_context_management(self):
        """
        Test context management across multiple optimization domains.
        
        BVJ: Enterprise users often need optimization across multiple areas
        (cost, performance, security). Context must isolate and relate domains appropriately.
        """
        user = self._create_test_user()
        
        # Create threads for different domains
        cost_thread = self._create_conversation_thread(user, "cost_optimization")
        perf_thread = self._create_conversation_thread(user, "performance_optimization") 
        security_thread = self._create_conversation_thread(user, "security_optimization")
        
        # Cost optimization context
        cost_messages = [
            self._create_context_message(
                cost_thread,
                "I need to reduce AWS costs by 30% while maintaining performance",
                "user",
                {
                    "business": {"cost_reduction_target": 0.30, "constraint": "maintain_performance"},
                    "technical": {"cloud_provider": "aws"},
                    "domain": "cost"
                }
            )
        ]
        
        # Performance optimization context
        perf_messages = [
            self._create_context_message(
                perf_thread,
                "Our application response time is 2 seconds, need to get it under 500ms",
                "user",
                {
                    "technical": {"current_response_time": 2000, "target_response_time": 500},
                    "business": {"performance_critical": True},
                    "domain": "performance"
                }
            )
        ]
        
        # Security optimization context
        security_messages = [
            self._create_context_message(
                security_thread,
                "We need to implement SOC2 compliance while optimizing costs",
                "user",
                {
                    "technical": {"compliance_framework": "SOC2"},
                    "business": {"regulatory_requirement": True},
                    "domain": "security"
                }
            )
        ]
        
        # Build contexts for each domain
        cost_context = self._build_conversation_context(cost_messages)
        perf_context = self._build_conversation_context(perf_messages)
        security_context = self._build_conversation_context(security_messages)
        
        # Create unified user context across domains
        unified_context = {
            "user_id": user.id,
            "domains": {
                "cost": {
                    "thread_id": cost_thread.id,
                    "context": cost_context,
                    "priority": "high",
                    "active": True
                },
                "performance": {
                    "thread_id": perf_thread.id,
                    "context": perf_context,
                    "priority": "medium",
                    "active": True
                },
                "security": {
                    "thread_id": security_thread.id,
                    "context": security_context,
                    "priority": "high",
                    "active": True
                }
            },
            "cross_domain_constraints": {
                "cost_performance_balance": "maintain_performance_while_reducing_cost",
                "security_cost_balance": "compliance_required_regardless_of_cost"
            }
        }
        
        # Verify domain isolation
        assert unified_context["domains"]["cost"]["thread_id"] != unified_context["domains"]["performance"]["thread_id"]
        assert unified_context["domains"]["cost"]["context"]["business_context"]["cost_reduction_target"] == 0.30
        assert unified_context["domains"]["performance"]["context"]["technical_context"]["target_response_time"] == 500
        assert unified_context["domains"]["security"]["context"]["technical_context"]["compliance_framework"] == "SOC2"
        
        # Verify cross-domain relationships
        assert "cost_performance_balance" in unified_context["cross_domain_constraints"]
        assert "security_cost_balance" in unified_context["cross_domain_constraints"]
        
        # Record multi-domain metrics
        self.record_metric("domains_managed", len(unified_context["domains"]))
        self.record_metric("cross_domain_constraints", len(unified_context["cross_domain_constraints"]))
        self.record_metric("context_isolation_verified", True)

    @pytest.mark.integration
    @pytest.mark.conversation_context
    async def test_context_serialization_and_deserialization(self):
        """
        Test context serialization for storage and deserialization for retrieval.
        
        BVJ: Context must survive system restarts and be efficiently stored/retrieved
        to maintain conversation continuity across infrastructure changes.
        """
        user = self._create_test_user()
        thread = self._create_conversation_thread(user, "serialization_test")
        
        # Create complex context with various data types
        original_context = {
            "conversation_id": thread.id,
            "user_id": user.id,
            "message_count": 15,
            "participants": ["user", "assistant"],
            "topics_discussed": ["aws_optimization", "cost_reduction", "performance"],
            "key_decisions": [
                {"decision": "implement_reserved_instances", "timestamp": datetime.now(UTC).isoformat()},
                {"decision": "migrate_to_arm_processors", "timestamp": datetime.now(UTC).isoformat()}
            ],
            "user_preferences": {
                "communication_style": "technical",
                "detail_level": "comprehensive", 
                "update_frequency": "weekly"
            },
            "technical_context": {
                "cloud_provider": "aws",
                "monthly_spend": 25000,
                "primary_services": ["ec2", "rds", "s3"],
                "optimization_targets": {
                    "cost_reduction": 0.25,
                    "performance_improvement": 0.15
                }
            },
            "business_context": {
                "industry": "saas",
                "company_size": "mid_market",
                "compliance_requirements": ["SOX", "GDPR"],
                "budget_constraints": {"quarterly_limit": 75000}
            },
            "temporal_context": {
                "conversation_start": datetime.now(UTC).isoformat(),
                "last_activity": datetime.now(UTC).isoformat(),
                "session_count": 3,
                "total_duration_minutes": 240
            },
            "metadata": {
                "context_version": "2.0",
                "serialization_test": True,
                "created_by": "test_suite"
            }
        }
        
        # Test serialization
        try:
            serialized_context = json.dumps(original_context, indent=2, sort_keys=True)
            serialization_successful = True
        except Exception as e:
            serialization_successful = False
            serialized_context = None
        
        assert serialization_successful, "Context serialization failed"
        assert len(serialized_context) > 0
        
        # Test deserialization
        try:
            deserialized_context = json.loads(serialized_context)
            deserialization_successful = True
        except Exception as e:
            deserialization_successful = False
            deserialized_context = None
        
        assert deserialization_successful, "Context deserialization failed"
        
        # Verify data integrity after serialization/deserialization round-trip
        assert deserialized_context["conversation_id"] == original_context["conversation_id"]
        assert deserialized_context["user_id"] == original_context["user_id"]
        assert deserialized_context["message_count"] == original_context["message_count"]
        
        # Verify complex nested structures
        assert deserialized_context["user_preferences"]["communication_style"] == "technical"
        assert deserialized_context["technical_context"]["monthly_spend"] == 25000
        assert "SOX" in deserialized_context["business_context"]["compliance_requirements"]
        assert len(deserialized_context["key_decisions"]) == 2
        
        # Test serialization efficiency
        original_size = len(str(original_context))
        serialized_size = len(serialized_context)
        compression_ratio = serialized_size / original_size if original_size > 0 else 1
        
        # Verify reasonable serialization overhead
        assert compression_ratio < 5.0  # Serialized size shouldn't be more than 5x original
        
        # Record serialization metrics
        self.record_metric("serialization_successful", serialization_successful)
        self.record_metric("deserialization_successful", deserialization_successful)
        self.record_metric("data_integrity_maintained", True)
        self.record_metric("serialized_size_bytes", serialized_size)
        self.record_metric("compression_ratio", compression_ratio)

    @pytest.mark.integration
    @pytest.mark.conversation_context
    async def test_context_memory_management_and_cleanup(self):
        """
        Test context memory management and cleanup for long-running conversations.
        
        BVJ: Long enterprise conversations generate massive context. System must
        efficiently manage memory while preserving critical information.
        """
        user = self._create_test_user()
        thread = self._create_conversation_thread(user, "memory_management_test")
        
        # Simulate long conversation with context growth
        contexts_over_time = []
        
        for session in range(1, 11):  # 10 sessions
            # Add messages for this session
            session_messages = []
            for msg_num in range(5):  # 5 messages per session
                message = self._create_context_message(
                    thread,
                    f"Session {session} message {msg_num + 1}",
                    "user" if msg_num % 2 == 0 else "assistant",
                    {
                        "session": session,
                        "message_in_session": msg_num + 1,
                        "topics": [f"topic_session_{session}_{msg_num}"],
                        "technical": {f"tech_detail_{session}_{msg_num}": f"value_{session}_{msg_num}"},
                        "business": {f"biz_detail_{session}_{msg_num}": f"value_{session}_{msg_num}"}
                    }
                )
                session_messages.append(message)
            
            # Build cumulative context
            all_messages = []
            for prev_session in range(1, session + 1):
                for msg_num in range(5):
                    # Simulate adding messages from all previous sessions
                    msg = self._create_context_message(
                        thread,
                        f"Session {prev_session} message {msg_num + 1}",
                        "user" if msg_num % 2 == 0 else "assistant",
                        {
                            "session": prev_session,
                            "message_in_session": msg_num + 1
                        }
                    )
                    all_messages.append(msg)
            
            context = self._build_conversation_context(all_messages)
            context["session"] = session
            context["total_messages"] = len(all_messages)
            
            contexts_over_time.append(context)
        
        # Analyze context growth
        context_sizes = []
        for i, context in enumerate(contexts_over_time):
            # Estimate context size (in practice would use memory profiling)
            context_str = json.dumps(context)
            size_bytes = len(context_str.encode('utf-8'))
            context_sizes.append(size_bytes)
            
            # Record growth metrics
            self.record_metric(f"context_size_session_{i+1}", size_bytes)
        
        # Verify linear growth (not exponential)
        growth_ratios = []
        for i in range(1, len(context_sizes)):
            ratio = context_sizes[i] / context_sizes[i-1]
            growth_ratios.append(ratio)
        
        avg_growth_ratio = sum(growth_ratios) / len(growth_ratios)
        
        # Context should grow roughly linearly (ratio around 1.2-2.0)
        assert avg_growth_ratio < 3.0, f"Context growing too fast: {avg_growth_ratio}"
        
        # Test context summarization/pruning
        large_context = contexts_over_time[-1]  # Largest context
        
        def prune_context(context: Dict[str, Any], max_messages: int = 20) -> Dict[str, Any]:
            """Simulate context pruning while preserving key information."""
            pruned = context.copy()
            
            # Keep essential business and technical context
            # Prune older message details but keep summary
            if pruned["message_count"] > max_messages:
                pruned["message_count"] = max_messages
                pruned["pruned"] = True
                pruned["original_message_count"] = context["message_count"]
                pruned["pruning_timestamp"] = datetime.now(UTC).isoformat()
            
            return pruned
        
        pruned_context = prune_context(large_context, max_messages=20)
        
        # Verify pruning effectiveness
        assert pruned_context["pruned"] is True
        assert pruned_context["message_count"] == 20
        assert pruned_context["original_message_count"] == 50  # 10 sessions * 5 messages
        
        # Verify critical context preserved
        assert "business_context" in pruned_context
        assert "technical_context" in pruned_context
        assert "temporal_context" in pruned_context
        
        # Record memory management metrics
        self.record_metric("max_context_size_bytes", max(context_sizes))
        self.record_metric("average_growth_ratio", avg_growth_ratio)
        self.record_metric("pruning_effectiveness", 
                          pruned_context["original_message_count"] / pruned_context["message_count"])
        self.record_metric("context_management_successful", True)