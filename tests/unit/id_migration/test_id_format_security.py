"""
ID Format & Security Tests - Issue #89

This test suite validates ID format consistency and security properties
as specified in the comprehensive test plan. These tests are designed to FAIL
until proper UnifiedIDManager patterns are implemented.

Business Value Justification:
- Segment: Enterprise/All Tiers (Security affects all users)
- Business Goal: Security Compliance (SOC2/GDPR audit readiness)
- Value Impact: Prevents ID collision and predictability vulnerabilities
- Strategic Impact: Ensures enterprise-grade ID security and traceability

Test Strategy: Create FAILING tests that demonstrate security gaps
"""

import uuid
import time
import asyncio
import threading
from typing import List, Dict, Set, Any
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestIDFormatSecurity(SSotBaseTestCase):
    """
    Test suite to validate ID format consistency and security properties.

    These tests are designed to FAIL initially, demonstrating current
    security and format issues that need to be addressed.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.unified_id_manager = UnifiedIDManager()

    def test_structured_id_format_consistency(self):
        """
        FAILING TEST: Verify structured ID format across all services.

        Tests that IDs follow pattern: {type}_{counter}_{uuid8}
        Current state: Mixed formats causing inconsistency
        """
        services = ['backend', 'auth', 'websocket', 'agent', 'database']
        id_types = [IDType.USER, IDType.SESSION, IDType.REQUEST, IDType.EXECUTION, IDType.WEBSOCKET]

        format_violations = []
        inconsistent_patterns = []

        for service in services:
            for id_type in id_types:
                # Generate test IDs for each service/type combination
                test_ids = self._generate_test_ids_for_service(service, id_type, count=10)

                for i, id_val in enumerate(test_ids):
                    # Validate structured ID format
                    if not self._validate_structured_id_format(id_val):
                        format_violations.append({
                            "service": service,
                            "id_type": id_type.value,
                            "id_value": id_val,
                            "error": f"ID does not follow structured format: {id_val}"
                        })

                    # Check for format consistency within the same type
                    if i > 0:
                        prev_id = test_ids[i-1]
                        if not self._ids_have_consistent_format(prev_id, id_val):
                            inconsistent_patterns.append({
                                "service": service,
                                "id_type": id_type.value,
                                "id1": prev_id,
                                "id2": id_val,
                                "error": "Inconsistent format between IDs of same type"
                            })

        # Record metrics
        self.record_metric("format_violations", len(format_violations))
        self.record_metric("inconsistent_patterns", len(inconsistent_patterns))
        self.record_metric("format_violation_details", format_violations)
        self.record_metric("inconsistent_pattern_details", inconsistent_patterns)

        total_violations = len(format_violations) + len(inconsistent_patterns)

        # The test should FAIL if format violations exist
        assert total_violations == 0, (
            f"Found {total_violations} ID format violations. "
            f"Format violations: {len(format_violations)}, "
            f"Inconsistent patterns: {len(inconsistent_patterns)}. "
            f"All IDs must follow structured format: {{type}}_{{counter}}_{{uuid8}}"
        )

    def test_id_collision_resistance(self):
        """
        FAILING TEST: Verify ID uniqueness across concurrent generation.

        Generate 10K IDs concurrently and check for collisions.
        Current state: Potential collisions due to uuid.uuid4() timing issues
        """
        collision_test_size = 10000
        thread_count = 50
        collisions_found = []

        # Concurrent ID generation to stress-test collision resistance
        ids = self._concurrent_id_generation(count=collision_test_size, threads=thread_count)

        # Check for exact duplicates
        id_set = set(ids)
        exact_duplicates = collision_test_size - len(id_set)

        # Check for near-collisions (similar patterns that could cause confusion)
        near_collisions = self._detect_near_collisions(ids)

        # Check for predictable patterns that could be exploited
        predictable_patterns = self._detect_predictable_patterns(ids)

        # Record security metrics
        self.record_metric("total_ids_generated", collision_test_size)
        self.record_metric("unique_ids", len(id_set))
        self.record_metric("exact_duplicates", exact_duplicates)
        self.record_metric("near_collisions", len(near_collisions))
        self.record_metric("predictable_patterns", len(predictable_patterns))

        # Calculate collision rate
        collision_rate = (exact_duplicates / collision_test_size) * 100
        self.record_metric("collision_rate_percentage", collision_rate)

        # The test should FAIL if any collisions are found
        assert exact_duplicates == 0, (
            f"Found {exact_duplicates} exact ID collisions out of {collision_test_size} generated IDs. "
            f"Collision rate: {collision_rate:.4f}%. "
            f"ID generation must guarantee uniqueness even under concurrent load."
        )

        assert len(near_collisions) == 0, (
            f"Found {len(near_collisions)} near-collision patterns that could cause confusion. "
            f"Near-collisions: {near_collisions[:5]}. "  # Show first 5 examples
            f"ID patterns must be sufficiently distinct to prevent user confusion."
        )

    def test_id_predictability_resistance(self):
        """
        FAILING TEST: Verify IDs are not predictable or guessable.

        This test checks for patterns that could allow attackers to predict
        or enumerate IDs, which is a security vulnerability.
        """
        # Generate a sequence of IDs and analyze for predictable patterns
        test_ids = []
        for id_type in [IDType.USER, IDType.SESSION, IDType.WEBSOCKET]:
            ids = [self.unified_id_manager.generate_id(id_type) for _ in range(100)]
            test_ids.extend(ids)

        # Analyze predictability patterns
        predictability_violations = []

        # Check for sequential patterns
        sequential_patterns = self._detect_sequential_patterns(test_ids)
        if sequential_patterns:
            predictability_violations.extend(sequential_patterns)

        # Check for timestamp-based predictability
        timestamp_patterns = self._detect_timestamp_patterns(test_ids)
        if timestamp_patterns:
            predictability_violations.extend(timestamp_patterns)

        # Check for entropy analysis
        entropy_analysis = self._analyze_id_entropy(test_ids)
        if entropy_analysis["insufficient_entropy"]:
            predictability_violations.append(entropy_analysis)

        # Record predictability metrics
        self.record_metric("predictability_violations", len(predictability_violations))
        self.record_metric("sequential_patterns", len(sequential_patterns))
        self.record_metric("timestamp_patterns", len(timestamp_patterns))
        self.record_metric("entropy_score", entropy_analysis["entropy_score"])

        # The test should FAIL if predictability issues exist
        assert len(predictability_violations) == 0, (
            f"Found {len(predictability_violations)} predictability violations. "
            f"Sequential patterns: {len(sequential_patterns)}, "
            f"Timestamp patterns: {len(timestamp_patterns)}, "
            f"Entropy score: {entropy_analysis['entropy_score']:.2f}. "
            f"IDs must be cryptographically unpredictable for security."
        )

    def test_cross_user_id_isolation(self):
        """
        FAILING TEST: Verify IDs maintain strict user isolation.

        This test ensures that user-specific IDs don't leak information
        about other users or allow cross-user access.
        """
        user_count = 50
        isolation_violations = []

        # Generate user contexts and their associated IDs
        user_contexts = {}
        for i in range(user_count):
            user_id = f"test_user_{i}"
            user_contexts[user_id] = self._generate_user_context_ids(user_id)

        # Check for isolation violations
        for user_id, user_ids in user_contexts.items():
            for other_user_id, other_user_ids in user_contexts.items():
                if user_id == other_user_id:
                    continue

                # Check for ID overlap or similarity that could cause confusion
                isolation_issues = self._check_user_id_isolation(user_ids, other_user_ids, user_id, other_user_id)
                if isolation_issues:
                    isolation_violations.extend(isolation_issues)

        # Record isolation metrics
        self.record_metric("users_tested", user_count)
        self.record_metric("isolation_violations", len(isolation_violations))
        self.record_metric("isolation_violation_details", isolation_violations)

        # The test should FAIL if isolation violations exist
        assert len(isolation_violations) == 0, (
            f"Found {len(isolation_violations)} user isolation violations across {user_count} test users. "
            f"User ID isolation must be strictly maintained to prevent cross-user access. "
            f"Violations: {isolation_violations[:3]}"  # Show first 3 examples
        )

    def test_id_format_backward_compatibility(self):
        """
        FAILING TEST: Verify ID format changes don't break existing systems.

        This test checks that new UnifiedIDManager formats are compatible
        with existing UUID-based systems during migration period.
        """
        compatibility_violations = []

        # Test with existing UUID formats
        existing_uuids = [str(uuid.uuid4()) for _ in range(20)]
        new_structured_ids = [self.unified_id_manager.generate_id(IDType.USER) for _ in range(20)]

        # Check UUID format acceptance
        for uuid_id in existing_uuids:
            if not self._is_backward_compatible_format(uuid_id):
                compatibility_violations.append({
                    "type": "uuid_rejection",
                    "id": uuid_id,
                    "error": "Legacy UUID format not accepted"
                })

        # Check structured ID format validation
        for structured_id in new_structured_ids:
            if not self._is_valid_new_format(structured_id):
                compatibility_violations.append({
                    "type": "structured_format_invalid",
                    "id": structured_id,
                    "error": "New structured format validation failed"
                })

        # Check cross-format validation
        for uuid_id in existing_uuids[:5]:
            for structured_id in new_structured_ids[:5]:
                cross_validation_issues = self._check_cross_format_validation(uuid_id, structured_id)
                compatibility_violations.extend(cross_validation_issues)

        # Record compatibility metrics
        self.record_metric("compatibility_violations", len(compatibility_violations))
        self.record_metric("uuid_compatibility_issues",
                          len([v for v in compatibility_violations if v["type"] == "uuid_rejection"]))
        self.record_metric("structured_format_issues",
                          len([v for v in compatibility_violations if v["type"] == "structured_format_invalid"]))

        # The test should FAIL if compatibility violations exist
        assert len(compatibility_violations) == 0, (
            f"Found {len(compatibility_violations)} backward compatibility violations. "
            f"ID format migration must maintain compatibility with existing UUID-based systems. "
            f"Violations: {compatibility_violations[:3]}"
        )

    def _generate_test_ids_for_service(self, service: str, id_type: IDType, count: int) -> List[str]:
        """Generate test IDs for a specific service and type."""
        ids = []
        for i in range(count):
            # Simulate different ID generation patterns that might exist
            if service == "backend":
                id_val = self.unified_id_manager.generate_id(id_type, prefix=service)
            elif service == "auth":
                id_val = self.unified_id_manager.generate_id(id_type)
            else:
                # Some services might still use uuid.uuid4() - simulate this
                id_val = str(uuid.uuid4())
            ids.append(id_val)
        return ids

    def _validate_structured_id_format(self, id_val: str) -> bool:
        """Validate that an ID follows the structured format."""
        return self.unified_id_manager.is_valid_id_format_compatible(id_val)

    def _ids_have_consistent_format(self, id1: str, id2: str) -> bool:
        """Check if two IDs have consistent formatting patterns."""
        # Both should be either UUID format or structured format
        id1_is_uuid = self._is_uuid_format(id1)
        id2_is_uuid = self._is_uuid_format(id2)

        # Inconsistent if one is UUID and other is structured
        return id1_is_uuid == id2_is_uuid

    def _is_uuid_format(self, id_val: str) -> bool:
        """Check if ID is in UUID format."""
        try:
            uuid.UUID(id_val)
            return True
        except ValueError:
            return False

    def _concurrent_id_generation(self, count: int, threads: int) -> List[str]:
        """Generate IDs concurrently to test for race conditions."""
        ids = []

        def generate_batch(batch_size):
            batch_ids = []
            for _ in range(batch_size):
                # Mix different ID types to test cross-type uniqueness
                id_type = [IDType.USER, IDType.SESSION, IDType.REQUEST, IDType.EXECUTION][_ % 4]
                id_val = self.unified_id_manager.generate_id(id_type)
                batch_ids.append(id_val)
            return batch_ids

        batch_size = count // threads
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(generate_batch, batch_size) for _ in range(threads)]

            for future in futures:
                ids.extend(future.result())

        return ids

    def _detect_near_collisions(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Detect near-collisions that could cause confusion."""
        near_collisions = []

        for i, id1 in enumerate(ids):
            for j, id2 in enumerate(ids[i+1:], i+1):
                # Check for similar patterns
                similarity_score = self._calculate_id_similarity(id1, id2)
                if similarity_score > 0.8:  # 80% similarity threshold
                    near_collisions.append({
                        "id1": id1,
                        "id2": id2,
                        "similarity_score": similarity_score,
                        "indices": [i, j]
                    })

        return near_collisions

    def _calculate_id_similarity(self, id1: str, id2: str) -> float:
        """Calculate similarity score between two IDs."""
        if id1 == id2:
            return 1.0

        # Use string similarity metrics
        common_chars = set(id1) & set(id2)
        total_chars = set(id1) | set(id2)

        if not total_chars:
            return 0.0

        return len(common_chars) / len(total_chars)

    def _detect_predictable_patterns(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Detect predictable patterns in ID generation."""
        patterns = []

        # Check for incrementing sequences
        for i in range(len(ids) - 1):
            if self._ids_are_sequential(ids[i], ids[i+1]):
                patterns.append({
                    "type": "sequential",
                    "id1": ids[i],
                    "id2": ids[i+1],
                    "index": i
                })

        return patterns

    def _ids_are_sequential(self, id1: str, id2: str) -> bool:
        """Check if two IDs are sequential (indicating predictable generation)."""
        # Extract numeric parts and check if they're sequential
        import re

        nums1 = re.findall(r'\d+', id1)
        nums2 = re.findall(r'\d+', id2)

        if len(nums1) != len(nums2):
            return False

        for n1, n2 in zip(nums1, nums2):
            if int(n2) == int(n1) + 1:
                return True

        return False

    def _detect_sequential_patterns(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Detect sequential patterns that indicate predictability."""
        sequential_patterns = []

        for i in range(len(ids) - 2):
            if (self._ids_are_sequential(ids[i], ids[i+1]) and
                self._ids_are_sequential(ids[i+1], ids[i+2])):
                sequential_patterns.append({
                    "type": "three_sequential",
                    "ids": [ids[i], ids[i+1], ids[i+2]],
                    "start_index": i
                })

        return sequential_patterns

    def _detect_timestamp_patterns(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Detect timestamp-based patterns that could be predictable."""
        timestamp_patterns = []
        current_time = int(time.time())

        for id_val in ids:
            # Look for timestamp-like numbers in the ID
            import re
            numbers = re.findall(r'\d{8,}', id_val)  # 8+ digit numbers

            for num_str in numbers:
                num = int(num_str)
                # Check if it's close to current timestamp (within last hour to next hour)
                if abs(num - current_time) < 3600 or abs(num - current_time * 1000) < 3600000:
                    timestamp_patterns.append({
                        "type": "timestamp_based",
                        "id": id_val,
                        "suspicious_number": num_str,
                        "time_diff": abs(num - current_time)
                    })

        return timestamp_patterns

    def _analyze_id_entropy(self, ids: List[str]) -> Dict[str, Any]:
        """Analyze the entropy of ID generation."""
        import math
        from collections import Counter

        # Combine all characters from all IDs
        all_chars = ''.join(ids)
        char_counts = Counter(all_chars)
        total_chars = len(all_chars)

        # Calculate Shannon entropy
        entropy = 0.0
        for count in char_counts.values():
            probability = count / total_chars
            if probability > 0:
                entropy -= probability * math.log2(probability)

        # Good entropy should be close to log2(character_set_size)
        # For alphanumeric + special chars, this should be around 5-6 bits
        insufficient_entropy = entropy < 4.0

        return {
            "entropy_score": entropy,
            "insufficient_entropy": insufficient_entropy,
            "char_distribution": dict(char_counts.most_common(10)),
            "total_chars_analyzed": total_chars
        }

    def _generate_user_context_ids(self, user_id: str) -> Dict[str, List[str]]:
        """Generate various IDs associated with a user context."""
        context_ids = {
            "user_sessions": [],
            "websocket_connections": [],
            "agent_executions": [],
            "requests": []
        }

        # Generate multiple IDs for each category
        for _ in range(5):
            context_ids["user_sessions"].append(
                self.unified_id_manager.generate_id(IDType.SESSION, context={"user_id": user_id})
            )
            context_ids["websocket_connections"].append(
                self.unified_id_manager.generate_id(IDType.WEBSOCKET, context={"user_id": user_id})
            )
            context_ids["agent_executions"].append(
                self.unified_id_manager.generate_id(IDType.EXECUTION, context={"user_id": user_id})
            )
            context_ids["requests"].append(
                self.unified_id_manager.generate_id(IDType.REQUEST, context={"user_id": user_id})
            )

        return context_ids

    def _check_user_id_isolation(self, user1_ids: Dict[str, List[str]],
                                user2_ids: Dict[str, List[str]],
                                user1_id: str, user2_id: str) -> List[Dict[str, Any]]:
        """Check for isolation violations between two users' IDs."""
        violations = []

        # Flatten all IDs for each user
        all_user1_ids = []
        all_user2_ids = []

        for id_list in user1_ids.values():
            all_user1_ids.extend(id_list)
        for id_list in user2_ids.values():
            all_user2_ids.extend(id_list)

        # Check for exact duplicates (should never happen)
        user1_set = set(all_user1_ids)
        user2_set = set(all_user2_ids)
        duplicates = user1_set & user2_set

        if duplicates:
            violations.append({
                "type": "exact_duplicate",
                "user1": user1_id,
                "user2": user2_id,
                "duplicate_ids": list(duplicates)
            })

        # Check for patterns that could lead to confusion
        for id1 in all_user1_ids:
            for id2 in all_user2_ids:
                if self._calculate_id_similarity(id1, id2) > 0.9:
                    violations.append({
                        "type": "high_similarity",
                        "user1": user1_id,
                        "user2": user2_id,
                        "id1": id1,
                        "id2": id2,
                        "similarity": self._calculate_id_similarity(id1, id2)
                    })

        return violations

    def _is_backward_compatible_format(self, id_val: str) -> bool:
        """Check if ID format is backward compatible."""
        return self.unified_id_manager.is_valid_id_format_compatible(id_val)

    def _is_valid_new_format(self, id_val: str) -> bool:
        """Check if ID follows the new structured format correctly."""
        return self.unified_id_manager._is_structured_id_format(id_val)

    def _check_cross_format_validation(self, uuid_id: str, structured_id: str) -> List[Dict[str, Any]]:
        """Check for issues when validating different format types together."""
        issues = []

        # Both should be considered valid formats
        if not self.unified_id_manager.is_valid_id_format_compatible(uuid_id):
            issues.append({
                "type": "uuid_format_rejected",
                "id": uuid_id,
                "error": "UUID format should be accepted during migration"
            })

        if not self.unified_id_manager.is_valid_id_format_compatible(structured_id):
            issues.append({
                "type": "structured_format_rejected",
                "id": structured_id,
                "error": "Structured format should be accepted"
            })

        return issues


if __name__ == "__main__":
    # Run tests to demonstrate current security gaps
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])