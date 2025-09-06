from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
Test Environment Setup for Real LLM Testing

Provides utilities for setting up and managing isolated test environments
with seed data loading and transaction-based isolation.

Business Value Justification (BVJ):
1. Segment: Platform/Internal  
2. Business Goal: Testing Infrastructure Excellence
3. Value Impact: Enables reliable validation of AI optimization features
4. Revenue Impact: Prevents production issues through comprehensive testing

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines (modular design)
- Function size: <25 lines each
- Single responsibility: Test environment setup and management
- Type safety with proper error handling
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from test_framework.real_llm_config import RealLLMTestManager, get_real_llm_manager
from test_framework.seed_data_manager import (
    SeedDataManager,
    TestEnvironmentConfig,
    get_seed_data_manager,
)

logger = logging.getLogger(__name__)


@dataclass
class TestSession:
    """Configuration for a test session."""
    session_id: str
    test_level: str
    datasets_required: List[str] = field(default_factory=list)
    use_real_llm: bool = False
    llm_model: str = "gemini-2.5-pro" 
    llm_timeout: int = 30
    isolation_enabled: bool = True
    setup_time: Optional[str] = None
    cleanup_time: Optional[str] = None


class TestEnvironmentValidator:
    """Validates test environment configuration and prerequisites."""
    
    def __init__(self):
        self.validation_results: Dict[str, Any] = {}
    
    async def validate_database_connection(self, database_url: str) -> bool:
        """Validate database connection and schema."""
        try:
            import asyncpg
            from shared.database_url_builder import DatabaseURLBuilder
            
            # Normalize URL for asyncpg compatibility
            normalized_url = DatabaseURLBuilder.format_for_asyncpg_driver(database_url)
            conn = await asyncpg.connect(normalized_url)
            
            # Check if test schema exists
            schema_exists = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'netra_test')
            """)
            
            if not schema_exists:
                logger.warning("Test schema 'netra_test' does not exist - will be created")
                self.validation_results['database_schema'] = 'missing'
            else:
                self.validation_results['database_schema'] = 'exists'
            
            await conn.close()
            self.validation_results['database_connection'] = 'success'
            return True
            
        except Exception as e:
            logger.error(f"Database validation failed: {e}")
            self.validation_results['database_connection'] = f'failed: {e}'
            return False
    
    async def validate_api_keys(self, use_real_llm: bool) -> bool:
        """Validate required API keys for LLM testing with enhanced TEST_* preference."""
        if not use_real_llm:
            self.validation_results['api_keys'] = 'not_required'
            return True
        
        # Check for test-specific API keys first, then fallback to production keys
        provider_keys = {
            'openai': ['TEST_OPENAI_API_KEY', 'GOOGLE_API_KEY'],
            'anthropic': ['TEST_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'],
            'google': ['TEST_GOOGLE_API_KEY', 'GOOGLE_API_KEY']
        }
        
        available_providers = []
        production_key_warnings = []
        missing_providers = []
        
        for provider, key_options in provider_keys.items():
            found_key = None
            for key in key_options:
                if get_env().get(key):
                    found_key = key
                    break
            
            if found_key:
                available_providers.append(provider)
                if not found_key.startswith('TEST_'):
                    production_key_warnings.append(f"Using production {provider.upper()} key - recommend TEST_{found_key}")
            else:
                missing_providers.append(provider)
        
        # At least one provider must be available
        if not available_providers:
            logger.error("No LLM API keys found for real LLM testing")
            self.validation_results['api_keys'] = 'none_available'
            return False
        
        # Log warnings about production keys
        for warning in production_key_warnings:
            logger.warning(warning)
        
        self.validation_results['api_keys'] = {
            'available_providers': available_providers,
            'missing_providers': missing_providers,
            'production_key_warnings': production_key_warnings,
            'status': 'complete' if not missing_providers else 'partial',
            'isolation_level': 'test_keys' if not production_key_warnings else 'mixed'
        }
        
        logger.info(f"API key validation: {len(available_providers)} providers available ({available_providers})")
        return True
    
    def validate_seed_data_files(self, datasets_required: List[str]) -> bool:
        """Validate that required seed data files exist and are valid."""
        test_data_dir = Path(__file__).parent.parent / "test_data" / "seed"
        
        if not test_data_dir.exists():
            logger.error(f"Seed data directory does not exist: {test_data_dir}")
            self.validation_results['seed_data'] = {
                'status': 'directory_missing',
                'directory': str(test_data_dir)
            }
            return False
        
        missing_files = []
        existing_files = []
        invalid_files = []
        file_details = {}
        
        for dataset in datasets_required:
            data_file = test_data_dir / f"{dataset}.json"
            if data_file.exists():
                try:
                    # Validate JSON structure
                    import json
                    with open(data_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Check for required structure
                    if 'metadata' not in data:
                        invalid_files.append(f"{dataset}: missing metadata")
                    else:
                        metadata = data['metadata']
                        file_details[dataset] = {
                            'size_bytes': data_file.stat().st_size,
                            'description': metadata.get('description', 'No description'),
                            'record_count': metadata.get('record_count', {})
                        }
                    
                    existing_files.append(str(data_file))
                    
                except Exception as e:
                    invalid_files.append(f"{dataset}: {str(e)}")
                    logger.error(f"Invalid seed data file {data_file}: {e}")
            else:
                missing_files.append(str(data_file))
        
        if missing_files or invalid_files:
            logger.error(f"Seed data validation failed - Missing: {missing_files}, Invalid: {invalid_files}")
            self.validation_results['seed_data'] = {
                'status': 'incomplete',
                'missing': missing_files,
                'invalid': invalid_files,
                'existing': existing_files,
                'file_details': file_details
            }
            return False
        
        self.validation_results['seed_data'] = {
            'status': 'complete',
            'files': existing_files,
            'file_details': file_details,
            'total_size_bytes': sum(details['size_bytes'] for details in file_details.values())
        }
        
        logger.info(f"Seed data validation: {len(existing_files)} files validated successfully")
        return True
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation results summary."""
        return {
            'validation_results': self.validation_results,
            'overall_status': self._calculate_overall_status()
        }
    
    def _calculate_overall_status(self) -> str:
        """Calculate overall validation status."""
        if not self.validation_results:
            return 'not_validated'
        
        critical_failures = [
            self.validation_results.get('database_connection', '').startswith('failed'),
            self.validation_results.get('api_keys') == 'none_available',
            self.validation_results.get('seed_data', {}).get('status') == 'incomplete'
        ]
        
        if any(critical_failures):
            return 'failed'
        
        warnings = [
            self.validation_results.get('database_schema') == 'missing',
            isinstance(self.validation_results.get('api_keys'), dict) and 
            self.validation_results['api_keys'].get('status') == 'partial'
        ]
        
        if any(warnings):
            return 'passed_with_warnings'
        
        return 'passed'


class TestEnvironmentOrchestrator:
    """Orchestrates setup and management of test environments."""
    
    def __init__(self):
        self.active_sessions: Dict[str, TestSession] = {}
        self.seed_manager: Optional[SeedDataManager] = None
        self.llm_manager: Optional[RealLLMTestManager] = None
        self.validator = TestEnvironmentValidator()
    
    async def initialize(self, config: Optional[TestEnvironmentConfig] = None):
        """Initialize the test environment orchestrator."""
        # Initialize seed data manager
        self.seed_manager = await get_seed_data_manager(config)
        
        # Initialize LLM manager
        self.llm_manager = get_real_llm_manager()
        
        logger.info("Test environment orchestrator initialized")
    
    async def setup_test_session(self, test_level: str, use_real_llm: bool = False, 
                                llm_model: str = "gemini-2.5-pro", 
                                datasets: Optional[List[str]] = None) -> str:
        """Setup a complete test session with environment and data."""
        session_id = str(uuid.uuid4())[:8]
        
        # Determine required datasets based on test level
        if datasets is None:
            datasets = self._get_datasets_for_level(test_level)
        
        session = TestSession(
            session_id=session_id,
            test_level=test_level,
            datasets_required=datasets,
            use_real_llm=use_real_llm,
            llm_model=llm_model,
            isolation_enabled=True
        )
        
        try:
            # Validate environment
            validation_passed = await self._validate_session_requirements(session)
            if not validation_passed:
                raise RuntimeError(f"Environment validation failed for session {session_id}")
            
            # Setup seed data environment
            if self.seed_manager and datasets:
                await self.seed_manager.setup_test_environment(session_id, datasets)
                logger.info(f"Seed data loaded for session {session_id}: {datasets}")
            
            # Configure LLM testing if requested
            if use_real_llm and self.llm_manager:
                logger.info(f"Real LLM testing enabled for session {session_id} with model {llm_model}")
            
            self.active_sessions[session_id] = session
            session.setup_time = str(asyncio.get_running_loop().time())
            
            logger.info(f"Test session {session_id} setup complete")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to setup test session {session_id}: {e}")
            await self.cleanup_test_session(session_id)
            raise
    
    async def cleanup_test_session(self, session_id: str):
        """Cleanup test session and associated resources."""
        if session_id not in self.active_sessions:
            logger.warning(f"Test session {session_id} not found for cleanup")
            return
        
        try:
            session = self.active_sessions[session_id]
            
            # Cleanup seed data environment
            if self.seed_manager:
                await self.seed_manager.cleanup_test_environment(session_id)
            
            session.cleanup_time = str(asyncio.get_running_loop().time())
            del self.active_sessions[session_id]
            
            logger.info(f"Test session {session_id} cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup of session {session_id}: {e}")
    
    async def cleanup_all_sessions(self):
        """Cleanup all active test sessions."""
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            await self.cleanup_test_session(session_id)
        
        if self.seed_manager:
            await self.seed_manager.close()
            
        logger.info(f"Cleaned up {len(session_ids)} test sessions")
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a test session."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        return {
            'session_id': session.session_id,
            'test_level': session.test_level,
            'datasets_loaded': session.datasets_required,
            'use_real_llm': session.use_real_llm,
            'llm_model': session.llm_model,
            'isolation_enabled': session.isolation_enabled,
            'setup_time': session.setup_time,
            'status': 'active'
        }
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active test sessions."""
        return [self.get_session_info(sid) for sid in self.active_sessions.keys()]
    
    async def _validate_session_requirements(self, session: TestSession) -> bool:
        """Validate requirements for a test session with comprehensive checks."""
        # Get database URL with TEST_ preference
        database_url = (
            get_env().get('TEST_DATABASE_URL') or 
            get_env().get('DATABASE_URL', '')
        )
        
        if not database_url:
            logger.error("No database URL configured for testing")
            return False
        
        # Run all validations in parallel for better performance
        validation_tasks = [
            self.validator.validate_database_connection(database_url),
            self.validator.validate_api_keys(session.use_real_llm)
        ]
        
        # Seed data validation is synchronous
        seed_data_valid = self.validator.validate_seed_data_files(session.datasets_required)
        
        # Wait for async validations
        async_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Check for exceptions in async validations
        for i, result in enumerate(async_results):
            if isinstance(result, Exception):
                logger.error(f"Validation task {i} failed with exception: {result}")
                return False
        
        # Combine all validation results
        all_validations_passed = all(async_results) and seed_data_valid
        
        validation_summary = self.validator.get_validation_summary()
        
        if validation_summary['overall_status'] == 'failed':
            logger.error(f"Session validation failed: {validation_summary}")
            return False
        
        if validation_summary['overall_status'] == 'passed_with_warnings':
            logger.warning(f"Session validation passed with warnings: {validation_summary}")
        else:
            logger.info(f"Session validation passed successfully")
        
        return all_validations_passed
    
    def _get_datasets_for_level(self, test_level: str) -> List[str]:
        """Get required datasets based on test level with enhanced mapping."""
        dataset_mappings = {
            'smoke': [],  # No seed data needed for smoke tests
            'unit': ['basic_optimization'],
            'integration': ['basic_optimization', 'complex_workflows'],
            'agents': ['basic_optimization', 'complex_workflows'],  # LLM agents need comprehensive data
            'e2e': ['basic_optimization', 'complex_workflows', 'edge_cases'],  # Full E2E needs all data
            'comprehensive': ['basic_optimization', 'complex_workflows', 'edge_cases'],
            'critical': ['basic_optimization'],  # Critical tests use minimal, reliable data
            'performance': ['basic_optimization'],  # Performance tests use consistent baseline data
            'real_llm': ['basic_optimization', 'complex_workflows'],  # Real LLM tests need realistic scenarios
        }
        
        datasets = dataset_mappings.get(test_level, ['basic_optimization'])
        logger.debug(f"Test level '{test_level}' requires datasets: {datasets}")
        return datasets


# Context manager for test sessions
@asynccontextmanager
async def test_session_context(test_level: str, use_real_llm: bool = False, 
                              llm_model: str = "gemini-2.5-pro",
                              datasets: Optional[List[str]] = None):
    """Context manager for managing test sessions."""
    orchestrator = TestEnvironmentOrchestrator()
    await orchestrator.initialize()
    
    session_id = None
    try:
        session_id = await orchestrator.setup_test_session(
            test_level, use_real_llm, llm_model, datasets
        )
        yield session_id, orchestrator
    finally:
        if session_id:
            await orchestrator.cleanup_test_session(session_id)
        await orchestrator.cleanup_all_sessions()


# Global orchestrator instance
_test_orchestrator: Optional[TestEnvironmentOrchestrator] = None

async def get_test_orchestrator() -> TestEnvironmentOrchestrator:
    """Get global test orchestrator instance with error handling."""
    global _test_orchestrator
    if _test_orchestrator is None:
        try:
            _test_orchestrator = TestEnvironmentOrchestrator()
            await _test_orchestrator.initialize()
            logger.info("Test orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize test orchestrator: {e}")
            _test_orchestrator = None
            raise
    return _test_orchestrator


async def cleanup_global_orchestrator():
    """Cleanup global test orchestrator."""
    global _test_orchestrator
    if _test_orchestrator:
        await _test_orchestrator.cleanup_all_sessions()
        _test_orchestrator = None
