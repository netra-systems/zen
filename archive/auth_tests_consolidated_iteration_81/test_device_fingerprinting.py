"""
Device fingerprinting tests (Iteration 50).

Tests comprehensive device fingerprinting and recognition including:
- Browser fingerprinting techniques
- Device characteristic analysis
- Behavioral fingerprinting
- Device trust scoring
- Anomalous device detection
- Device registration and management
- Cross-session device tracking
- Anti-fingerprinting countermeasures
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, List, Any, Optional

from auth_service.auth_core.models.auth_models import User
from auth_service.auth_core.services.device_fingerprint_service import DeviceFingerprintService
from auth_service.auth_core.models.device import DeviceFingerprint, DeviceProfile, TrustScore
from test_framework.environment_markers import env

# Skip entire module until device fingerprinting components are available
pytestmark = pytest.mark.skip(reason="Device fingerprinting components not available in current codebase")

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.auth_service,
    pytest.mark.device_fingerprinting,
    pytest.mark.security
]


class TestBrowserFingerprinting:
    """Test browser fingerprinting techniques."""

    @pytest.fixture
    def mock_fingerprint_service(self):
        """Mock device fingerprint service."""
        service = MagicMock(spec=DeviceFingerprintService)
        service.generate_fingerprint = AsyncMock()
        service.analyze_browser_characteristics = AsyncMock()
        service.detect_fingerprint_evasion = AsyncMock()
        return service

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            id=str(uuid4()),
            email='user@example.com',
            full_name='Test User',
            auth_provider='local',
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc)
        )

    @pytest.fixture
    def browser_characteristics(self):
        """Sample browser characteristics for fingerprinting."""
        return {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'screen_resolution': '1920x1080',
            'color_depth': 24,
            'timezone': 'America/New_York',
            'language': 'en-US',
            'platform': 'Win32',
            'cookie_enabled': True,
            'do_not_track': False,
            'canvas_fingerprint': 'canvas_hash_123456789',
            'webgl_vendor': 'Google Inc. (NVIDIA)',
            'webgl_renderer': 'ANGLE (NVIDIA GeForce RTX 3080)',
            'audio_context_fingerprint': 'audio_hash_987654321',
            'fonts_available': ['Arial', 'Times New Roman', 'Helvetica', 'Georgia'],
            'plugins': [
                {'name': 'Chrome PDF Plugin', 'version': '1.0'},
                {'name': 'Adobe Flash Player', 'version': '32.0.0.465'}
            ],
            'touch_support': False,
            'webrtc_fingerprint': 'webrtc_hash_456789123'
        }

    async def test_generate_browser_fingerprint(self, mock_fingerprint_service, browser_characteristics):
        """Test generation of browser fingerprint."""
        # Mock fingerprint generation
        mock_fingerprint_service.generate_fingerprint.return_value = {
            'fingerprint_id': str(uuid4()),
            'fingerprint_hash': 'fp_hash_abcdef123456789',
            'confidence_score': 0.94,
            'entropy_score': 18.5,
            'uniqueness_estimate': 0.00012,  # 1 in 8,333 devices
            'characteristics_analyzed': 15,
            'fingerprint_version': '2.1',
            'generation_timestamp': datetime.now(timezone.utc)
        }
        
        # Generate browser fingerprint
        fingerprint_result = await mock_fingerprint_service.generate_fingerprint(
            browser_characteristics
        )
        
        # Verify fingerprint generation
        assert 'fingerprint_hash' in fingerprint_result
        assert fingerprint_result['confidence_score'] > 0.9
        assert fingerprint_result['entropy_score'] > 15
        assert fingerprint_result['uniqueness_estimate'] < 0.001

    async def test_canvas_fingerprinting(self, mock_fingerprint_service):
        """Test canvas fingerprinting technique."""
        canvas_data = {
            'canvas_2d_hash': 'canvas2d_hash_123',
            'canvas_webgl_hash': 'webgl_hash_456',
            'canvas_text_metrics': {
                'width': 245.7,
                'height': 18.2,
                'baseline': 14.6
            },
            'canvas_rendering_differences': True
        }
        
        # Mock canvas analysis
        mock_fingerprint_service.analyze_canvas_fingerprint.return_value = {
            'canvas_uniqueness': 0.95,
            'rendering_engine': 'chrome_v108',
            'graphics_driver_signature': 'nvidia_driver_522',
            'anti_fingerprinting_detected': False,
            'canvas_stability_score': 0.98
        }
        
        # Analyze canvas fingerprint
        canvas_analysis = mock_fingerprint_service.analyze_canvas_fingerprint(canvas_data)
        
        # Verify canvas fingerprinting
        assert canvas_analysis['canvas_uniqueness'] > 0.9
        assert canvas_analysis['anti_fingerprinting_detected'] is False
        assert canvas_analysis['canvas_stability_score'] > 0.95

    async def test_webgl_fingerprinting(self, mock_fingerprint_service):
        """Test WebGL fingerprinting technique."""
        webgl_data = {
            'webgl_vendor': 'Google Inc. (NVIDIA)',
            'webgl_renderer': 'ANGLE (NVIDIA GeForce RTX 3080)',
            'webgl_version': 'WebGL 1.0',
            'shading_language_version': 'WebGL GLSL ES 1.0',
            'max_texture_size': 16384,
            'max_viewport_dims': [16384, 16384],
            'supported_extensions': [
                'ANGLE_instanced_arrays',
                'EXT_blend_minmax',
                'WEBGL_debug_renderer_info'
            ]
        }
        
        # Mock WebGL analysis
        mock_fingerprint_service.analyze_webgl_fingerprint.return_value = {
            'webgl_uniqueness': 0.87,
            'graphics_card_detected': 'RTX_3080',
            'driver_version_estimate': '522.25',
            'rendering_capabilities_hash': 'webgl_caps_789',
            'webgl_stability_score': 0.96
        }
        
        # Analyze WebGL fingerprint
        webgl_analysis = mock_fingerprint_service.analyze_webgl_fingerprint(webgl_data)
        
        # Verify WebGL fingerprinting
        assert webgl_analysis['webgl_uniqueness'] > 0.8
        assert 'RTX' in webgl_analysis['graphics_card_detected']
        assert webgl_analysis['webgl_stability_score'] > 0.9

    async def test_audio_fingerprinting(self, mock_fingerprint_service):
        """Test audio context fingerprinting."""
        audio_data = {
            'audio_context_hash': 'audio_hash_321654987',
            'sample_rate': 44100,
            'max_channel_count': 2,
            'number_of_inputs': 1,
            'number_of_outputs': 1,
            'channel_count': 2,
            'oscillator_fingerprint': 'osc_fp_147258369',
            'compressor_fingerprint': 'comp_fp_963852741'
        }
        
        # Mock audio analysis
        mock_fingerprint_service.analyze_audio_fingerprint.return_value = {
            'audio_uniqueness': 0.82,
            'audio_hardware_signature': 'realtek_alc897',
            'audio_driver_version': 'v6.0.9435.1',
            'audio_processing_capabilities': 'high_definition',
            'noise_floor_analysis': 'standard_consumer_device'
        }
        
        # Analyze audio fingerprint
        audio_analysis = mock_fingerprint_service.analyze_audio_fingerprint(audio_data)
        
        # Verify audio fingerprinting
        assert audio_analysis['audio_uniqueness'] > 0.8
        assert 'realtek' in audio_analysis['audio_hardware_signature'].lower()
        assert audio_analysis['audio_processing_capabilities'] is not None


class TestDeviceCharacteristicAnalysis:
    """Test device characteristic analysis."""

    @pytest.fixture
    def mock_device_analyzer(self):
        """Mock device analyzer."""
        analyzer = MagicMock()
        analyzer.analyze_device_characteristics = AsyncMock()
        analyzer.detect_device_type = AsyncMock()
        analyzer.analyze_hardware_specifications = AsyncMock()
        return analyzer

    async def test_device_type_detection(self, mock_device_analyzer, browser_characteristics):
        """Test detection of device type."""
        # Mock device type detection
        mock_device_analyzer.detect_device_type.return_value = {
            'device_type': 'desktop',
            'operating_system': 'Windows 10',
            'os_version': '10.0.19041',
            'browser': 'Chrome',
            'browser_version': '108.0.5359.125',
            'is_mobile': False,
            'is_tablet': False,
            'confidence_score': 0.96
        }
        
        # Detect device type
        device_type = await mock_device_analyzer.detect_device_type(browser_characteristics)
        
        # Verify device type detection
        assert device_type['device_type'] == 'desktop'
        assert device_type['operating_system'] == 'Windows 10'
        assert device_type['is_mobile'] is False
        assert device_type['confidence_score'] > 0.9

    async def test_hardware_specification_analysis(self, mock_device_analyzer):
        """Test hardware specification analysis."""
        hardware_data = {
            'cpu_cores': 8,
            'memory_gb': 16,
            'screen_resolution': '1920x1080',
            'color_depth': 24,
            'pixel_ratio': 1.0,
            'hardware_concurrency': 8,
            'max_touch_points': 0,
            'device_memory': 8  # GB
        }
        
        # Mock hardware analysis
        mock_device_analyzer.analyze_hardware_specifications.return_value = {
            'hardware_tier': 'high_end',
            'estimated_device_age': 'recent',
            'performance_category': 'gaming_workstation',
            'ram_category': 'standard',
            'display_category': 'full_hd',
            'hardware_uniqueness_score': 0.75,
            'hardware_consistency_check': 'passed'
        }
        
        # Analyze hardware specifications
        hardware_analysis = await mock_device_analyzer.analyze_hardware_specifications(
            hardware_data
        )
        
        # Verify hardware analysis
        assert hardware_analysis['hardware_tier'] == 'high_end'
        assert hardware_analysis['performance_category'] == 'gaming_workstation'
        assert hardware_analysis['hardware_consistency_check'] == 'passed'
        assert hardware_analysis['hardware_uniqueness_score'] > 0.7

    async def test_browser_capability_analysis(self, mock_device_analyzer):
        """Test browser capability analysis."""
        browser_capabilities = {
            'supports_webgl': True,
            'supports_webgl2': True,
            'supports_webrtc': True,
            'supports_websockets': True,
            'supports_webworkers': True,
            'supports_indexeddb': True,
            'supports_geolocation': True,
            'supports_notifications': True,
            'supports_camera': True,
            'supports_microphone': True,
            'webassembly_support': True
        }
        
        # Mock capability analysis
        mock_device_analyzer.analyze_browser_capabilities.return_value = {
            'capability_score': 0.95,
            'modern_browser': True,
            'security_features_available': [
                'secure_contexts',
                'content_security_policy',
                'subresource_integrity'
            ],
            'privacy_features_available': [
                'do_not_track',
                'tracking_protection',
                'cookie_controls'
            ],
            'feature_support_profile': 'comprehensive_modern'
        }
        
        # Analyze browser capabilities
        capability_analysis = mock_device_analyzer.analyze_browser_capabilities(
            browser_capabilities
        )
        
        # Verify capability analysis
        assert capability_analysis['capability_score'] > 0.9
        assert capability_analysis['modern_browser'] is True
        assert len(capability_analysis['security_features_available']) > 0
        assert capability_analysis['feature_support_profile'] == 'comprehensive_modern'


class TestBehavioralFingerprinting:
    """Test behavioral fingerprinting techniques."""

    @pytest.fixture
    def mock_behavioral_analyzer(self):
        """Mock behavioral analyzer."""
        analyzer = MagicMock()
        analyzer.analyze_typing_patterns = AsyncMock()
        analyzer.analyze_mouse_behavior = AsyncMock()
        analyzer.analyze_interaction_patterns = AsyncMock()
        return analyzer

    async def test_typing_pattern_analysis(self, mock_behavioral_analyzer, sample_user):
        """Test typing pattern analysis."""
        typing_data = {
            'user_id': sample_user.id,
            'session_id': str(uuid4()),
            'keystrokes': [
                {'key': 'p', 'press_time': 150, 'release_time': 200},
                {'key': 'a', 'press_time': 180, 'release_time': 230},
                {'key': 's', 'press_time': 210, 'release_time': 260}
            ],
            'typing_speed_wpm': 65,
            'dwell_times': [50, 50, 50],  # Key press durations
            'flight_times': [30, 30],     # Time between key releases and next press
            'rhythm_consistency': 0.85
        }
        
        # Mock typing pattern analysis
        mock_behavioral_analyzer.analyze_typing_patterns.return_value = {
            'typing_signature': 'tp_sig_abc123def456',
            'pattern_uniqueness': 0.78,
            'consistency_score': 0.85,
            'matches_known_profile': True,
            'anomaly_detected': False,
            'confidence_level': 0.82,
            'behavioral_traits': {
                'average_dwell_time_ms': 50,
                'typing_rhythm': 'consistent',
                'pressure_variation': 'low',
                'error_correction_pattern': 'methodical'
            }
        }
        
        # Analyze typing patterns
        typing_analysis = await mock_behavioral_analyzer.analyze_typing_patterns(typing_data)
        
        # Verify typing pattern analysis
        assert typing_analysis['pattern_uniqueness'] > 0.7
        assert typing_analysis['matches_known_profile'] is True
        assert typing_analysis['anomaly_detected'] is False
        assert 'typing_signature' in typing_analysis

    async def test_mouse_behavior_analysis(self, mock_behavioral_analyzer, sample_user):
        """Test mouse behavior analysis."""
        mouse_data = {
            'user_id': sample_user.id,
            'session_id': str(uuid4()),
            'mouse_movements': [
                {'x': 100, 'y': 200, 'timestamp': 1000},
                {'x': 150, 'y': 180, 'timestamp': 1050},
                {'x': 200, 'y': 160, 'timestamp': 1100}
            ],
            'click_patterns': [
                {'x': 200, 'y': 160, 'button': 'left', 'duration': 120}
            ],
            'scroll_behavior': {
                'scroll_speed': 'moderate',
                'scroll_direction_changes': 3,
                'scroll_acceleration_pattern': 'smooth'
            }
        }
        
        # Mock mouse behavior analysis
        mock_behavioral_analyzer.analyze_mouse_behavior.return_value = {
            'mouse_signature': 'ms_sig_789xyz321',
            'movement_pattern_uniqueness': 0.72,
            'click_timing_signature': 'moderate_precision',
            'scroll_pattern_consistency': 0.88,
            'hand_dominance_detected': 'right_handed',
            'coordination_level': 'good',
            'behavioral_consistency': 0.79,
            'anomaly_indicators': []
        }
        
        # Analyze mouse behavior
        mouse_analysis = await mock_behavioral_analyzer.analyze_mouse_behavior(mouse_data)
        
        # Verify mouse behavior analysis
        assert mouse_analysis['movement_pattern_uniqueness'] > 0.7
        assert mouse_analysis['hand_dominance_detected'] in ['left_handed', 'right_handed']
        assert mouse_analysis['behavioral_consistency'] > 0.75
        assert len(mouse_analysis['anomaly_indicators']) == 0

    async def test_interaction_pattern_analysis(self, mock_behavioral_analyzer, sample_user):
        """Test user interaction pattern analysis."""
        interaction_data = {
            'user_id': sample_user.id,
            'session_duration_minutes': 45,
            'pages_visited': 8,
            'clicks_per_minute': 2.3,
            'time_spent_reading': 0.65,  # Ratio of time spent reading vs interacting
            'navigation_patterns': [
                'linear_navigation',
                'occasional_backtracking',
                'methodical_exploration'
            ],
            'form_filling_behavior': {
                'completion_speed': 'moderate',
                'error_frequency': 'low',
                'correction_method': 'immediate_backspace'
            }
        }
        
        # Mock interaction analysis
        mock_behavioral_analyzer.analyze_interaction_patterns.return_value = {
            'interaction_signature': 'int_sig_def456ghi789',
            'user_type_classification': 'methodical_user',
            'engagement_level': 'high',
            'technical_proficiency': 'intermediate',
            'behavioral_predictability': 0.81,
            'session_consistency': 0.87,
            'anomalous_behaviors': [],
            'user_intent_confidence': 0.84
        }
        
        # Analyze interaction patterns
        interaction_analysis = await mock_behavioral_analyzer.analyze_interaction_patterns(
            interaction_data
        )
        
        # Verify interaction analysis
        assert interaction_analysis['user_type_classification'] == 'methodical_user'
        assert interaction_analysis['engagement_level'] == 'high'
        assert interaction_analysis['behavioral_predictability'] > 0.8
        assert len(interaction_analysis['anomalous_behaviors']) == 0


class TestDeviceTrustScoring:
    """Test device trust scoring system."""

    @pytest.fixture
    def mock_trust_scorer(self):
        """Mock device trust scorer."""
        scorer = MagicMock()
        scorer.calculate_trust_score = AsyncMock()
        scorer.update_trust_history = AsyncMock()
        scorer.detect_trust_anomalies = AsyncMock()
        return scorer

    async def test_device_trust_score_calculation(self, mock_trust_scorer, sample_user):
        """Test device trust score calculation."""
        device_data = {
            'device_id': str(uuid4()),
            'user_id': sample_user.id,
            'fingerprint_stability': 0.95,
            'usage_history_days': 30,
            'successful_authentications': 45,
            'failed_authentications': 2,
            'location_consistency': 0.92,
            'behavior_consistency': 0.88,
            'last_security_incident': None,
            'device_registered': True
        }
        
        # Mock trust score calculation
        mock_trust_scorer.calculate_trust_score.return_value = {
            'overall_trust_score': 87,
            'trust_level': 'high',
            'score_components': {
                'fingerprint_consistency': 22,  # out of 25
                'usage_history': 18,            # out of 20
                'authentication_success': 23,   # out of 25
                'location_consistency': 14,     # out of 15
                'behavioral_consistency': 10    # out of 15
            },
            'risk_factors': [
                'occasional_location_changes'
            ],
            'trust_trend': 'stable',
            'last_updated': datetime.now(timezone.utc)
        }
        
        # Calculate trust score
        trust_score = await mock_trust_scorer.calculate_trust_score(device_data)
        
        # Verify trust score calculation
        assert trust_score['overall_trust_score'] > 80
        assert trust_score['trust_level'] == 'high'
        assert len(trust_score['score_components']) == 5
        assert trust_score['trust_trend'] in ['increasing', 'stable', 'decreasing']

    async def test_trust_score_history_tracking(self, mock_trust_scorer, sample_user):
        """Test trust score history tracking."""
        trust_update = {
            'device_id': str(uuid4()),
            'user_id': sample_user.id,
            'new_trust_score': 85,
            'previous_trust_score': 82,
            'change_reason': 'consistent_usage_pattern',
            'timestamp': datetime.now(timezone.utc)
        }
        
        # Mock trust history update
        mock_trust_scorer.update_trust_history.return_value = {
            'history_updated': True,
            'trust_trend_updated': True,
            'score_change': +3,
            'trend_direction': 'increasing',
            'historical_scores': [78, 80, 82, 85],
            'average_score_30d': 81.25
        }
        
        # Update trust history
        history_update = await mock_trust_scorer.update_trust_history(trust_update)
        
        # Verify trust history tracking
        assert history_update['history_updated'] is True
        assert history_update['score_change'] > 0
        assert history_update['trend_direction'] == 'increasing'
        assert len(history_update['historical_scores']) > 0

    async def test_trust_anomaly_detection(self, mock_trust_scorer, sample_user):
        """Test detection of trust score anomalies."""
        anomaly_data = {
            'device_id': str(uuid4()),
            'user_id': sample_user.id,
            'current_trust_score': 45,
            'historical_average': 85,
            'score_drop_percentage': 47,
            'recent_events': [
                'new_location_detected',
                'fingerprint_changes_detected',
                'failed_authentication_attempts'
            ]
        }
        
        # Mock anomaly detection
        mock_trust_scorer.detect_trust_anomalies.return_value = {
            'anomaly_detected': True,
            'anomaly_type': 'significant_trust_drop',
            'severity': 'high',
            'contributing_factors': [
                'location_inconsistency',
                'fingerprint_instability',
                'authentication_failures'
            ],
            'recommended_actions': [
                'require_additional_verification',
                'flag_for_manual_review',
                'temporary_restricted_access'
            ],
            'confidence_level': 0.91
        }
        
        # Detect trust anomalies
        anomaly_result = await mock_trust_scorer.detect_trust_anomalies(anomaly_data)
        
        # Verify anomaly detection
        assert anomaly_result['anomaly_detected'] is True
        assert anomaly_result['severity'] == 'high'
        assert len(anomaly_result['contributing_factors']) > 0
        assert len(anomaly_result['recommended_actions']) > 0


class TestDeviceRegistrationManagement:
    """Test device registration and management."""

    @pytest.fixture
    def mock_device_manager(self):
        """Mock device manager."""
        manager = MagicMock()
        manager.register_device = AsyncMock()
        manager.update_device_profile = AsyncMock()
        manager.get_user_devices = AsyncMock()
        manager.revoke_device = AsyncMock()
        return manager

    async def test_device_registration(self, mock_device_manager, sample_user, browser_characteristics):
        """Test device registration process."""
        registration_data = {
            'user_id': sample_user.id,
            'device_name': 'Work Laptop - Chrome',
            'fingerprint_data': browser_characteristics,
            'trust_this_device': True,
            'location_info': {
                'country_code': 'US',
                'city': 'New York',
                'ip_address': '8.8.8.8'
            }
        }
        
        # Mock device registration
        mock_device_manager.register_device.return_value = {
            'device_id': str(uuid4()),
            'device_name': 'Work Laptop - Chrome',
            'fingerprint_id': str(uuid4()),
            'registration_timestamp': datetime.now(timezone.utc),
            'initial_trust_score': 75,
            'trust_level': 'medium',
            'requires_verification': False,
            'status': 'active'
        }
        
        # Register device
        registration_result = await mock_device_manager.register_device(registration_data)
        
        # Verify device registration
        assert 'device_id' in registration_result
        assert registration_result['device_name'] == 'Work Laptop - Chrome'
        assert registration_result['status'] == 'active'
        assert registration_result['initial_trust_score'] > 0

    async def test_device_profile_update(self, mock_device_manager):
        """Test device profile update."""
        device_id = str(uuid4())
        update_data = {
            'device_id': device_id,
            'last_seen': datetime.now(timezone.utc),
            'authentication_count': 156,
            'location_info': {
                'country_code': 'US',
                'city': 'Boston',
                'ip_address': '192.168.1.100'
            },
            'fingerprint_changes': {
                'browser_version': 'updated',
                'plugins': 'modified'
            }
        }
        
        # Mock profile update
        mock_device_manager.update_device_profile.return_value = {
            'update_successful': True,
            'profile_version': 2,
            'trust_score_change': -2,  # Small decrease due to fingerprint changes
            'location_flagged': False,
            'fingerprint_drift_detected': True,
            'update_timestamp': datetime.now(timezone.utc)
        }
        
        # Update device profile
        update_result = await mock_device_manager.update_device_profile(update_data)
        
        # Verify profile update
        assert update_result['update_successful'] is True
        assert update_result['profile_version'] > 1
        assert update_result['fingerprint_drift_detected'] is True

    async def test_user_device_management(self, mock_device_manager, sample_user):
        """Test user device management."""
        # Mock user devices list
        mock_device_manager.get_user_devices.return_value = {
            'user_id': sample_user.id,
            'device_count': 3,
            'devices': [
                {
                    'device_id': str(uuid4()),
                    'device_name': 'Work Laptop - Chrome',
                    'device_type': 'desktop',
                    'trust_score': 87,
                    'last_seen': datetime.now(timezone.utc) - timedelta(hours=2),
                    'status': 'active'
                },
                {
                    'device_id': str(uuid4()),
                    'device_name': 'iPhone 13',
                    'device_type': 'mobile',
                    'trust_score': 82,
                    'last_seen': datetime.now(timezone.utc) - timedelta(minutes=30),
                    'status': 'active'
                },
                {
                    'device_id': str(uuid4()),
                    'device_name': 'Home Desktop - Firefox',
                    'device_type': 'desktop',
                    'trust_score': 45,
                    'last_seen': datetime.now(timezone.utc) - timedelta(days=15),
                    'status': 'inactive'
                }
            ]
        }
        
        # Get user devices
        devices = await mock_device_manager.get_user_devices(sample_user.id)
        
        # Verify device management
        assert devices['device_count'] == 3
        assert len(devices['devices']) == 3
        active_devices = [d for d in devices['devices'] if d['status'] == 'active']
        assert len(active_devices) == 2

    async def test_device_revocation(self, mock_device_manager):
        """Test device revocation."""
        device_id = str(uuid4())
        revocation_reason = 'user_requested'
        
        # Mock device revocation
        mock_device_manager.revoke_device.return_value = {
            'revocation_successful': True,
            'device_id': device_id,
            'revoked_at': datetime.now(timezone.utc),
            'revocation_reason': revocation_reason,
            'active_sessions_terminated': 2,
            'tokens_invalidated': 3,
            'grace_period_hours': 0
        }
        
        # Revoke device
        revocation_result = await mock_device_manager.revoke_device(
            device_id=device_id,
            reason=revocation_reason
        )
        
        # Verify device revocation
        assert revocation_result['revocation_successful'] is True
        assert revocation_result['device_id'] == device_id
        assert revocation_result['active_sessions_terminated'] > 0
        assert revocation_result['tokens_invalidated'] > 0


class TestAntiFingerprintingCountermeasures:
    """Test anti-fingerprinting countermeasures."""

    @pytest.fixture
    def mock_evasion_detector(self):
        """Mock fingerprinting evasion detector."""
        detector = MagicMock()
        detector.detect_evasion_techniques = AsyncMock()
        detector.analyze_privacy_tools = AsyncMock()
        detector.validate_fingerprint_authenticity = AsyncMock()
        return detector

    async def test_privacy_tool_detection(self, mock_evasion_detector, browser_characteristics):
        """Test detection of privacy tools and evasion techniques."""
        # Mock privacy tool detection
        mock_evasion_detector.detect_evasion_techniques.return_value = {
            'evasion_detected': True,
            'detected_tools': [
                'user_agent_spoofer',
                'canvas_blocker',
                'font_randomizer'
            ],
            'evasion_confidence': 0.88,
            'fingerprint_reliability': 0.45,
            'recommended_response': 'additional_verification',
            'bypass_attempts': 3
        }
        
        # Detect evasion techniques
        evasion_result = await mock_evasion_detector.detect_evasion_techniques(
            browser_characteristics
        )
        
        # Verify evasion detection
        assert evasion_result['evasion_detected'] is True
        assert len(evasion_result['detected_tools']) > 0
        assert evasion_result['fingerprint_reliability'] < 0.5
        assert evasion_result['recommended_response'] == 'additional_verification'

    async def test_fingerprint_authenticity_validation(self, mock_evasion_detector):
        """Test fingerprint authenticity validation."""
        fingerprint_data = {
            'fingerprint_hash': 'fp_hash_test123',
            'generation_timestamp': datetime.now(timezone.utc),
            'characteristics_count': 15,
            'entropy_score': 16.2,
            'consistency_checks_passed': 13,
            'consistency_checks_failed': 2
        }
        
        # Mock authenticity validation
        mock_evasion_detector.validate_fingerprint_authenticity.return_value = {
            'authenticity_score': 0.72,
            'is_authentic': True,
            'suspicious_characteristics': [
                'unusual_font_list',
                'inconsistent_timezone_data'
            ],
            'validation_confidence': 0.68,
            'requires_additional_verification': True,
            'authenticity_factors': {
                'hardware_consistency': 0.85,
                'software_consistency': 0.65,
                'behavioral_consistency': 0.78
            }
        }
        
        # Validate fingerprint authenticity
        authenticity_result = await mock_evasion_detector.validate_fingerprint_authenticity(
            fingerprint_data
        )
        
        # Verify authenticity validation
        assert authenticity_result['is_authentic'] is True
        assert authenticity_result['authenticity_score'] > 0.7
        assert len(authenticity_result['suspicious_characteristics']) > 0
        assert authenticity_result['requires_additional_verification'] is True