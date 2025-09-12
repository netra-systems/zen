"""Agent Startup Test Data Generation Utilities

Comprehensive test data generators for agent startup scenarios.
Generates realistic user profiles, conversation histories, message patterns,
corrupted states, and load testing data for all customer tiers.

Business Value Justification (BVJ):
1. Segment: ALL customer segments (Free, Early, Mid, Enterprise)  
2. Business Goal: Ensure agent startup reliability across all scenarios
3. Value Impact: Prevents agent failures that block user interactions
4. Revenue Impact: Protects $200K+ MRR by ensuring reliable startup

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Production-like data patterns
- Comprehensive edge case coverage
- Load testing support for 100+ users
"""

import json
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Tuple

from netra_backend.app.agents.state import AgentMetadata, DeepAgentState
from netra_backend.app.schemas.shared_types import CustomerTier
from tests.e2e.config import TestUser, get_test_user


class DataCorruptionType(Enum):
    """Types of data corruption for testing."""
    MISSING_FIELDS = "missing_fields"
    INVALID_TYPES = "invalid_types"
    CIRCULAR_REFS = "circular_references"
    OVERSIZED_DATA = "oversized_data"
    MALFORMED_JSON = "malformed_json"


class MessagePattern(Enum):
    """Common message patterns in conversations."""
    GREETING = "greeting"
    OPTIMIZATION_REQUEST = "optimization"
    ANALYSIS_REQUEST = "analysis"
    REPORT_REQUEST = "report"
    ERROR_SCENARIO = "error_scenario"


@dataclass
class UserProfile:
    """Enhanced user profile for testing."""
    user: TestUser
    history_length: int
    interaction_patterns: List[MessagePattern]
    complexity_score: float
    failure_history: bool = False
    ai_spend_monthly: Optional[float] = None


class TestDataFactory:
    """Factory for generating all types of test data."""
    
    def __init__(self):
        """Initialize test data factory."""
        self._seed = random.randint(1, 1000000)
        random.seed(self._seed)
        self.conversation_templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, List[str]]:
        """Load conversation templates for each pattern."""
        return self._create_message_templates()
    
    def _create_message_templates(self) -> Dict[str, List[str]]:
        """Create templates for different message types."""
        greeting = self._get_greeting_templates()
        optimization = self._get_optimization_templates()
        return {**greeting, **optimization}
    
    def _get_greeting_templates(self) -> Dict[str, List[str]]:
        """Get greeting message templates."""
        return {
            "greeting": [
                "Hello, I need help optimizing my AI costs",
                "Hi there, can you analyze my AI spending?",
                "Good morning, I'm looking for AI optimization advice"
            ]
        }
    
    def _get_optimization_templates(self) -> Dict[str, List[str]]:
        """Get optimization message templates."""
        return {
            "optimization": [
                "My AI costs are too high, help me optimize",
                "I need recommendations for reducing AI spending",
                "Can you analyze my model usage and suggest improvements?"
            ]
        }


class UserProfileGenerator:
    """Generates realistic user profiles with history."""
    
    def __init__(self, factory: TestDataFactory):
        """Initialize profile generator."""
        self.factory = factory
    
    def generate_profile(self, tier: CustomerTier) -> UserProfile:
        """Generate user profile for specific tier."""
        user = get_test_user(tier.value)
        history_length = self._get_history_length(tier)
        patterns = self._get_interaction_patterns(tier)
        complexity = self._get_complexity_score(tier)
        return UserProfile(user, history_length, patterns, complexity)
    
    def _get_history_length(self, tier: CustomerTier) -> int:
        """Get appropriate history length for tier."""
        lengths = {
            CustomerTier.FREE: random.randint(0, 5),
            CustomerTier.EARLY: random.randint(5, 20),
            CustomerTier.MID: random.randint(15, 50),
            CustomerTier.ENTERPRISE: random.randint(30, 100)
        }
        return lengths.get(tier, 10)
    
    def _get_interaction_patterns(self, tier: CustomerTier) -> List[MessagePattern]:
        """Get interaction patterns based on tier."""
        base_patterns = [MessagePattern.GREETING, MessagePattern.OPTIMIZATION_REQUEST]
        if tier in [CustomerTier.MID, CustomerTier.ENTERPRISE]:
            base_patterns.extend([MessagePattern.ANALYSIS_REQUEST, MessagePattern.REPORT_REQUEST])
        return base_patterns
    
    def _get_complexity_score(self, tier: CustomerTier) -> float:
        """Get complexity score for tier."""
        scores = {
            CustomerTier.FREE: 0.3, CustomerTier.EARLY: 0.6,
            CustomerTier.MID: 0.8, CustomerTier.ENTERPRISE: 1.0
        }
        return scores.get(tier, 0.5)
    
    def generate_batch_profiles(self, count: int) -> List[UserProfile]:
        """Generate batch of user profiles."""
        profiles = []
        tiers = list(CustomerTier)
        for i in range(count):
            tier = tiers[i % len(tiers)]
            profiles.append(self.generate_profile(tier))
        return profiles


class ConversationHistorySeeder:
    """Seeds realistic conversation histories."""
    
    def __init__(self, factory: TestDataFactory):
        """Initialize conversation seeder."""
        self.factory = factory
    
    def seed_history(self, profile: UserProfile) -> List[Dict[str, Any]]:
        """Seed conversation history for user profile."""
        messages = []
        for i in range(profile.history_length):
            message = self._create_historical_message(profile, i)
            messages.append(message)
        return messages
    
    def _create_historical_message(self, profile: UserProfile, index: int) -> Dict[str, Any]:
        """Create single historical message."""
        pattern = random.choice(profile.interaction_patterns)
        template = random.choice(self.factory.conversation_templates.get(pattern.value, ["Generic message"]))
        timestamp = self._get_historical_timestamp(index)
        return self._build_message_dict(template, timestamp, pattern)
    
    def _get_historical_timestamp(self, index: int) -> datetime:
        """Get timestamp for historical message."""
        days_ago = random.randint(1, 30)
        hours_ago = random.randint(0, 23)
        return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)
    
    def _build_message_dict(self, content: str, timestamp: datetime, pattern: MessagePattern) -> Dict[str, Any]:
        """Build message dictionary."""
        return {
            "content": content,
            "timestamp": timestamp.isoformat(),
            "pattern": pattern.value,
            "id": str(uuid.uuid4())
        }


class MessagePatternGenerator:
    """Generates various message patterns for testing."""
    
    def generate_edge_case_messages(self) -> List[Dict[str, Any]]:
        """Generate edge case message scenarios."""
        return [
            self._create_empty_message(),
            self._create_oversized_message(),
            self._create_special_char_message(),
            self._create_unicode_message()
        ]
    
    def _create_empty_message(self) -> Dict[str, Any]:
        """Create empty message edge case."""
        return {"content": "", "type": "empty", "id": str(uuid.uuid4())}
    
    def _create_oversized_message(self) -> Dict[str, Any]:
        """Create oversized message edge case."""
        content = "Large message " * 1000
        return {"content": content, "type": "oversized", "id": str(uuid.uuid4())}
    
    def _create_special_char_message(self) -> Dict[str, Any]:
        """Create special character message."""
        content = "Special chars: !@#$%^&*()[]{}|;:,.<>?"
        return {"content": content, "type": "special_chars", "id": str(uuid.uuid4())}
    
    def _create_unicode_message(self) -> Dict[str, Any]:
        """Create unicode message."""
        content = "Unicode: [U+4F60][U+597D] [U+1F680] [U+0394][U+03C6][U+03BC] [U+00F1][U+00ED][U+0192]"
        return {"content": content, "type": "unicode", "id": str(uuid.uuid4())}


class CorruptedStateGenerator:
    """Generates corrupted state data for testing."""
    
    def generate_corrupted_state(self, corruption_type: DataCorruptionType) -> Dict[str, Any]:
        """Generate corrupted state based on type."""
        generators = {
            DataCorruptionType.MISSING_FIELDS: self._create_missing_fields_state,
            DataCorruptionType.INVALID_TYPES: self._create_invalid_types_state,
            DataCorruptionType.CIRCULAR_REFS: self._create_circular_refs_state,
            DataCorruptionType.OVERSIZED_DATA: self._create_oversized_state
        }
        return generators.get(corruption_type, self._create_generic_corrupted_state)()
    
    def _create_missing_fields_state(self) -> Dict[str, Any]:
        """Create state with missing required fields."""
        return {"user_id": None, "corrupted": True, "type": "missing_fields"}
    
    def _create_invalid_types_state(self) -> Dict[str, Any]:
        """Create state with invalid field types."""
        return {
            "user_request": 12345,  # Should be string
            "step_count": "invalid",  # Should be int
            "corrupted": True,
            "type": "invalid_types"
        }
    
    def _create_circular_refs_state(self) -> Dict[str, Any]:
        """Create state with circular references."""
        state = {"corrupted": True, "type": "circular_refs"}
        state["self_ref"] = state  # Circular reference
        return state
    
    def _create_oversized_state(self) -> Dict[str, Any]:
        """Create oversized state data."""
        large_data = ["x" * 10000] * 100
        return {"large_data": large_data, "corrupted": True, "type": "oversized"}
    
    def _create_generic_corrupted_state(self) -> Dict[str, Any]:
        """Create generic corrupted state."""
        return {"corrupted": True, "type": "generic"}


class LoadTestDataGenerator:
    """Generates data for load testing scenarios."""
    
    def __init__(self, factory: TestDataFactory):
        """Initialize load test generator."""
        self.factory = factory
        self.profile_gen = UserProfileGenerator(factory)
    
    def generate_concurrent_users(self, count: int = 100) -> List[Tuple[UserProfile, DeepAgentState]]:
        """Generate concurrent user data for load testing."""
        users = []
        for i in range(count):
            profile = self._create_load_test_profile(i)
            state = self._create_load_test_state(profile, i)
            users.append((profile, state))
        return users
    
    def _create_load_test_profile(self, index: int) -> UserProfile:
        """Create profile for load testing."""
        tier = list(CustomerTier)[index % len(CustomerTier)]
        profile = self.profile_gen.generate_profile(tier)
        profile.ai_spend_monthly = self._get_spend_for_tier(tier)
        return profile
    
    def _get_spend_for_tier(self, tier: CustomerTier) -> float:
        """Get monthly AI spend for tier."""
        spend_ranges = {
            CustomerTier.FREE: 0.0, CustomerTier.EARLY: random.uniform(100, 1000),
            CustomerTier.MID: random.uniform(1000, 10000), CustomerTier.ENTERPRISE: random.uniform(10000, 100000)
        }
        return spend_ranges.get(tier, 0.0)
    
    def _create_load_test_state(self, profile: UserProfile, index: int) -> DeepAgentState:
        """Create state for load testing."""
        return DeepAgentState(
            user_request=f"Load test request {index}",
            chat_thread_id=str(uuid.uuid4()),
            user_id=profile.user.id,
            metadata=AgentMetadata()
        )


# Main interface functions for easy usage
def create_test_data_factory() -> TestDataFactory:
    """Create configured test data factory."""
    return TestDataFactory()


def generate_startup_test_suite() -> Dict[str, Any]:
    """Generate complete startup test data suite."""
    factory = create_test_data_factory()
    return _build_test_suite(factory)


def _build_test_suite(factory: TestDataFactory) -> Dict[str, Any]:
    """Build complete test suite data."""
    load_gen = LoadTestDataGenerator(factory)
    corrupt_gen = CorruptedStateGenerator()
    pattern_gen = MessagePatternGenerator()
    
    return {
        "user_profiles": UserProfileGenerator(factory).generate_batch_profiles(50),
        "load_test_users": load_gen.generate_concurrent_users(100),
        "corrupted_states": _generate_corruption_samples(corrupt_gen),
        "edge_case_messages": pattern_gen.generate_edge_case_messages()
    }


def _generate_corruption_samples(corrupt_gen: CorruptedStateGenerator) -> List[Dict[str, Any]]:
    """Generate samples of each corruption type."""
    samples = []
    for corruption_type in DataCorruptionType:
        sample = corrupt_gen.generate_corrupted_state(corruption_type)
        samples.append(sample)
    return samples


def seed_conversation_for_profile(profile: UserProfile) -> List[Dict[str, Any]]:
    """Seed conversation history for user profile."""
    factory = create_test_data_factory()
    seeder = ConversationHistorySeeder(factory)
    return seeder.seed_history(profile)
