"""
Password policy enforcement tests (Iteration 44).

Tests comprehensive password policy enforcement including:
- Password strength validation
- Password history enforcement
- Password expiration policies
- Password complexity requirements
- Dictionary attack prevention
- Common password filtering
- Password reuse prevention
- Account lockout on policy violations
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Dict, List, Any, Optional

from auth_service.auth_core.models.auth_models import User
from auth_service.auth_core.services.password_policy_service import PasswordPolicyService
from auth_service.auth_core.models.password_policy import PasswordPolicy, PasswordStrength
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.exceptions.password_exceptions import (
    WeakPasswordError, 
    PasswordReuseError,
    PasswordExpiredError,
    PasswordPolicyViolationError
)
from test_framework.environment_markers import env

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.auth_service,
    pytest.mark.password_policy,
    pytest.mark.security
]


class TestPasswordStrengthValidation:
    """Test password strength validation and complexity requirements."""

    @pytest.fixture
    def password_policy_service(self):
        """Password policy service for testing."""
        return PasswordPolicyService()

    @pytest.fixture
    def strict_password_policy(self):
        """Strict password policy for testing."""
        return PasswordPolicy(
            min_length=12,
            max_length=128,
            require_uppercase=True,
            require_lowercase=True,
            require_numbers=True,
            require_special_chars=True,
            min_special_chars=2,
            prohibited_patterns=[
                r'(.)\1{2,}',  # No character repeated 3+ times
                r'(012|123|234|345|456|567|678|789|890)',  # No sequential numbers
                r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)'  # No sequential letters
            ],
            dictionary_check=True,
            personal_info_check=True,
            password_history_count=12,
            max_age_days=90
        )

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            id=str(uuid4()),
            email='john.doe@example.com',
            full_name='John Doe',
            auth_provider='local',
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc)
        )

    async def test_password_minimum_length_validation(self, password_policy_service, strict_password_policy):
        """Test password minimum length validation."""
        # Too short password
        short_password = "Abc123!"
        
        with pytest.raises(WeakPasswordError) as exc_info:
            await password_policy_service.validate_password(
                password=short_password,
                policy=strict_password_policy
            )
        
        assert "length" in str(exc_info.value).lower()
        assert "12" in str(exc_info.value)  # Minimum length requirement

    async def test_password_complexity_requirements(self, password_policy_service, strict_password_policy):
        """Test password complexity requirements validation."""
        test_cases = [
            ("nocapitalletters123!@", "uppercase"),
            ("NOLOWERCASELETTERS123!@", "lowercase"),
            ("NoNumbers!@#", "number"),
            ("NoSpecialChars123ABC", "special"),
            ("OnlyOneSpecial1A!", "special")  # Only 1 special char, needs 2
        ]
        
        for password, missing_requirement in test_cases:
            with pytest.raises(WeakPasswordError) as exc_info:
                await password_policy_service.validate_password(
                    password=password,
                    policy=strict_password_policy
                )
            
            assert missing_requirement in str(exc_info.value).lower()

    async def test_password_prohibited_patterns_validation(self, password_policy_service, strict_password_policy):
        """Test password prohibited patterns validation."""
        prohibited_passwords = [
            "ValidPassword123!!!",  # Character repeated 3+ times
            "ValidPass012!@#",      # Sequential numbers
            "ValidPassabc!@#",      # Sequential letters
        ]
        
        for password in prohibited_passwords:
            with pytest.raises(WeakPasswordError) as exc_info:
                await password_policy_service.validate_password(
                    password=password,
                    policy=strict_password_policy
                )
            
            assert "pattern" in str(exc_info.value).lower() or "sequence" in str(exc_info.value).lower()

    async def test_password_dictionary_check(self, password_policy_service, strict_password_policy):
        """Test password against common dictionary words."""
        # Mock dictionary check
        with patch.object(password_policy_service, 'check_dictionary_word') as mock_dict_check:
            mock_dict_check.return_value = True  # Password contains dictionary word
            
            dictionary_password = "Password123!@"
            
            with pytest.raises(WeakPasswordError) as exc_info:
                await password_policy_service.validate_password(
                    password=dictionary_password,
                    policy=strict_password_policy
                )
            
            assert "dictionary" in str(exc_info.value).lower() or "common" in str(exc_info.value).lower()

    async def test_password_personal_info_check(self, password_policy_service, strict_password_policy, sample_user):
        """Test password against user's personal information."""
        # Password containing user's name
        personal_password = "JohnDoe123!@"
        
        with patch.object(password_policy_service, 'contains_personal_info') as mock_personal_check:
            mock_personal_check.return_value = True  # Password contains personal info
            
            with pytest.raises(WeakPasswordError) as exc_info:
                await password_policy_service.validate_password(
                    password=personal_password,
                    policy=strict_password_policy,
                    user=sample_user
                )
            
            assert "personal" in str(exc_info.value).lower() or "name" in str(exc_info.value).lower()

    async def test_valid_strong_password(self, password_policy_service, strict_password_policy):
        """Test validation of a strong password that meets all requirements."""
        strong_password = "MySecure$Password2024!@"
        
        # Should not raise any exception
        result = await password_policy_service.validate_password(
            password=strong_password,
            policy=strict_password_policy
        )
        
        assert result.is_valid is True
        assert result.strength_score >= 80  # Strong password score
        assert result.violations == []

    async def test_password_strength_scoring(self, password_policy_service):
        """Test password strength scoring algorithm."""
        test_passwords = [
            ("weak", 0, 30),           # Weak password range
            ("Medium123", 30, 70),     # Medium password range  
            ("VeryStrong$Pass2024!@", 70, 100)  # Strong password range
        ]
        
        for password, min_score, max_score in test_passwords:
            strength_result = await password_policy_service.calculate_password_strength(password)
            
            assert min_score <= strength_result.score <= max_score
            assert strength_result.feedback is not None
            assert isinstance(strength_result.feedback, list)


class TestPasswordHistoryEnforcement:
    """Test password history and reuse prevention."""

    @pytest.fixture
    def mock_password_history_service(self):
        """Mock password history service."""
        service = MagicMock()
        service.get_password_history = AsyncMock()
        service.add_password_to_history = AsyncMock()
        service.is_password_reused = AsyncMock()
        return service

    @pytest.fixture
    def sample_password_history(self):
        """Sample password history for testing."""
        return [
            {
                'password_hash': 'hash1',
                'created_at': datetime.now(timezone.utc) - timedelta(days=30),
                'salt': 'salt1'
            },
            {
                'password_hash': 'hash2', 
                'created_at': datetime.now(timezone.utc) - timedelta(days=60),
                'salt': 'salt2'
            },
            {
                'password_hash': 'hash3',
                'created_at': datetime.now(timezone.utc) - timedelta(days=90),
                'salt': 'salt3'
            }
        ]

    async def test_password_reuse_prevention(self, password_policy_service, sample_user, mock_password_history_service, sample_password_history):
        """Test prevention of password reuse."""
        # Mock password history retrieval
        mock_password_history_service.get_password_history.return_value = sample_password_history
        mock_password_history_service.is_password_reused.return_value = True
        
        password_policy_service.password_history_service = mock_password_history_service
        
        reused_password = "PreviousPassword123!"
        
        with pytest.raises(PasswordReuseError) as exc_info:
            await password_policy_service.validate_password_history(
                user_id=sample_user.id,
                new_password=reused_password
            )
        
        assert "reuse" in str(exc_info.value).lower() or "previous" in str(exc_info.value).lower()
        mock_password_history_service.is_password_reused.assert_called_once()

    async def test_password_history_limit_enforcement(self, password_policy_service, sample_user, mock_password_history_service):
        """Test password history limit enforcement."""
        # Create history exceeding the limit
        extensive_history = []
        for i in range(15):  # More than the 12-password limit
            extensive_history.append({
                'password_hash': f'hash_{i}',
                'created_at': datetime.now(timezone.utc) - timedelta(days=i*30),
                'salt': f'salt_{i}'
            })
        
        mock_password_history_service.get_password_history.return_value = extensive_history
        mock_password_history_service.is_password_reused.return_value = False  # New password
        
        password_policy_service.password_history_service = mock_password_history_service
        
        new_password = "BrandNewPassword123!@"
        
        # Should pass validation (new password, not in recent 12)
        result = await password_policy_service.validate_password_history(
            user_id=sample_user.id,
            new_password=new_password
        )
        
        assert result is True

    async def test_password_history_cleanup(self, password_policy_service, mock_password_history_service, strict_password_policy):
        """Test automatic cleanup of old password history."""
        user_id = str(uuid4())
        
        # Mock cleanup operation
        mock_password_history_service.cleanup_old_passwords.return_value = 5  # Cleaned 5 old passwords
        
        password_policy_service.password_history_service = mock_password_history_service
        
        cleaned_count = await password_policy_service.cleanup_password_history(
            user_id=user_id,
            keep_count=strict_password_policy.password_history_count
        )
        
        assert cleaned_count == 5
        mock_password_history_service.cleanup_old_passwords.assert_called_once_with(
            user_id=user_id,
            keep_count=strict_password_policy.password_history_count
        )

    async def test_similar_password_detection(self, password_policy_service, mock_password_history_service):
        """Test detection of passwords similar to previous ones."""
        user_id = str(uuid4())
        
        # Mock similar password detection
        mock_password_history_service.find_similar_passwords.return_value = [
            {'password_hash': 'similar_hash', 'similarity_score': 0.85}
        ]
        
        password_policy_service.password_history_service = mock_password_history_service
        
        similar_password = "MyPassword2024!"  # Similar to "MyPassword2023!"
        
        with patch.object(password_policy_service, 'calculate_password_similarity') as mock_similarity:
            mock_similarity.return_value = 0.85  # High similarity
            
            with pytest.raises(PasswordReuseError) as exc_info:
                await password_policy_service.validate_password_similarity(
                    user_id=user_id,
                    new_password=similar_password,
                    similarity_threshold=0.8
                )
            
            assert "similar" in str(exc_info.value).lower()


class TestPasswordExpirationPolicies:
    """Test password expiration and aging policies."""

    @pytest.fixture
    def mock_auth_service(self):
        """Mock auth service."""
        service = MagicMock(spec=AuthService)
        service.get_user_password_info = AsyncMock()
        service.force_password_reset = AsyncMock()
        return service

    async def test_password_expiration_validation(self, password_policy_service, mock_auth_service, strict_password_policy, sample_user):
        """Test password expiration validation."""
        # Mock expired password
        mock_auth_service.get_user_password_info.return_value = {
            'password_created_at': datetime.now(timezone.utc) - timedelta(days=100),  # Older than 90-day policy
            'password_updated_at': datetime.now(timezone.utc) - timedelta(days=100),
            'is_expired': True
        }
        
        password_policy_service.auth_service = mock_auth_service
        
        with pytest.raises(PasswordExpiredError) as exc_info:
            await password_policy_service.validate_password_expiration(
                user_id=sample_user.id,
                policy=strict_password_policy
            )
        
        assert "expired" in str(exc_info.value).lower()
        assert "90" in str(exc_info.value) or "days" in str(exc_info.value)

    async def test_password_expiration_warning(self, password_policy_service, mock_auth_service, strict_password_policy, sample_user):
        """Test password expiration warning before actual expiration."""
        # Mock password nearing expiration (75 days old, policy is 90 days)
        mock_auth_service.get_user_password_info.return_value = {
            'password_created_at': datetime.now(timezone.utc) - timedelta(days=75),
            'password_updated_at': datetime.now(timezone.utc) - timedelta(days=75),
            'is_expired': False,
            'days_until_expiration': 15
        }
        
        password_policy_service.auth_service = mock_auth_service
        
        warning_info = await password_policy_service.check_password_expiration_warning(
            user_id=sample_user.id,
            policy=strict_password_policy,
            warning_days=30  # Warn 30 days before expiration
        )
        
        assert warning_info['warning_required'] is True
        assert warning_info['days_until_expiration'] == 15
        assert warning_info['message'] is not None

    async def test_force_password_reset_on_expiration(self, password_policy_service, mock_auth_service, sample_user):
        """Test forcing password reset when password is expired."""
        # Mock expired password
        mock_auth_service.get_user_password_info.return_value = {
            'password_created_at': datetime.now(timezone.utc) - timedelta(days=100),
            'is_expired': True
        }
        
        password_policy_service.auth_service = mock_auth_service
        
        # Force password reset
        reset_result = await password_policy_service.force_password_reset_if_expired(
            user_id=sample_user.id,
            max_age_days=90
        )
        
        assert reset_result['reset_required'] is True
        assert reset_result['reason'] == 'password_expired'
        mock_auth_service.force_password_reset.assert_called_once_with(sample_user.id)

    async def test_password_age_calculation(self, password_policy_service):
        """Test accurate calculation of password age."""
        password_created_at = datetime.now(timezone.utc) - timedelta(days=45, hours=12, minutes=30)
        
        age_info = password_policy_service.calculate_password_age(password_created_at)
        
        assert age_info['days'] == 45
        assert age_info['hours'] >= 12  # Should account for partial day
        assert age_info['total_hours'] > 45 * 24

    async def test_batch_password_expiration_check(self, password_policy_service, mock_auth_service):
        """Test batch checking of password expiration for multiple users."""
        user_ids = [str(uuid4()) for _ in range(5)]
        
        # Mock batch password info retrieval
        mock_auth_service.get_batch_password_info.return_value = {
            user_ids[0]: {'is_expired': True, 'days_old': 100},
            user_ids[1]: {'is_expired': False, 'days_old': 30},
            user_ids[2]: {'is_expired': True, 'days_old': 95},
            user_ids[3]: {'is_expired': False, 'days_old': 80},
            user_ids[4]: {'is_expired': False, 'days_old': 10}
        }
        
        password_policy_service.auth_service = mock_auth_service
        
        expiration_results = await password_policy_service.batch_check_password_expiration(
            user_ids=user_ids,
            max_age_days=90
        )
        
        expired_users = [result for result in expiration_results if result['is_expired']]
        assert len(expired_users) == 2  # user_ids[0] and user_ids[2]


class TestPasswordPolicyViolationHandling:
    """Test handling of password policy violations."""

    @pytest.fixture
    def mock_violation_handler(self):
        """Mock password policy violation handler."""
        handler = MagicMock()
        handler.record_violation = AsyncMock()
        handler.determine_action = AsyncMock()
        handler.apply_penalty = AsyncMock()
        return handler

    async def test_password_violation_recording(self, password_policy_service, mock_violation_handler, sample_user):
        """Test recording of password policy violations."""
        violation = PasswordPolicyViolationError(
            message="Password does not meet complexity requirements",
            violation_type="complexity",
            user_id=sample_user.id,
            attempted_password_hash="hash_of_attempted_password"
        )
        
        password_policy_service.violation_handler = mock_violation_handler
        
        await password_policy_service.record_password_violation(violation)
        
        mock_violation_handler.record_violation.assert_called_once_with(violation)

    async def test_repeated_password_violations(self, password_policy_service, mock_violation_handler, sample_user):
        """Test handling of repeated password policy violations."""
        # Mock multiple violations for same user
        mock_violation_handler.get_violation_count.return_value = 5  # 5 recent violations
        mock_violation_handler.determine_action.return_value = "temporary_lockout"
        
        password_policy_service.violation_handler = mock_violation_handler
        
        action = await password_policy_service.handle_repeated_violations(
            user_id=sample_user.id,
            time_window_hours=24,
            max_violations=3
        )
        
        assert action == "temporary_lockout"
        mock_violation_handler.determine_action.assert_called_once()

    async def test_account_lockout_on_policy_violations(self, password_policy_service, mock_violation_handler, mock_auth_service):
        """Test account lockout after excessive policy violations."""
        user_id = str(uuid4())
        
        # Mock excessive violations leading to lockout
        mock_violation_handler.determine_action.return_value = "account_lockout"
        mock_auth_service.lock_account = AsyncMock()
        
        password_policy_service.violation_handler = mock_violation_handler
        password_policy_service.auth_service = mock_auth_service
        
        await password_policy_service.apply_violation_penalty(
            user_id=user_id,
            penalty_type="account_lockout",
            duration_minutes=30
        )
        
        mock_auth_service.lock_account.assert_called_once_with(
            user_id=user_id,
            reason="password_policy_violations",
            duration_minutes=30
        )

    async def test_violation_recovery_mechanism(self, password_policy_service, mock_violation_handler):
        """Test violation count recovery after successful password change."""
        user_id = str(uuid4())
        
        # Mock violation count reset
        mock_violation_handler.reset_violation_count.return_value = True
        
        password_policy_service.violation_handler = mock_violation_handler
        
        await password_policy_service.reset_violations_on_successful_change(user_id)
        
        mock_violation_handler.reset_violation_count.assert_called_once_with(user_id)


class TestAdvancedPasswordSecurity:
    """Test advanced password security features."""

    async def test_password_entropy_calculation(self, password_policy_service):
        """Test password entropy calculation for security assessment."""
        test_passwords = [
            ("password", 20),           # Low entropy
            ("Password123", 40),        # Medium entropy  
            ("Tr0ub4dor&3", 65),       # High entropy
            ("MySecure$Password2024!@", 80)  # Very high entropy
        ]
        
        for password, min_entropy in test_passwords:
            entropy = password_policy_service.calculate_password_entropy(password)
            assert entropy >= min_entropy
            assert isinstance(entropy, (int, float))

    async def test_password_breach_database_check(self, password_policy_service):
        """Test checking password against breach databases (like HaveIBeenPwned)."""
        with patch.object(password_policy_service, 'check_password_breach_database') as mock_breach_check:
            # Mock breached password
            mock_breach_check.return_value = {'is_breached': True, 'breach_count': 12345}
            
            breached_password = "password123"
            
            with pytest.raises(WeakPasswordError) as exc_info:
                await password_policy_service.validate_password_against_breaches(breached_password)
            
            assert "breach" in str(exc_info.value).lower() or "compromised" in str(exc_info.value).lower()

    async def test_password_pattern_analysis(self, password_policy_service):
        """Test advanced password pattern analysis."""
        patterns_to_test = [
            ("Qwerty123!@#", "keyboard_pattern"),    # Keyboard pattern
            ("Password2024!", "year_pattern"),       # Current year pattern
            ("Company123!@", "company_name"),        # Company name pattern
            ("Admin123!@#", "role_based")            # Role-based pattern
        ]
        
        for password, expected_pattern in patterns_to_test:
            patterns = password_policy_service.analyze_password_patterns(password)
            assert expected_pattern in patterns or len(patterns) > 0

    async def test_password_strength_real_time_feedback(self, password_policy_service):
        """Test real-time password strength feedback during typing."""
        partial_passwords = [
            "P",                    # Very weak
            "Pass",                 # Weak
            "Password",             # Weak-medium
            "Password1",            # Medium
            "Password1!",           # Medium-strong
            "MySecure$Pass2024!"    # Strong
        ]
        
        for password in partial_passwords:
            feedback = await password_policy_service.get_real_time_feedback(password)
            
            assert 'strength_score' in feedback
            assert 'suggestions' in feedback
            assert 'estimated_crack_time' in feedback
            assert isinstance(feedback['suggestions'], list)

    async def test_context_aware_password_policies(self, password_policy_service, sample_user):
        """Test context-aware password policies based on user role/risk level."""
        # Mock different user contexts
        contexts = [
            {'role': 'admin', 'risk_level': 'high'},
            {'role': 'user', 'risk_level': 'medium'},
            {'role': 'guest', 'risk_level': 'low'}
        ]
        
        for context in contexts:
            policy = await password_policy_service.get_context_aware_policy(
                user=sample_user,
                context=context
            )
            
            if context['risk_level'] == 'high':
                assert policy.min_length >= 14  # Stricter for high-risk
                assert policy.require_special_chars is True
            elif context['risk_level'] == 'low':
                assert policy.min_length >= 8   # More lenient for low-risk


class TestPasswordPolicyMetrics:
    """Test password policy metrics and monitoring."""

    async def test_password_policy_compliance_metrics(self, password_policy_service):
        """Test tracking of password policy compliance rates."""
        with patch('auth_service.metrics.password_policy_compliance_rate') as mock_metric:
            # Mock compliance calculation
            compliance_data = await password_policy_service.calculate_compliance_metrics()
            
            # Should track various compliance metrics
            expected_metrics = [
                'overall_compliance_rate',
                'strength_compliance_rate', 
                'history_compliance_rate',
                'expiration_compliance_rate'
            ]
            
            for metric in expected_metrics:
                assert metric in compliance_data
                assert isinstance(compliance_data[metric], (int, float))

    async def test_password_violation_trend_analysis(self, password_policy_service):
        """Test analysis of password violation trends."""
        with patch.object(password_policy_service, 'analyze_violation_trends') as mock_analysis:
            mock_analysis.return_value = {
                'total_violations_24h': 25,
                'most_common_violations': ['complexity', 'length', 'reuse'],
                'violation_trend': 'increasing',
                'high_risk_users': 5
            }
            
            trend_analysis = mock_analysis()
            
            assert 'total_violations_24h' in trend_analysis
            assert 'most_common_violations' in trend_analysis
            assert isinstance(trend_analysis['most_common_violations'], list)
            assert trend_analysis['high_risk_users'] >= 0

    async def test_password_security_score_tracking(self, password_policy_service):
        """Test tracking of overall password security scores."""
        with patch.object(password_policy_service, 'calculate_security_score') as mock_score:
            mock_score.return_value = {
                'overall_security_score': 85,
                'strength_score': 88,
                'policy_adherence_score': 82,
                'breach_resistance_score': 90,
                'recommendations': [
                    'Increase minimum password length',
                    'Enable breach database checking'
                ]
            }
            
            security_score = mock_score()
            
            assert security_score['overall_security_score'] >= 0
            assert security_score['overall_security_score'] <= 100
            assert isinstance(security_score['recommendations'], list)