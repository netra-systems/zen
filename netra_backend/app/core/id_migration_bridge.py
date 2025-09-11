"""ID Migration Bridge - Phase 1 SSOT Remediation

MISSION CRITICAL: This module provides translation services between legacy ID formats
and SSOT-compliant ID patterns to enable gradual migration without breaking changes.

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: System stability during SSOT migration
- Value Impact: Prevents WebSocket 1011 errors that break $500K+ ARR chat functionality
- Strategic Impact: Enables safe incremental migration to SSOT compliance

PHASE 1 IMPLEMENTATION SCOPE:
1. ID format detection and normalization
2. Pattern-agnostic resource matching for cleanup logic
3. Legacy-to-SSOT translation services
4. Backward compatibility preservation
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple, List, Set
from dataclasses import dataclass
from enum import Enum

from shared.id_generation.unified_id_generator import UnifiedIdGenerator

logger = logging.getLogger(__name__)


class IdFormat(Enum):
    """ID format types for classification."""
    SSOT = "ssot"
    LEGACY_THREAD = "legacy_thread"
    LEGACY_RUN = "legacy_run"  
    WEBSOCKET_FACTORY = "websocket_factory"
    DATABASE_SESSION = "database_session"
    UNKNOWN = "unknown"


@dataclass
class IdTranslationResult:
    """Result of ID translation operation."""
    original_id: str
    translated_id: str
    format_detected: IdFormat
    translation_needed: bool
    confidence_score: float  # 0.0-1.0


class IdMigrationBridge:
    """Bridge service for translating between ID formats during SSOT migration.
    
    PHASE 1 SSOT REMEDIATION: This class enables WebSocket resource cleanup
    to work correctly despite ID pattern mismatches by providing translation
    and matching services.
    """
    
    def __init__(self):
        self.translation_cache: Dict[str, IdTranslationResult] = {}
        self.pattern_registry: Dict[str, IdFormat] = {}
        self._setup_pattern_registry()
    
    def _setup_pattern_registry(self) -> None:
        """Initialize pattern registry for format detection."""
        # SSOT patterns
        self.pattern_registry.update({
            r"thread_\w+_\d{13}_\d+_[a-f0-9]{8}": IdFormat.SSOT,
            r"run_\w+_\d{13}_\d+_[a-f0-9]{8}": IdFormat.SSOT,
            r"req_\w+_\d{13}_\d+_[a-f0-9]{8}": IdFormat.SSOT,
        })
        
        # Legacy patterns
        self.pattern_registry.update({
            r"thread_\w+_\d+_[a-f0-9]{8}": IdFormat.LEGACY_THREAD,
            r"run_\w+_\d+_[a-f0-9]{8}": IdFormat.LEGACY_RUN,
            r"websocket_factory_\d+": IdFormat.WEBSOCKET_FACTORY,
            r"thread_session_\d{13}_\d+_[a-f0-9]{8}": IdFormat.DATABASE_SESSION,
        })
    
    def detect_id_format(self, id_string: str) -> Tuple[IdFormat, float]:
        """Detect the format of an ID string.
        
        Args:
            id_string: ID to analyze
            
        Returns:
            Tuple of (detected_format, confidence_score)
        """
        if not id_string or not isinstance(id_string, str):
            return IdFormat.UNKNOWN, 0.0
        
        # Try UnifiedIdGenerator parsing first (SSOT format)
        parsed = UnifiedIdGenerator.parse_id(id_string)
        if parsed:
            return IdFormat.SSOT, 1.0
        
        # Check legacy patterns
        parts = id_string.split('_')
        
        if len(parts) >= 3:
            prefix = parts[0]
            operation = parts[1]
            
            # Legacy thread pattern: thread_operation_counter_random (no timestamp)
            if prefix == 'thread' and len(parts) == 4:
                try:
                    counter = int(parts[2])
                    if counter < 1000000:  # Counter, not timestamp
                        return IdFormat.LEGACY_THREAD, 0.9
                except ValueError:
                    pass
            
            # Legacy run pattern: run_operation_counter_random (no timestamp)
            elif prefix == 'run' and len(parts) == 4:
                try:
                    counter = int(parts[2])
                    if counter < 1000000:  # Counter, not timestamp
                        return IdFormat.LEGACY_RUN, 0.9
                except ValueError:
                    pass
            
            # WebSocket factory pattern: websocket_factory_timestamp
            elif 'websocket_factory' in id_string and parts[-1].isdigit():
                return IdFormat.WEBSOCKET_FACTORY, 0.8
        
        return IdFormat.UNKNOWN, 0.0
    
    def translate_id(self, id_string: str, target_format: IdFormat = IdFormat.SSOT) -> IdTranslationResult:
        """Translate an ID to the target format.
        
        Args:
            id_string: ID to translate
            target_format: Target format (default: SSOT)
            
        Returns:
            Translation result with metadata
        """
        # Check cache first
        cache_key = f"{id_string}:{target_format.value}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]
        
        # Detect source format
        source_format, confidence = self.detect_id_format(id_string)
        
        # No translation needed if already in target format
        if source_format == target_format and source_format != IdFormat.UNKNOWN:
            result = IdTranslationResult(
                original_id=id_string,
                translated_id=id_string,
                format_detected=source_format,
                translation_needed=False,
                confidence_score=confidence
            )
            self.translation_cache[cache_key] = result
            return result
        
        # Perform translation
        translated_id = self._perform_translation(id_string, source_format, target_format)
        
        result = IdTranslationResult(
            original_id=id_string,
            translated_id=translated_id,
            format_detected=source_format,
            translation_needed=translated_id != id_string,
            confidence_score=confidence
        )
        
        self.translation_cache[cache_key] = result
        return result
    
    def _perform_translation(self, id_string: str, source_format: IdFormat, 
                           target_format: IdFormat) -> str:
        """Perform the actual ID translation.
        
        Args:
            id_string: Source ID
            source_format: Detected source format
            target_format: Target format
            
        Returns:
            Translated ID string
        """
        if target_format == IdFormat.SSOT:
            # Translate to SSOT format using UnifiedIdGenerator
            return UnifiedIdGenerator.normalize_id_format(id_string)
        
        # For now, only support translation to SSOT format
        # Future phases can add other translation targets
        return id_string
    
    def find_matching_ids(self, target_id: str, candidate_ids: List[str]) -> List[str]:
        """Find IDs that should be considered matches for resource cleanup.
        
        CRITICAL FIX: This method enables WebSocket cleanup logic to find
        resources even when ID patterns don't exactly match.
        
        Args:
            target_id: ID to find matches for
            candidate_ids: List of candidate IDs to check
            
        Returns:
            List of IDs that match the target for cleanup purposes
        """
        matches = []
        
        # Always include exact matches
        if target_id in candidate_ids:
            matches.append(target_id)
        
        # Use UnifiedIdGenerator's matching logic for semantic matches
        for candidate_id in candidate_ids:
            if candidate_id != target_id and UnifiedIdGenerator.ids_match_for_cleanup(target_id, candidate_id):
                matches.append(candidate_id)
        
        return matches
    
    def normalize_context_ids(self, user_id: str, thread_id: str, run_id: str) -> Tuple[str, str, str]:
        """Normalize context IDs to ensure consistent patterns.
        
        PHASE 1 SSOT REMEDIATION: This method ensures that context IDs are
        in SSOT-compliant format for proper resource management.
        
        Args:
            user_id: User identifier
            thread_id: Thread ID (any format)
            run_id: Run ID (any format)
            
        Returns:
            Tuple of (normalized_thread_id, normalized_run_id, new_request_id)
        """
        return UnifiedIdGenerator.translate_legacy_context_ids(
            user_id, thread_id, run_id, "normalization"
        )
    
    def get_cleanup_key(self, id_string: str) -> str:
        """Generate a cleanup key for resource matching.
        
        Args:
            id_string: ID to generate cleanup key for
            
        Returns:
            Cleanup key for resource matching
        """
        pattern_info = UnifiedIdGenerator.extract_pattern_info(id_string)
        
        # Use user_context as cleanup key - this allows different timestamps/counters
        # but same logical resource to be matched
        return pattern_info.get('user_context', id_string)
    
    def validate_migration_safety(self, legacy_ids: List[str], ssot_ids: List[str]) -> Dict[str, Any]:
        """Validate that migration will preserve resource relationships.
        
        Args:
            legacy_ids: List of legacy format IDs
            ssot_ids: List of SSOT format IDs
            
        Returns:
            Validation report with safety assessment
        """
        report = {
            'safe_to_migrate': True,
            'issues': [],
            'translations': {},
            'orphaned_resources': [],
            'duplicate_mappings': []
        }
        
        # Track cleanup key mappings
        cleanup_mappings: Dict[str, List[str]] = {}
        
        for legacy_id in legacy_ids:
            cleanup_key = self.get_cleanup_key(legacy_id)
            if cleanup_key not in cleanup_mappings:
                cleanup_mappings[cleanup_key] = []
            cleanup_mappings[cleanup_key].append(legacy_id)
            
            # Check if SSOT equivalent exists
            matches = self.find_matching_ids(legacy_id, ssot_ids)
            if matches:
                report['translations'][legacy_id] = matches
            else:
                report['orphaned_resources'].append(legacy_id)
        
        # Check for duplicate mappings
        for cleanup_key, ids in cleanup_mappings.items():
            if len(ids) > 1:
                report['duplicate_mappings'].append({
                    'cleanup_key': cleanup_key,
                    'conflicting_ids': ids
                })
        
        # Assess safety
        if report['orphaned_resources']:
            report['issues'].append('Some legacy resources have no SSOT equivalent')
        
        if report['duplicate_mappings']:
            report['issues'].append('Some cleanup keys map to multiple resources')
            
        report['safe_to_migrate'] = len(report['issues']) == 0
        
        return report
    
    def get_translation_stats(self) -> Dict[str, Any]:
        """Get statistics about translation operations.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            'cache_size': len(self.translation_cache),
            'format_distribution': {},
            'translation_success_rate': 0.0,
            'total_translations': len(self.translation_cache)
        }
        
        if self.translation_cache:
            format_counts = {}
            successful_translations = 0
            
            for result in self.translation_cache.values():
                format_name = result.format_detected.value
                format_counts[format_name] = format_counts.get(format_name, 0) + 1
                
                if result.confidence_score > 0.8:
                    successful_translations += 1
            
            stats['format_distribution'] = format_counts
            stats['translation_success_rate'] = successful_translations / len(self.translation_cache)
        
        return stats
    
    def clear_cache(self) -> None:
        """Clear translation cache (for testing/debugging)."""
        self.translation_cache.clear()


# Global instance for singleton pattern
_migration_bridge: Optional[IdMigrationBridge] = None


def get_migration_bridge() -> IdMigrationBridge:
    """Get the global ID migration bridge instance."""
    global _migration_bridge
    if _migration_bridge is None:
        _migration_bridge = IdMigrationBridge()
    return _migration_bridge


# Convenience functions for common operations
def normalize_for_cleanup(id_string: str) -> str:
    """Normalize an ID for cleanup operations."""
    bridge = get_migration_bridge()
    result = bridge.translate_id(id_string, IdFormat.SSOT)
    return result.translated_id


def find_cleanup_matches(target_id: str, candidate_ids: List[str]) -> List[str]:
    """Find IDs that match for cleanup purposes."""
    bridge = get_migration_bridge()
    return bridge.find_matching_ids(target_id, candidate_ids)


def validate_id_compatibility(id1: str, id2: str) -> bool:
    """Check if two IDs are compatible for resource operations."""
    return UnifiedIdGenerator.ids_match_for_cleanup(id1, id2)


# Export main classes and functions
__all__ = [
    'IdMigrationBridge',
    'IdFormat',
    'IdTranslationResult',
    'get_migration_bridge',
    'normalize_for_cleanup',
    'find_cleanup_matches',
    'validate_id_compatibility'
]