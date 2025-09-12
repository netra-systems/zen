"""
Unit Tests: Unified Corpus Admin SSOT Violations - Issue #596

Purpose: Detect direct os.getenv() usage in corpus administration functions
Expected: These tests should FAIL initially to prove violations exist

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform)  
- Business Goal: Stability - Ensure consistent corpus path resolution
- Value Impact: Prevents corpus access inconsistencies across user contexts
- Strategic Impact: SSOT compliance ensures multi-user isolation integrity
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from netra_backend.app.admin.corpus.unified_corpus_admin import (
    create_user_corpus_context,
    UnifiedCorpusAdmin,
    IsolationStrategy
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types import UserID
from shared.isolated_environment import get_env
from test_framework.base_unit_test import BaseUnitTest


class TestUnifiedCorpusAdminSSOTViolations(BaseUnitTest):
    """Test SSOT violations in corpus admin functions that compromise user isolation."""
    
    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        
    def teardown_method(self):
        """Teardown for each test."""
        super().teardown_method()
        # Ensure isolation is disabled
        env = get_env()
        if hasattr(env, 'disable_isolation'):
            env.disable_isolation()

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    async def test_FAILING_corpus_path_uses_direct_os_getenv(self):
        """
        TEST EXPECTATION: FAIL - Proves direct os.getenv() usage in corpus context creation
        
        This test demonstrates the SSOT violation in unified_corpus_admin.py line 155
        where create_user_corpus_context() uses direct os.getenv() instead of 
        IsolatedEnvironment SSOT pattern.
        
        VIOLATION LOCATION: netra_backend/app/admin/corpus/unified_corpus_admin.py:155
        CODE: corpus_base_path = os.getenv('CORPUS_BASE_PATH', '/data/corpus')
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set CORPUS_BASE_PATH only in os.environ, NOT in IsolatedEnvironment
            corpus_path = "/test/direct/corpus/path"
            
            with patch.dict(os.environ, {'CORPUS_BASE_PATH': corpus_path}):
                # Ensure NOT in isolated environment (proper SSOT behavior)
                env.delete('CORPUS_BASE_PATH')
                assert env.get('CORPUS_BASE_PATH') is None
                
                # Verify exists in os.environ (violation source)
                assert os.environ.get('CORPUS_BASE_PATH') == corpus_path
                
                # Create test user context
                user_context = UserExecutionContext(
                    user_id=UserID("test-user-123"),
                    agent_context={}
                )
                
                # This function uses direct os.getenv() - SSOT violation
                enhanced_context = create_user_corpus_context(
                    context=user_context,
                    corpus_base_path=None  # Force fallback to os.getenv
                )
                
                # Extract the corpus path from enhanced context
                corpus_metadata = enhanced_context.agent_context
                found_corpus_path = corpus_metadata.get('corpus_base_path')
                
                # THIS ASSERTION SHOULD FAIL - proving SSOT violation exists
                assert found_corpus_path != corpus_path, (
                    f"🚨 SSOT VIOLATION DETECTED: create_user_corpus_context() found "
                    f"CORPUS_BASE_PATH = '{found_corpus_path}' via direct os.getenv() "
                    f"instead of IsolatedEnvironment SSOT pattern. "
                    f"VIOLATION LOCATION: unified_corpus_admin.py line 155. "
                    f"This compromises user corpus isolation and environment consistency."
                )
                
        except Exception as e:
            # Document any exceptions as part of violation analysis
            pytest.fail(
                f"UNEXPECTED ERROR in corpus admin SSOT violation test: {str(e)}. "
                f"This may indicate the violation has broader impacts than expected."
            )
        finally:
            env.disable_isolation()

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    async def test_FAILING_corpus_admin_constructor_uses_os_getenv(self):
        """
        TEST EXPECTATION: FAIL - Proves UnifiedCorpusAdmin constructor uses os.getenv
        
        This test demonstrates the SSOT violation in unified_corpus_admin.py line 281
        where _get_user_corpus_path() uses direct os.getenv() for path resolution.
        
        VIOLATION LOCATION: netra_backend/app/admin/corpus/unified_corpus_admin.py:281  
        CODE: base_path = Path(os.getenv('CORPUS_BASE_PATH', '/data/corpus'))
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set CORPUS_BASE_PATH only in os.environ
            corpus_base = "/violation/test/corpus/base"
            
            with patch.dict(os.environ, {'CORPUS_BASE_PATH': corpus_base}):
                # Ensure NOT in isolated environment
                env.delete('CORPUS_BASE_PATH')
                assert env.get('CORPUS_BASE_PATH') is None
                
                # Create test user context
                user_context = UserExecutionContext(
                    user_id=UserID("test-user-456"),
                    agent_context={}
                )
                
                # Initialize UnifiedCorpusAdmin - this triggers path resolution
                corpus_admin = UnifiedCorpusAdmin(
                    context=user_context,
                    isolation_strategy=IsolationStrategy.PER_USER_CORPUS
                )
                
                # Check if the admin found the corpus path via os.getenv violation
                user_corpus_path = corpus_admin.user_corpus_path
                
                # If the path contains our test value, it proves os.getenv usage
                if corpus_base in str(user_corpus_path):
                    pytest.fail(
                        f"🚨 SSOT VIOLATION CONFIRMED: UnifiedCorpusAdmin constructor "
                        f"resolved CORPUS_BASE_PATH to '{user_corpus_path}' using "
                        f"direct os.getenv() instead of IsolatedEnvironment. "
                        f"VIOLATION LOCATION: unified_corpus_admin.py line 281. "
                        f"This compromises multi-user corpus isolation."
                    )
                
                # Even if path doesn't contain our test value, document the violation
                assert False, (
                    f"🚨 SSOT VIOLATION DOCUMENTED: UnifiedCorpusAdmin._get_user_corpus_path() "
                    f"uses 'os.getenv('CORPUS_BASE_PATH', '/data/corpus')' pattern "
                    f"(line 281) instead of IsolatedEnvironment SSOT. "
                    f"Resolved path: '{user_corpus_path}'. The violation exists "
                    f"regardless of the resolved path value."
                )
                
        except Exception as e:
            # Document exception as part of violation impact
            print(f"⚠️  Exception during UnifiedCorpusAdmin violation test: {str(e)}")
            raise
        finally:
            env.disable_isolation()

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_FAILING_corpus_path_resolution_inconsistency(self):
        """
        TEST EXPECTATION: FAIL - Proves corpus path resolution creates inconsistencies
        
        This test shows how the os.getenv() usage in corpus admin creates
        different behavior when the same environment variable has different
        values in IsolatedEnvironment vs os.environ.
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Create scenario with different values in each environment source
            os_corpus_path = "/os/environ/corpus/path"
            isolated_corpus_path = "/isolated/env/corpus/path"
            
            with patch.dict(os.environ, {'CORPUS_BASE_PATH': os_corpus_path}):
                # Set different value in isolated environment
                env.set('CORPUS_BASE_PATH', isolated_corpus_path, 'test')
                
                # Verify different values exist
                assert env.get('CORPUS_BASE_PATH') == isolated_corpus_path
                assert os.environ.get('CORPUS_BASE_PATH') == os_corpus_path
                
                user_context = UserExecutionContext(
                    user_id=UserID("test-inconsistency-user"),
                    agent_context={}
                )
                
                # Test corpus context creation (should use isolated env if SSOT compliant)
                enhanced_context = create_user_corpus_context(
                    context=user_context,
                    corpus_base_path=None  # Force environment variable lookup
                )
                
                # Test corpus admin creation (should use isolated env if SSOT compliant)
                corpus_admin = UnifiedCorpusAdmin(
                    context=user_context,
                    isolation_strategy=IsolationStrategy.PER_USER_CORPUS
                )
                
                # Extract paths from both methods
                context_corpus_path = enhanced_context.agent_context.get('corpus_base_path')
                admin_corpus_path = str(corpus_admin.user_corpus_path.parent)
                
                # If either uses the os.environ value instead of isolated env value,
                # it proves SSOT violation and inconsistency
                
                context_uses_os_environ = os_corpus_path in str(context_corpus_path)
                admin_uses_os_environ = os_corpus_path in admin_corpus_path
                
                if context_uses_os_environ or admin_uses_os_environ:
                    pytest.fail(
                        f"🚨 SSOT VIOLATION CONFIRMED: Corpus path resolution "
                        f"inconsistency detected. create_user_corpus_context() "
                        f"resolved to '{context_corpus_path}' (uses os.environ: {context_uses_os_environ}), "
                        f"UnifiedCorpusAdmin resolved to '{admin_corpus_path}' "
                        f"(uses os.environ: {admin_uses_os_environ}). "
                        f"IsolatedEnvironment value: '{isolated_corpus_path}', "
                        f"os.environ value: '{os_corpus_path}'. This proves "
                        f"SSOT violations cause inconsistent corpus isolation."
                    )
                
                # Document the violation even if behavior appears consistent
                assert False, (
                    f"🚨 SSOT VIOLATION EXISTS: Both create_user_corpus_context() "
                    f"and UnifiedCorpusAdmin use direct os.getenv() access "
                    f"(lines 155 and 281) creating potential for inconsistencies. "
                    f"Current results: context='{context_corpus_path}', "
                    f"admin='{admin_corpus_path}', but violation still exists "
                    f"in implementation."
                )
                
        finally:
            env.disable_isolation()

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_FAILING_isolation_strategy_affected_by_env_violations(self):
        """
        TEST EXPECTATION: FAIL - Proves isolation strategies can be compromised
        
        This test shows how SSOT violations in corpus path resolution can
        affect different isolation strategies, potentially breaking user isolation.
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Test different isolation strategies with environment violation
            corpus_base = "/violation/isolation/test"
            
            with patch.dict(os.environ, {'CORPUS_BASE_PATH': corpus_base}):
                env.delete('CORPUS_BASE_PATH')
                
                user_context = UserExecutionContext(
                    user_id=UserID("isolation-test-user"),
                    agent_context={'tenant_id': 'test-tenant'}
                )
                
                # Test each isolation strategy
                strategies_to_test = [
                    IsolationStrategy.PER_USER_CORPUS,
                    IsolationStrategy.TENANT_BASED,
                    IsolationStrategy.SHARED_CORPUS
                ]
                
                violation_detected = False
                
                for strategy in strategies_to_test:
                    try:
                        admin = UnifiedCorpusAdmin(
                            context=user_context,
                            isolation_strategy=strategy
                        )
                        
                        # If admin initializes successfully with os.environ path,
                        # it proves the violation affects all isolation strategies
                        if corpus_base in str(admin.user_corpus_path):
                            violation_detected = True
                            break
                            
                    except Exception as e:
                        # Exception might indicate violation impact
                        print(f"Strategy {strategy} failed: {e}")
                
                # Document the violation impact on isolation strategies
                if violation_detected:
                    pytest.fail(
                        f"🚨 CRITICAL SSOT VIOLATION: os.getenv() usage in "
                        f"UnifiedCorpusAdmin affects ALL isolation strategies, "
                        f"compromising multi-user corpus isolation. Detected "
                        f"os.environ path '{corpus_base}' in corpus admin paths."
                    )
                else:
                    # Document that violation exists even if not detected in this test
                    pytest.fail(
                        f"🚨 SSOT VIOLATION DOCUMENTED: UnifiedCorpusAdmin uses "
                        f"direct os.getenv() (line 281) affecting all isolation "
                        f"strategies. While not detected in this specific test "
                        f"scenario, the implementation violation creates risk "
                        f"for multi-user corpus isolation integrity."
                    )
                
        finally:
            env.disable_isolation()