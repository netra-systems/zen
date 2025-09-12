"""
Test State Serialization and Deserialization - State Management & Context Swimlane

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise) - Core data persistence and transfer functionality
- Business Goal: Ensure reliable state preservation across system boundaries and storage layers
- Value Impact: Enables conversation continuity, state recovery, and cross-service communication
- Strategic Impact: CRITICAL - State serialization enables all persistent AI interactions and system reliability

This test suite validates comprehensive state serialization/deserialization:
- Complex state object serialization with nested data structures
- JSON serialization for cache and API communication
- Binary serialization for efficient storage
- State versioning and migration compatibility
- Large state object handling and compression
- Data integrity validation across serialization boundaries
- Performance optimization for serialization operations
"""

import asyncio
import gzip
import json
import logging
import pickle
import pytest
import time
import uuid
import zlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from decimal import Decimal

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import RealServicesManager, get_real_services
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.session_management import UserSessionManager, get_user_session_tracker
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID

logger = logging.getLogger(__name__)


@dataclass
class ComplexConversationState:
    """Complex state object for serialization testing."""
    user_id: str
    thread_id: str
    run_id: str
    conversation_metadata: Dict[str, Any]
    message_history: List[Dict[str, Any]]
    ai_context: Dict[str, Any]
    user_preferences: Dict[str, Any]
    performance_metrics: Dict[str, Union[int, float, str]]
    created_at: datetime
    updated_at: datetime
    version: int = 1


class StateSerializationHelper:
    """Helper class for state serialization operations."""
    
    @staticmethod
    def serialize_to_json(state_obj: Any) -> str:
        """Serialize state object to JSON string."""
        if isinstance(state_obj, ComplexConversationState):
            # Convert dataclass to dict with datetime handling
            state_dict = asdict(state_obj)
            state_dict['created_at'] = state_obj.created_at.isoformat()
            state_dict['updated_at'] = state_obj.updated_at.isoformat()
        else:
            state_dict = state_obj
            
        return json.dumps(state_dict, default=str, ensure_ascii=False)
    
    @staticmethod
    def deserialize_from_json(json_str: str, target_class=None) -> Any:
        """Deserialize JSON string back to state object."""
        state_dict = json.loads(json_str)
        
        if target_class == ComplexConversationState:
            # Handle datetime conversion
            if 'created_at' in state_dict:
                state_dict['created_at'] = datetime.fromisoformat(state_dict['created_at'])
            if 'updated_at' in state_dict:
                state_dict['updated_at'] = datetime.fromisoformat(state_dict['updated_at'])
            return ComplexConversationState(**state_dict)
        
        return state_dict
    
    @staticmethod
    def serialize_to_binary(state_obj: Any) -> bytes:
        """Serialize state object to binary format."""
        return pickle.dumps(state_obj)
    
    @staticmethod
    def deserialize_from_binary(binary_data: bytes) -> Any:
        """Deserialize binary data back to state object."""
        return pickle.loads(binary_data)
    
    @staticmethod
    def compress_state(serialized_data: Union[str, bytes]) -> bytes:
        """Compress serialized state data."""
        if isinstance(serialized_data, str):
            serialized_data = serialized_data.encode('utf-8')
        return gzip.compress(serialized_data)
    
    @staticmethod
    def decompress_state(compressed_data: bytes) -> bytes:
        """Decompress state data."""
        return gzip.decompress(compressed_data)


@pytest.fixture
async def real_services_fixture():
    """SSOT fixture for real services integration testing."""
    async with get_real_services() as services:
        yield services


@pytest.fixture
async def auth_helper():
    """E2E authentication helper fixture."""
    return E2EAuthHelper(environment="test")


@pytest.fixture
async def id_generator():
    """Unified ID generator fixture."""
    return UnifiedIdGenerator()


@pytest.fixture
def serialization_helper():
    """State serialization helper fixture."""
    return StateSerializationHelper()


class TestStateSerializationDeserialization(BaseIntegrationTest):
    """
    Comprehensive state serialization and deserialization tests.
    
    CRITICAL: Tests use REAL services only - Redis and PostgreSQL for actual persistence validation.
    All tests must validate actual business value through reliable state serialization.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complex_state_json_serialization(self, real_services_fixture, auth_helper, id_generator, serialization_helper):
        """
        Test complex state object JSON serialization with real persistence.
        
        Business Value: Validates JSON serialization for API communication and cache storage.
        """
        # Create authenticated user and context
        auth_user = await auth_helper.create_authenticated_user(
            email=f"serialization_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        thread_id, run_id, request_id = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id,
            operation="json_serialization_test"
        )
        
        # Create complex conversation state with realistic data
        complex_state = ComplexConversationState(
            user_id=auth_user.user_id,
            thread_id=thread_id,
            run_id=run_id,
            conversation_metadata={
                'conversation_type': 'cost_optimization',
                'business_domain': 'aws_infrastructure',
                'optimization_goals': ['reduce_costs', 'improve_performance', 'enhance_security'],
                'session_context': {
                    'user_tier': 'enterprise',
                    'previous_conversations': 3,
                    'satisfaction_score': 4.8,
                    'engagement_level': 'high'
                },
                'ai_agent_config': {
                    'model': 'gpt-4',
                    'temperature': 0.7,
                    'max_tokens': 2000,
                    'reasoning_depth': 'deep'
                }
            },
            message_history=[
                {
                    'id': f'{run_id}_msg_0',
                    'role': 'user',
                    'content': 'I need help optimizing my AWS costs. My monthly bill is $8,000.',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'metadata': {'urgency': 'high', 'domain': 'aws_costs'}
                },
                {
                    'id': f'{run_id}_msg_1',
                    'role': 'assistant',
                    'content': 'I can help you optimize your AWS costs. Let me analyze your current usage patterns and identify savings opportunities.',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'metadata': {'analysis_type': 'cost_optimization', 'tools_used': ['cost_analyzer']}
                },
                {
                    'id': f'{run_id}_msg_2',
                    'role': 'user',
                    'content': 'My main costs are EC2 instances (60%) and S3 storage (25%). I have 50 instances running.',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'metadata': {'data_provided': True, 'cost_breakdown': True}
                }
            ],
            ai_context={
                'current_analysis': {
                    'ec2_optimization_potential': 0.35,  # 35% savings potential
                    'storage_optimization_potential': 0.20,
                    'recommended_actions': [
                        'implement_reserved_instances',
                        'right_size_instances',
                        'lifecycle_policies_s3',
                        'spot_instances_non_critical'
                    ]
                },
                'conversation_flow': {
                    'current_stage': 'analysis_complete',
                    'next_actions': ['present_recommendations', 'implementation_planning'],
                    'confidence_level': 0.92
                },
                'learned_context': {
                    'user_aws_experience': 'intermediate',
                    'risk_tolerance': 'moderate',
                    'implementation_preference': 'gradual'
                }
            },
            user_preferences={
                'communication_style': 'detailed_technical',
                'notification_frequency': 'real_time',
                'data_retention': 'extended',
                'privacy_level': 'standard',
                'preferred_savings_approach': 'conservative_first'
            },
            performance_metrics={
                'response_time_ms': 850,
                'tokens_used': 1247,
                'cost_per_interaction': 0.0234,
                'satisfaction_predicted': 4.6,
                'engagement_score': 8.9,
                'business_value_score': 9.2
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Test JSON serialization
        serialized_json = serialization_helper.serialize_to_json(complex_state)
        assert isinstance(serialized_json, str)
        assert len(serialized_json) > 1000  # Ensure substantial data
        
        # Store serialized state in real Redis
        cache_key = f"complex_state:{auth_user.user_id}:{thread_id}"
        await real_services_fixture.redis.set(cache_key, serialized_json, ex=3600)
        
        # Retrieve and deserialize from Redis
        cached_json = await real_services_fixture.redis.get(cache_key)
        assert cached_json is not None
        
        deserialized_state = serialization_helper.deserialize_from_json(cached_json, ComplexConversationState)
        
        # Validate complete round-trip serialization integrity
        assert deserialized_state.user_id == complex_state.user_id
        assert deserialized_state.thread_id == complex_state.thread_id
        assert deserialized_state.run_id == complex_state.run_id
        
        # Validate complex nested data structures
        assert len(deserialized_state.message_history) == len(complex_state.message_history)
        for i, (original_msg, deserialized_msg) in enumerate(zip(complex_state.message_history, deserialized_state.message_history)):
            assert deserialized_msg['role'] == original_msg['role']
            assert deserialized_msg['content'] == original_msg['content']
            assert deserialized_msg['metadata'] == original_msg['metadata']
        
        # Validate AI context preservation
        assert deserialized_state.ai_context['current_analysis']['ec2_optimization_potential'] == 0.35
        assert len(deserialized_state.ai_context['current_analysis']['recommended_actions']) == 4
        assert deserialized_state.ai_context['conversation_flow']['confidence_level'] == 0.92
        
        # Validate performance metrics
        assert deserialized_state.performance_metrics['response_time_ms'] == 850
        assert deserialized_state.performance_metrics['business_value_score'] == 9.2
        
        # Validate datetime handling
        assert isinstance(deserialized_state.created_at, datetime)
        assert isinstance(deserialized_state.updated_at, datetime)
        
        # Store in PostgreSQL as well (JSON column)
        async with real_services_fixture.postgres.transaction() as tx:
            await tx.execute("""
                INSERT INTO auth.users (id, email, name, is_active, created_at)
                VALUES ($1, $2, $3, true, $4)
                ON CONFLICT (email) DO NOTHING
            """, auth_user.user_id, auth_user.email, auth_user.full_name, datetime.now(timezone.utc))
            
            await tx.execute("""
                CREATE TABLE IF NOT EXISTS conversation_states (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    state_data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            state_id = f"{auth_user.user_id}_{thread_id}"
            await tx.execute("""
                INSERT INTO conversation_states (id, user_id, thread_id, state_data)
                VALUES ($1, $2, $3, $4)
            """, state_id, auth_user.user_id, thread_id, serialized_json)
        
        # Retrieve from PostgreSQL and validate
        db_state_data = await real_services_fixture.postgres.fetchval("""
            SELECT state_data FROM conversation_states WHERE id = $1
        """, state_id)
        
        assert db_state_data is not None
        db_deserialized_state = serialization_helper.deserialize_from_json(db_state_data, ComplexConversationState)
        
        # Validate database round-trip
        assert db_deserialized_state.user_id == complex_state.user_id
        assert len(db_deserialized_state.ai_context['current_analysis']['recommended_actions']) == 4
        
        # Clean up test table
        await real_services_fixture.postgres.execute("DROP TABLE IF EXISTS conversation_states")
        
        # BUSINESS VALUE VALIDATION: JSON serialization enables API communication
        self.assert_business_value_delivered({
            'serialization_successful': True,
            'data_integrity_maintained': True,
            'cache_persistence_verified': True,
            'database_persistence_verified': True,
            'complex_data_structures_preserved': len(complex_state.message_history) == len(deserialized_state.message_history)
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_binary_serialization_with_compression(self, real_services_fixture, auth_helper, id_generator, serialization_helper):
        """
        Test binary serialization with compression for efficient storage.
        
        Business Value: Validates efficient storage of large state objects.
        """
        # Create large conversation state for compression testing
        auth_user = await auth_helper.create_authenticated_user(
            email=f"binary_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        thread_id, run_id, _ = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id,
            operation="binary_serialization_test"
        )
        
        # Generate large message history for compression benefits
        large_message_history = []
        for i in range(100):  # 100 messages for substantial data
            message_content = f"Message {i}: " + "This is a detailed message with substantial content. " * 20
            large_message_history.append({
                'id': f'{run_id}_msg_{i}',
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': message_content,
                'timestamp': (datetime.now(timezone.utc) - timedelta(minutes=100-i)).isoformat(),
                'metadata': {
                    'length': len(message_content),
                    'sequence': i,
                    'processing_time_ms': 100 + (i * 10),
                    'tokens_used': 50 + (i * 5)
                }
            })
        
        # Create large AI context with detailed analysis
        large_ai_context = {
            'conversation_analysis': {
                'topics_discussed': [f'topic_{i}' for i in range(50)],
                'sentiment_analysis': [{'message_id': i, 'sentiment': 'positive', 'confidence': 0.8} for i in range(100)],
                'entity_extraction': {f'entity_{i}': {'type': 'business', 'confidence': 0.9} for i in range(30)},
                'optimization_recommendations': [
                    {
                        'recommendation_id': f'rec_{i}',
                        'category': 'cost_optimization',
                        'savings_potential': 1000 + (i * 100),
                        'implementation_complexity': 'medium',
                        'detailed_analysis': 'Detailed analysis: ' + 'Analysis content. ' * 50
                    } for i in range(20)
                ]
            },
            'user_modeling': {
                'interaction_patterns': {f'pattern_{i}': {'frequency': i, 'preference': 0.8} for i in range(25)},
                'preference_learning': {f'pref_{i}': {'value': f'value_{i}', 'confidence': 0.9} for i in range(30)},
                'expertise_assessment': {
                    'aws_services': {f'service_{i}': {'expertise_level': 'intermediate'} for i in range(40)},
                    'optimization_areas': {f'area_{i}': {'experience': 'moderate'} for i in range(15)}
                }
            }
        }
        
        large_state = ComplexConversationState(
            user_id=auth_user.user_id,
            thread_id=thread_id,
            run_id=run_id,
            conversation_metadata={'conversation_type': 'large_scale_optimization'},
            message_history=large_message_history,
            ai_context=large_ai_context,
            user_preferences={'data_retention': 'extended'},
            performance_metrics={'total_tokens': 50000, 'processing_time': 30.5},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Test binary serialization
        binary_data = serialization_helper.serialize_to_binary(large_state)
        assert isinstance(binary_data, bytes)
        original_size = len(binary_data)
        
        # Test compression
        compressed_data = serialization_helper.compress_state(binary_data)
        compressed_size = len(compressed_data)
        compression_ratio = compressed_size / original_size
        
        # Compression should be significant for large repetitive data
        assert compression_ratio < 0.8, f"Compression not effective: {compression_ratio}"
        
        # Store compressed data in Redis
        storage_key = f"compressed_state:{auth_user.user_id}:{thread_id}"
        await real_services_fixture.redis.set(storage_key, compressed_data, ex=3600)
        
        # Retrieve and decompress
        stored_compressed = await real_services_fixture.redis.get(storage_key)
        assert stored_compressed == compressed_data
        
        decompressed_data = serialization_helper.decompress_state(stored_compressed)
        assert len(decompressed_data) == original_size
        
        # Deserialize
        recovered_state = serialization_helper.deserialize_from_binary(decompressed_data)
        
        # Validate complete round-trip with compression
        assert recovered_state.user_id == large_state.user_id
        assert recovered_state.thread_id == large_state.thread_id
        assert len(recovered_state.message_history) == 100
        assert len(recovered_state.ai_context['conversation_analysis']['topics_discussed']) == 50
        
        # Validate specific data integrity
        for i in range(0, 100, 10):  # Sample every 10th message
            original_msg = large_state.message_history[i]
            recovered_msg = recovered_state.message_history[i]
            assert recovered_msg['id'] == original_msg['id']
            assert recovered_msg['content'] == original_msg['content']
            assert recovered_msg['metadata']['sequence'] == i
        
        # Performance measurement
        serialization_start = time.time()
        for _ in range(10):  # 10 serialization cycles for timing
            binary_data = serialization_helper.serialize_to_binary(large_state)
            compressed_data = serialization_helper.compress_state(binary_data)
        serialization_time = (time.time() - serialization_start) / 10
        
        deserialization_start = time.time()
        for _ in range(10):  # 10 deserialization cycles for timing
            decompressed = serialization_helper.decompress_state(compressed_data)
            recovered = serialization_helper.deserialize_from_binary(decompressed)
        deserialization_time = (time.time() - deserialization_start) / 10
        
        # Performance should be reasonable (< 100ms for this size)
        assert serialization_time < 0.1, f"Serialization too slow: {serialization_time}s"
        assert deserialization_time < 0.1, f"Deserialization too slow: {deserialization_time}s"
        
        # BUSINESS VALUE VALIDATION: Binary compression enables efficient storage
        self.assert_business_value_delivered({
            'data_size_original_bytes': original_size,
            'data_size_compressed_bytes': compressed_size,
            'compression_ratio': compression_ratio,
            'serialization_performance_ms': serialization_time * 1000,
            'deserialization_performance_ms': deserialization_time * 1000,
            'storage_efficiency_achieved': compression_ratio < 0.8
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_versioning_and_migration_compatibility(self, real_services_fixture, auth_helper, id_generator, serialization_helper):
        """
        Test state versioning and migration compatibility.
        
        Business Value: Ensures backward compatibility and smooth system upgrades.
        """
        # Create user for versioning test
        auth_user = await auth_helper.create_authenticated_user(
            email=f"versioning_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        thread_id, run_id, _ = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id,
            operation="versioning_test"
        )
        
        # Create states with different versions
        version_1_state = {
            'user_id': auth_user.user_id,
            'thread_id': thread_id,
            'run_id': run_id,
            'message_history': [
                {'id': f'{run_id}_msg_0', 'role': 'user', 'content': 'Hello'},
                {'id': f'{run_id}_msg_1', 'role': 'assistant', 'content': 'Hi there!'}
            ],
            'ai_context': {'conversation_stage': 'greeting'},
            'version': 1,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        version_2_state = {
            'user_id': auth_user.user_id,
            'thread_id': thread_id,
            'run_id': run_id,
            'message_history': [
                {
                    'id': f'{run_id}_msg_0', 
                    'role': 'user', 
                    'content': 'Hello',
                    'metadata': {'timestamp': datetime.now(timezone.utc).isoformat()}  # New in v2
                },
                {
                    'id': f'{run_id}_msg_1', 
                    'role': 'assistant', 
                    'content': 'Hi there!',
                    'metadata': {'confidence': 0.95, 'timestamp': datetime.now(timezone.utc).isoformat()}  # New in v2
                }
            ],
            'ai_context': {
                'conversation_stage': 'greeting',
                'sentiment_analysis': {'overall_sentiment': 'positive', 'confidence': 0.9}  # New in v2
            },
            'user_preferences': {'response_style': 'friendly'},  # New in v2
            'performance_metrics': {'response_time_ms': 150},  # New in v2
            'version': 2,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'migration_log': []  # Track migrations
        }
        
        # Version 3 with additional fields and structural changes
        version_3_state = {
            'user_id': auth_user.user_id,
            'thread_id': thread_id,
            'run_id': run_id,
            'conversations': {  # Restructured from message_history
                'messages': [
                    {
                        'id': f'{run_id}_msg_0',
                        'role': 'user',
                        'content': 'Hello',
                        'metadata': {
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'client_info': {'platform': 'web', 'version': '1.0'}  # New in v3
                        }
                    },
                    {
                        'id': f'{run_id}_msg_1',
                        'role': 'assistant',
                        'content': 'Hi there!',
                        'metadata': {
                            'confidence': 0.95,
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'generation_info': {'model': 'gpt-4', 'temperature': 0.7}  # New in v3
                        }
                    }
                ],
                'summary': {'total_messages': 2, 'conversation_quality': 'high'}  # New in v3
            },
            'ai_context': {
                'conversation_stage': 'greeting',
                'sentiment_analysis': {'overall_sentiment': 'positive', 'confidence': 0.9},
                'personalization': {'user_type': 'new', 'engagement_level': 'high'}  # New in v3
            },
            'user_preferences': {
                'response_style': 'friendly',
                'notification_settings': {'real_time': True, 'email': False}  # New in v3
            },
            'performance_metrics': {
                'response_time_ms': 150,
                'cost_tracking': {'tokens_used': 25, 'estimated_cost': 0.001}  # New in v3
            },
            'version': 3,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),  # New in v3
            'migration_log': []
        }
        
        # Store different versions in Redis with different keys
        version_keys = [
            f"state_v1:{auth_user.user_id}:{thread_id}",
            f"state_v2:{auth_user.user_id}:{thread_id}",
            f"state_v3:{auth_user.user_id}:{thread_id}"
        ]
        
        states = [version_1_state, version_2_state, version_3_state]
        
        for key, state in zip(version_keys, states):
            serialized_state = json.dumps(state, default=str, ensure_ascii=False)
            await real_services_fixture.redis.set(key, serialized_state, ex=3600)
        
        # Test migration compatibility - create migration functions
        def migrate_v1_to_v2(v1_state: Dict[str, Any]) -> Dict[str, Any]:
            """Migrate version 1 state to version 2."""
            v2_state = v1_state.copy()
            v2_state['version'] = 2
            
            # Add metadata to messages
            for message in v2_state['message_history']:
                message['metadata'] = {'timestamp': datetime.now(timezone.utc).isoformat()}
            
            # Enhance AI context
            v2_state['ai_context']['sentiment_analysis'] = {
                'overall_sentiment': 'neutral', 
                'confidence': 0.5
            }
            
            # Add new fields
            v2_state['user_preferences'] = {'response_style': 'standard'}
            v2_state['performance_metrics'] = {'response_time_ms': 200}
            v2_state['migration_log'] = [{'from_version': 1, 'to_version': 2, 'migrated_at': datetime.now(timezone.utc).isoformat()}]
            
            return v2_state
        
        def migrate_v2_to_v3(v2_state: Dict[str, Any]) -> Dict[str, Any]:
            """Migrate version 2 state to version 3."""
            v3_state = {
                'user_id': v2_state['user_id'],
                'thread_id': v2_state['thread_id'],
                'run_id': v2_state['run_id'],
                'version': 3,
                'created_at': v2_state['created_at'],
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'migration_log': v2_state.get('migration_log', [])
            }
            
            # Restructure message_history to conversations
            v3_state['conversations'] = {
                'messages': [],
                'summary': {
                    'total_messages': len(v2_state['message_history']),
                    'conversation_quality': 'good'
                }
            }
            
            # Migrate messages with enhanced metadata
            for message in v2_state['message_history']:
                v3_message = message.copy()
                if 'metadata' not in v3_message:
                    v3_message['metadata'] = {}
                
                if message['role'] == 'user':
                    v3_message['metadata']['client_info'] = {'platform': 'web', 'version': '1.0'}
                else:
                    v3_message['metadata']['generation_info'] = {'model': 'gpt-4', 'temperature': 0.7}
                
                v3_state['conversations']['messages'].append(v3_message)
            
            # Migrate and enhance other sections
            v3_state['ai_context'] = v2_state['ai_context'].copy()
            v3_state['ai_context']['personalization'] = {'user_type': 'migrated', 'engagement_level': 'medium'}
            
            v3_state['user_preferences'] = v2_state['user_preferences'].copy()
            v3_state['user_preferences']['notification_settings'] = {'real_time': True, 'email': False}
            
            v3_state['performance_metrics'] = v2_state['performance_metrics'].copy()
            v3_state['performance_metrics']['cost_tracking'] = {'tokens_used': 30, 'estimated_cost': 0.002}
            
            # Add migration log entry
            v3_state['migration_log'].append({
                'from_version': 2, 
                'to_version': 3, 
                'migrated_at': datetime.now(timezone.utc).isoformat()
            })
            
            return v3_state
        
        # Test migrations
        # Load v1 state and migrate to v2
        v1_json = await real_services_fixture.redis.get(version_keys[0])
        v1_loaded = json.loads(v1_json)
        v2_migrated = migrate_v1_to_v2(v1_loaded)
        
        # Validate v1 to v2 migration
        assert v2_migrated['version'] == 2
        assert 'user_preferences' in v2_migrated
        assert 'performance_metrics' in v2_migrated
        assert all('metadata' in msg for msg in v2_migrated['message_history'])
        assert len(v2_migrated['migration_log']) == 1
        assert v2_migrated['migration_log'][0]['from_version'] == 1
        
        # Migrate v2 to v3
        v3_migrated = migrate_v2_to_v3(v2_migrated)
        
        # Validate v2 to v3 migration
        assert v3_migrated['version'] == 3
        assert 'conversations' in v3_migrated
        assert 'message_history' not in v3_migrated  # Restructured
        assert len(v3_migrated['conversations']['messages']) == 2
        assert 'personalization' in v3_migrated['ai_context']
        assert 'cost_tracking' in v3_migrated['performance_metrics']
        assert len(v3_migrated['migration_log']) == 2  # Two migration entries
        
        # Store migrated states
        migrated_v2_key = f"migrated_v2:{auth_user.user_id}:{thread_id}"
        migrated_v3_key = f"migrated_v3:{auth_user.user_id}:{thread_id}"
        
        await real_services_fixture.redis.set(migrated_v2_key, json.dumps(v2_migrated, default=str), ex=3600)
        await real_services_fixture.redis.set(migrated_v3_key, json.dumps(v3_migrated, default=str), ex=3600)
        
        # Test backward compatibility reading
        def read_state_any_version(state_dict: Dict[str, Any]) -> Dict[str, Any]:
            """Read state with backward compatibility."""
            version = state_dict.get('version', 1)
            
            # Normalize to current format (v3-like structure)
            normalized = {
                'user_id': state_dict['user_id'],
                'thread_id': state_dict['thread_id'],
                'run_id': state_dict['run_id'],
                'version': version,
                'ai_context': state_dict.get('ai_context', {}),
                'user_preferences': state_dict.get('user_preferences', {}),
                'performance_metrics': state_dict.get('performance_metrics', {})
            }
            
            # Handle message structure differences
            if 'conversations' in state_dict:
                # v3 format
                normalized['messages'] = state_dict['conversations']['messages']
            elif 'message_history' in state_dict:
                # v1/v2 format
                normalized['messages'] = state_dict['message_history']
            
            return normalized
        
        # Test reading all versions with compatibility
        for i, key in enumerate(version_keys + [migrated_v2_key, migrated_v3_key]):
            stored_json = await real_services_fixture.redis.get(key)
            stored_state = json.loads(stored_json)
            normalized_state = read_state_any_version(stored_state)
            
            assert 'user_id' in normalized_state
            assert 'messages' in normalized_state
            assert len(normalized_state['messages']) >= 2
            
            # Each version should be readable
            assert normalized_state['user_id'] == auth_user.user_id
            assert normalized_state['thread_id'] == thread_id
        
        # BUSINESS VALUE VALIDATION: Version compatibility enables smooth upgrades
        self.assert_business_value_delivered({
            'versions_tested': 3,
            'migrations_successful': 2,
            'backward_compatibility_maintained': True,
            'data_integrity_preserved': True,
            'migration_log_tracking': len(v3_migrated['migration_log']) == 2
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_large_state_performance_optimization(self, real_services_fixture, auth_helper, id_generator, serialization_helper):
        """
        Test performance optimization for large state objects.
        
        Business Value: Ensures system scalability with large conversation states.
        """
        # Create user for performance testing
        auth_user = await auth_helper.create_authenticated_user(
            email=f"performance_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        # Generate very large state object
        thread_id, run_id, _ = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id,
            operation="performance_test"
        )
        
        # Create state with 1000 messages and extensive AI context
        massive_message_history = []
        for i in range(1000):  # 1000 messages for performance testing
            content_base = f"Message {i}: Business analysis and recommendations. "
            content = content_base + "Detailed analysis content. " * 100  # ~5KB per message
            
            massive_message_history.append({
                'id': f'{run_id}_msg_{i}',
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': content,
                'timestamp': (datetime.now(timezone.utc) - timedelta(minutes=1000-i)).isoformat(),
                'metadata': {
                    'tokens': 500 + (i * 2),
                    'processing_time_ms': 100 + (i % 50),
                    'confidence': 0.8 + (i % 20) * 0.01,
                    'business_value': 7.0 + (i % 30) * 0.1,
                    'complexity_score': (i % 10) + 1,
                    'optimization_potential': (i % 100) / 100.0
                }
            })
        
        # Create extensive AI analysis data
        massive_ai_context = {
            'conversation_analysis': {
                'topics': {f'topic_{i}': {'frequency': i, 'importance': (i % 10) / 10} for i in range(500)},
                'entities': {f'entity_{i}': {'type': 'business', 'confidence': 0.9, 'mentions': i % 20} for i in range(300)},
                'sentiment_timeline': [{'message_index': i, 'sentiment': 'positive' if i % 3 == 0 else 'neutral', 'score': 0.6 + (i % 40) * 0.01} for i in range(1000)],
                'recommendations': [
                    {
                        'id': f'rec_{i}',
                        'category': f'category_{i % 10}',
                        'priority': i % 5,
                        'savings_potential': (i * 100) % 10000,
                        'implementation_effort': ['low', 'medium', 'high'][i % 3],
                        'detailed_analysis': f'Detailed analysis for recommendation {i}: ' + 'Analysis content. ' * 200
                    } for i in range(200)
                ]
            },
            'user_modeling': {
                'interaction_patterns': {f'pattern_{i}': {'frequency': i, 'strength': (i % 100) / 100} for i in range(100)},
                'expertise_mapping': {f'domain_{i}': {'level': ['novice', 'intermediate', 'expert'][i % 3], 'confidence': 0.8} for i in range(50)},
                'preference_evolution': [{'timestamp': (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat(), 'preferences': {f'pref_{j}': j for j in range(10)}} for i in range(100)]
            }
        }
        
        massive_state = ComplexConversationState(
            user_id=auth_user.user_id,
            thread_id=thread_id,
            run_id=run_id,
            conversation_metadata={'conversation_type': 'enterprise_optimization', 'scale': 'massive'},
            message_history=massive_message_history,
            ai_context=massive_ai_context,
            user_preferences={'data_retention': 'maximum'},
            performance_metrics={'total_tokens': 500000, 'total_processing_time': 1500.0},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Performance test: JSON serialization
        json_start_time = time.time()
        json_serialized = serialization_helper.serialize_to_json(massive_state)
        json_serialization_time = time.time() - json_start_time
        json_size = len(json_serialized.encode('utf-8'))
        
        # Performance test: Binary serialization
        binary_start_time = time.time()
        binary_serialized = serialization_helper.serialize_to_binary(massive_state)
        binary_serialization_time = time.time() - binary_start_time
        binary_size = len(binary_serialized)
        
        # Performance test: Compression
        compression_start_time = time.time()
        compressed_binary = serialization_helper.compress_state(binary_serialized)
        compression_time = time.time() - compression_start_time
        compressed_size = len(compressed_binary)
        
        # Test Redis storage performance
        redis_storage_start = time.time()
        await real_services_fixture.redis.set(f"massive_state:{thread_id}", compressed_binary, ex=7200)
        redis_storage_time = time.time() - redis_storage_start
        
        # Test Redis retrieval performance
        redis_retrieval_start = time.time()
        retrieved_data = await real_services_fixture.redis.get(f"massive_state:{thread_id}")
        redis_retrieval_time = time.time() - redis_retrieval_start
        
        # Test decompression and deserialization performance
        decompression_start = time.time()
        decompressed_data = serialization_helper.decompress_state(retrieved_data)
        decompression_time = time.time() - decompression_start
        
        deserialization_start = time.time()
        recovered_massive_state = serialization_helper.deserialize_from_binary(decompressed_data)
        deserialization_time = time.time() - deserialization_start
        
        # Validate data integrity after all transformations
        assert recovered_massive_state.user_id == massive_state.user_id
        assert len(recovered_massive_state.message_history) == 1000
        assert len(recovered_massive_state.ai_context['conversation_analysis']['recommendations']) == 200
        
        # Sample validation to ensure deep data integrity
        for i in range(0, 1000, 100):  # Check every 100th message
            original_msg = massive_state.message_history[i]
            recovered_msg = recovered_massive_state.message_history[i]
            assert recovered_msg['id'] == original_msg['id']
            assert recovered_msg['metadata']['tokens'] == original_msg['metadata']['tokens']
        
        # Calculate performance metrics
        compression_ratio = compressed_size / binary_size
        total_round_trip_time = (json_serialization_time + compression_time + 
                                redis_storage_time + redis_retrieval_time + 
                                decompression_time + deserialization_time)
        
        # Performance assertions (reasonable thresholds for large data)
        assert json_serialization_time < 2.0, f"JSON serialization too slow: {json_serialization_time}s"
        assert binary_serialization_time < 1.0, f"Binary serialization too slow: {binary_serialization_time}s"
        assert compression_time < 1.0, f"Compression too slow: {compression_time}s"
        assert redis_storage_time < 0.5, f"Redis storage too slow: {redis_storage_time}s"
        assert redis_retrieval_time < 0.1, f"Redis retrieval too slow: {redis_retrieval_time}s"
        assert total_round_trip_time < 5.0, f"Total round-trip too slow: {total_round_trip_time}s"
        
        # Compression should be effective for large repetitive data
        assert compression_ratio < 0.3, f"Compression not effective: {compression_ratio}"
        
        # BUSINESS VALUE VALIDATION: Performance enables large-scale conversations
        self.assert_business_value_delivered({
            'data_size_original_mb': json_size / (1024 * 1024),
            'data_size_compressed_mb': compressed_size / (1024 * 1024),
            'compression_ratio': compression_ratio,
            'serialization_performance_ms': json_serialization_time * 1000,
            'storage_performance_ms': redis_storage_time * 1000,
            'retrieval_performance_ms': redis_retrieval_time * 1000,
            'total_round_trip_ms': total_round_trip_time * 1000,
            'scalability_demonstrated': True
        }, 'automation')