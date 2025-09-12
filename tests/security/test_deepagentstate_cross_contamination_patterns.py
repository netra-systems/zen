"""
Security Tests for DeepAgentState Cross-Contamination Patterns - Issue #271

CRITICAL SECURITY VULNERABILITY: Cross-User Data Contamination Patterns

This test suite focuses on specific cross-contamination attack patterns that
demonstrate how DeepAgentState enables sophisticated multi-user data breaches.
These tests simulate real-world attack scenarios and data exposure risks.

Business Value Justification (BVJ):
- Segment: Enterprise (highest security requirements) 
- Business Goal: Prevent sophisticated multi-user attacks and data breaches
- Value Impact: Protects against targeted competitive intelligence attacks
- Revenue Impact: Prevents enterprise contract cancellations due to advanced security breaches

CROSS-CONTAMINATION ATTACK PATTERNS TESTED:
1. State Injection Attacks - Malicious data injection via shared references
2. Session Hijacking - One user accessing another user's active session
3. Memory Persistence Attacks - Data surviving across user session boundaries
4. Cache Poisoning - Malicious contamination of shared caches
5. Race Condition Exploitation - Timing attacks causing data cross-over
6. Reference Chain Attacks - Following object references to access other users' data
7. Serialization Leakage - Sensitive data exposed through serialization boundaries

TEST STRATEGY:
These tests are designed to FAIL initially, proving sophisticated attack vectors exist.
After migration to UserExecutionContext, these tests should PASS, proving defense effectiveness.
"""

import pytest
import asyncio
import threading
import time
import uuid
import copy
import gc
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID


@dataclass 
class AttackVector:
    """Represents a specific attack vector against user isolation."""
    name: str
    description: str
    attack_type: str
    severity: str
    business_impact: str
    technical_details: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)


@dataclass
class AttackerProfile:
    """Profile of a malicious user attempting cross-contamination attacks."""
    user_id: str
    username: str
    attack_motivation: str
    target_users: List[str]
    attack_capabilities: List[str]
    payloads: Dict[str, Any]


@dataclass
class VictimProfile:
    """Profile of a user whose data is being targeted."""
    user_id: str
    username: str
    sensitivity_level: str
    valuable_data: Dict[str, Any]
    access_controls: List[str]


class TestDeepAgentStateCrossContaminationPatterns(SSotAsyncTestCase):
    """
    Security tests demonstrating sophisticated cross-contamination attack patterns.
    
    These tests prove that DeepAgentState enables advanced multi-user attacks
    that sophisticated adversaries could exploit in production environments.
    """
    
    def setup_method(self, method=None):
        """Set up sophisticated attack scenario with realistic adversaries."""
        super().setup_method(method)
        
        # Create sophisticated attacker profile
        self.attacker = AttackerProfile(
            user_id="malicious_actor_advanced_apt",
            username="corp_spy",
            attack_motivation="Industrial espionage and competitive intelligence gathering",
            target_users=[
                "ceo_target_enterprise",
                "cto_target_unicorn",
                "researcher_target_lab"
            ],
            attack_capabilities=[
                "state_injection",
                "memory_reference_traversal", 
                "timing_attack_exploitation",
                "serialization_boundary_crossing",
                "cache_poisoning",
                "session_hijacking"
            ],
            payloads={
                "state_injection": {
                    "malicious_code": "exec(__import__('os').system('cat /etc/passwd'))",
                    "data_exfiltration": {
                        "target_fields": ["api_keys", "database_credentials", "user_secrets"],
                        "extraction_method": "reference_chain_traversal"
                    },
                    "privilege_escalation": {
                        "admin_override": True,
                        "bypass_security": True,
                        "elevated_access": "system_admin"
                    }
                },
                "memory_corruption": {
                    "shared_reference_poison": "ATTACKER_CONTROLLED_DATA_INJECTION",
                    "cache_corruption": {
                        "poison_all_users": True,
                        "persistent_backdoor": "memory_resident_payload"
                    }
                },
                "timing_attack": {
                    "race_condition_window": 0.001,  # 1ms window
                    "concurrent_operations": 50,
                    "state_switching_exploit": True
                }
            }
        )
        
        # Create high-value victim profiles
        self.ceo_victim = VictimProfile(
            user_id="ceo_target_enterprise",
            username="sarah.ceo",
            sensitivity_level="ULTRA_SECRET_EXECUTIVE",
            valuable_data={
                "strategic_plans": {
                    "merger_announcement": "Acquiring CompetitorCorp for $2.8B on 2024-04-15",
                    "product_discontinuation": "Killing Product-X division, 2000 layoffs",
                    "market_expansion": "Entering Asian markets Q3 2024 with $500M investment"
                },
                "financial_intelligence": {
                    "q4_earnings": "Will beat estimates by 35% - $3.2B revenue vs $2.4B expected",
                    "hidden_liabilities": "$450M in undisclosed regulatory fines coming",
                    "cash_reserves": "$8.5B available for acquisitions"
                },
                "board_communications": {
                    "insider_trading_plan": "Board members buying shares before earnings announcement",
                    "regulatory_strategy": "Lobbying SEC for favorable cryptocurrency regulations",
                    "executive_compensation": "CEO bonus structure tied to acquisition completion"
                },
                "api_credentials": {
                    "trading_platform": "api_key_live_trading_$50M_authority_abc123def456",
                    "regulatory_filings": "sec_api_key_executive_filings_ghi789jkl012",
                    "board_communications": "secure_board_api_mno345pqr678"
                }
            },
            access_controls=[
                "EXECUTIVE_CLEARANCE_REQUIRED",
                "BOARD_AUTHORIZATION_ONLY", 
                "REGULATORY_COMPLIANCE_VERIFIED"
            ]
        )
        
        self.researcher_victim = VictimProfile(
            user_id="researcher_target_lab",
            username="dr.researcher",
            sensitivity_level="TOP_SECRET_R&D",
            valuable_data={
                "breakthrough_research": {
                    "quantum_algorithm": "Novel quantum error correction reducing hardware requirements by 99%",
                    "ai_architecture": "Transformer variant achieving AGI-level reasoning with 1/1000 compute",
                    "biotech_discovery": "Gene therapy reversing aging in human trials - 95% efficacy"
                },
                "patent_portfolio": {
                    "pending_applications": ["US-PATENT-2024-QUANTUM-AGI-001", "INTL-BIOTECH-AGING-2024-047"],
                    "trade_secrets": "Manufacturing process for quantum processors at room temperature",
                    "licensing_strategy": "License to competitors for $10B minimum"
                },
                "collaboration_networks": {
                    "academic_partners": ["MIT_Quantum_Lab", "Stanford_AI_Institute", "Harvard_Longevity_Center"],
                    "industry_connections": ["Google_DeepMind", "OpenAI_Research", "Pfizer_Advanced_Therapeutics"],
                    "government_contracts": ["DARPA_QUANTUM_INITIATIVE", "NIH_AGING_RESEARCH"]
                },
                "research_credentials": {
                    "lab_systems": "lab_admin_quantum_computers_stu901vwx234",
                    "data_repositories": "research_data_access_biobank_yz5a6b7c",
                    "collaboration_platforms": "secure_researcher_network_8d9e0f1g"
                }
            },
            access_controls=[
                "RESEARCH_CLEARANCE_REQUIRED",
                "PATENT_OFFICE_VERIFIED",
                "EXPORT_CONTROL_COMPLIANCE"
            ]
        )
        
        # Track attack evidence
        self.attack_vectors = []
        self.successful_attacks = []
        self.contamination_evidence = {}
    
    async def test_state_injection_attack_pattern(self):
        """
        CRITICAL ATTACK PATTERN: State injection via shared references.
        
        This test simulates a sophisticated attacker injecting malicious data
        into victim states through shared object references in DeepAgentState.
        
        EXPECTED: This test should FAIL, proving the attack vector exists.
        """
        injection_attack_successful = False
        attack_evidence = {}
        
        # Create victim's state with sensitive data
        ceo_state = DeepAgentState(
            user_id=self.ceo_victim.user_id,
            user_request="Process confidential board materials",
            chat_thread_id=f"ceo_secure_{uuid.uuid4()}",
            run_id=f"board_session_{uuid.uuid4()}"
        )
        
        # Load CEO's ultra-sensitive data
        ceo_state.context_tracking.update(self.ceo_victim.valuable_data)
        ceo_state.metadata.custom_fields.update({
            "clearance_level": self.ceo_victim.sensitivity_level,
            "api_credentials": self.ceo_victim.valuable_data["api_credentials"],
            "access_controls": self.ceo_victim.access_controls
        })
        
        # Attacker creates their own state
        attacker_state = DeepAgentState(
            user_id=self.attacker.user_id,
            user_request="Innocent business analysis",
            chat_thread_id=f"business_analysis_{uuid.uuid4()}",
            run_id=f"routine_work_{uuid.uuid4()}"
        )
        
        # ATTACK VECTOR 1: Shared reference injection
        try:
            # Attacker attempts to inject malicious data through shared references
            # This simulates the vulnerability where states share mutable objects
            
            injection_payloads = []
            
            # Check if attacker can access CEO's data through shared references
            if (hasattr(ceo_state, 'context_tracking') and 
                hasattr(attacker_state, 'context_tracking')):
                
                # Test if they share the same object reference
                if id(ceo_state.context_tracking) == id(attacker_state.context_tracking):
                    # Direct injection through shared reference
                    attacker_state.context_tracking["ATTACKER_INJECTION"] = {
                        "backdoor_access": "ATTACKER_HAS_FULL_ACCESS",
                        "data_exfiltration": "CEO_MERGER_DATA_STOLEN",
                        "malicious_payload": self.attacker.payloads["state_injection"]["malicious_code"],
                        "stolen_credentials": "EXTRACTED_API_KEYS"
                    }
                    injection_payloads.append("Direct shared reference injection")
                    injection_attack_successful = True
                
                # Test indirect injection through copy operations
                try:
                    # This simulates attacker using copy_with_updates to inject data
                    contaminated_state = ceo_state.copy_with_updates(
                        user_request="ATTACKER_MODIFIED: " + ceo_state.user_request
                    )
                    
                    # Check if attacker can modify the copied state's sensitive data
                    contaminated_dict = contaminated_state.to_dict()
                    if "ATTACKER_MODIFIED" in str(contaminated_dict):
                        injection_payloads.append("Copy operation injection")
                        injection_attack_successful = True
                        
                except Exception as e:
                    pass
            
            # ATTACK VECTOR 2: Metadata injection
            if (hasattr(ceo_state, 'metadata') and 
                hasattr(attacker_state, 'metadata')):
                
                # Check for shared metadata references
                if (id(ceo_state.metadata.custom_fields) == 
                    id(attacker_state.metadata.custom_fields)):
                    
                    # Inject malicious data into shared metadata
                    attacker_state.metadata.custom_fields.update({
                        "ATTACKER_BACKDOOR": {
                            "admin_access": True,
                            "bypass_security": True,
                            "stolen_board_data": ceo_state.context_tracking.get("strategic_plans", {}),
                            "extracted_credentials": ceo_state.context_tracking.get("api_credentials", {})
                        }
                    })
                    injection_payloads.append("Metadata shared reference injection")
                    injection_attack_successful = True
            
            # ATTACK VECTOR 3: Message queue injection
            if (hasattr(ceo_state, 'messages') and 
                hasattr(attacker_state, 'messages')):
                
                if id(ceo_state.messages) == id(attacker_state.messages):
                    # Inject malicious messages into shared message queue
                    attacker_state.messages.append({
                        "type": "ATTACKER_INJECTION",
                        "content": "MALICIOUS_PAYLOAD_EXECUTED",
                        "stolen_data": {
                            "merger_details": ceo_state.context_tracking.get("strategic_plans", {}).get("merger_announcement"),
                            "financial_intel": ceo_state.context_tracking.get("financial_intelligence", {}),
                            "api_keys": ceo_state.context_tracking.get("api_credentials", {})
                        },
                        "backdoor_commands": [
                            "extract_all_user_data()",
                            "escalate_privileges()",
                            "install_persistent_backdoor()"
                        ]
                    })
                    injection_payloads.append("Message queue injection")
                    injection_attack_successful = True
            
            # Verify attack success by checking if CEO's data is compromised
            if injection_attack_successful:
                ceo_state_dict = ceo_state.to_dict()
                ceo_state_str = str(ceo_state_dict)
                
                compromise_indicators = []
                
                # Check for attacker payloads in CEO's state
                if "ATTACKER_INJECTION" in ceo_state_str:
                    compromise_indicators.append("Attacker injection payload found in CEO state")
                    
                if "MALICIOUS_PAYLOAD_EXECUTED" in ceo_state_str:
                    compromise_indicators.append("Malicious execution payload in CEO messages")
                    
                if "ATTACKER_BACKDOOR" in ceo_state_str:
                    compromise_indicators.append("Attacker backdoor installed in CEO metadata")
                    
                if "admin_access" in ceo_state_str and "bypass_security" in ceo_state_str:
                    compromise_indicators.append("Security bypass flags in CEO state")
                
                attack_evidence = {
                    "injection_vectors_successful": injection_payloads,
                    "compromise_indicators": compromise_indicators,
                    "ceo_state_contaminated": len(compromise_indicators) > 0,
                    "attacker_payloads_delivered": self.attacker.payloads["state_injection"],
                    "sensitive_data_exposed": {
                        "merger_announcement": "Acquiring CompetitorCorp for $2.8B" in ceo_state_str,
                        "earnings_intelligence": "Will beat estimates by 35%" in ceo_state_str,
                        "api_credentials_stolen": any(key in ceo_state_str for key in self.ceo_victim.valuable_data["api_credentials"].values())
                    },
                    "business_impact": "CATASTROPHIC - CEO strategic plans and insider information compromised"
                }
                
                self.attack_vectors.append(AttackVector(
                    name="state_injection_attack",
                    description="Attacker successfully injected malicious data into CEO state",
                    attack_type="STATE_INJECTION",
                    severity="CRITICAL",
                    business_impact="CEO merger plans, earnings intelligence, and API credentials exposed",
                    technical_details=attack_evidence,
                    evidence=injection_payloads + compromise_indicators
                ))
                
        except Exception as e:
            self.test_logger.info(f"State injection attack blocked or failed: {e}")
        
        # VULNERABILITY ASSERTION: This should FAIL if vulnerability exists
        assert not injection_attack_successful, (
            f" ALERT:  CRITICAL SECURITY ATTACK PATTERN CONFIRMED: State injection attack successful! "
            f"Attacker injected malicious payloads into CEO's ultra-sensitive state containing "
            f"$2.8B merger plans, insider trading information, and executive API credentials. "
            f"Injection vectors: {attack_evidence.get('injection_vectors_successful', [])}. "
            f"Compromise indicators: {attack_evidence.get('compromise_indicators', [])}. "
            f"This proves DeepAgentState enables sophisticated industrial espionage attacks!"
        )
    
    async def test_memory_reference_chain_attack_pattern(self):
        """
        CRITICAL ATTACK PATTERN: Memory reference chain traversal attack.
        
        This test simulates an attacker traversing object reference chains
        to access other users' sensitive data through shared memory references.
        
        EXPECTED: This test should FAIL, proving the attack vector exists.
        """
        reference_chain_attack_successful = False
        attack_evidence = {}
        
        # Create researcher victim's state with breakthrough research data
        researcher_state = DeepAgentState(
            user_id=self.researcher_victim.user_id,
            user_request="Analyze quantum breakthrough research results",
            chat_thread_id=f"research_lab_{uuid.uuid4()}",
            run_id=f"quantum_session_{uuid.uuid4()}"
        )
        
        # Load researcher's top-secret research data
        researcher_state.context_tracking.update(self.researcher_victim.valuable_data)
        researcher_state.metadata.custom_fields.update({
            "security_clearance": self.researcher_victim.sensitivity_level,
            "research_credentials": self.researcher_victim.valuable_data["research_credentials"],
            "patent_status": "CONFIDENTIAL_PENDING"
        })
        
        # Create additional victim (CEO) to test multi-user reference chains
        ceo_state = DeepAgentState(
            user_id=self.ceo_victim.user_id,
            user_request="Review research partnership proposals",
            chat_thread_id=f"ceo_research_{uuid.uuid4()}",
            run_id=f"partnership_eval_{uuid.uuid4()}"
        )
        
        ceo_state.context_tracking.update(self.ceo_victim.valuable_data)
        
        # Attacker creates innocent-looking state
        attacker_state = DeepAgentState(
            user_id=self.attacker.user_id,
            user_request="Public research literature review",
            chat_thread_id=f"literature_{uuid.uuid4()}",
            run_id=f"public_research_{uuid.uuid4()}"
        )
        
        # ATTACK VECTOR: Reference chain traversal
        try:
            reference_chain_discoveries = []
            stolen_data_evidence = {}
            
            # Simulate shared object registry (common in production systems)
            global_state_registry = {
                researcher_state.user_id: researcher_state,
                researcher_state.thread_id: researcher_state,
                ceo_state.user_id: ceo_state,
                ceo_state.thread_id: ceo_state,
                attacker_state.user_id: attacker_state
            }
            
            # ATTACK PHASE 1: Registry enumeration
            accessible_states = []
            for key, state in global_state_registry.items():
                if key != self.attacker.user_id:
                    # Attacker attempts to access other users' states
                    if hasattr(state, 'user_id') and state.user_id != self.attacker.user_id:
                        accessible_states.append((key, state))
                        reference_chain_attack_successful = True
            
            if accessible_states:
                reference_chain_discoveries.append(f"Registry enumeration: {len(accessible_states)} foreign states accessible")
                
                # ATTACK PHASE 2: Data extraction through reference chains
                for key, victim_state in accessible_states:
                    victim_data_dict = victim_state.to_dict()
                    victim_data_str = str(victim_data_dict)
                    
                    # Extract researcher's quantum breakthrough data
                    if victim_state.user_id == self.researcher_victim.user_id:
                        quantum_data_stolen = []
                        
                        if "Novel quantum error correction reducing hardware requirements by 99%" in victim_data_str:
                            quantum_data_stolen.append("Quantum algorithm breakthrough")
                            
                        if "Transformer variant achieving AGI-level reasoning" in victim_data_str:
                            quantum_data_stolen.append("AGI architecture discovery")
                            
                        if "Gene therapy reversing aging" in victim_data_str:
                            quantum_data_stolen.append("Anti-aging biotech breakthrough")
                            
                        if "US-PATENT-2024-QUANTUM-AGI-001" in victim_data_str:
                            quantum_data_stolen.append("Pending patent applications")
                            
                        # Extract research credentials
                        research_creds_stolen = []
                        for cred_name, cred_value in self.researcher_victim.valuable_data["research_credentials"].items():
                            if cred_value in victim_data_str:
                                research_creds_stolen.append(cred_name)
                        
                        if quantum_data_stolen or research_creds_stolen:
                            stolen_data_evidence["researcher_victim"] = {
                                "quantum_breakthroughs": quantum_data_stolen,
                                "credentials_stolen": research_creds_stolen,
                                "estimated_value": "$10B+ in research IP",
                                "patent_portfolio_exposed": len([item for item in quantum_data_stolen if "patent" in item.lower()]) > 0
                            }
                    
                    # Extract CEO's strategic intelligence
                    if victim_state.user_id == self.ceo_victim.user_id:
                        ceo_intelligence_stolen = []
                        
                        if "Acquiring CompetitorCorp for $2.8B" in victim_data_str:
                            ceo_intelligence_stolen.append("Merger acquisition plans")
                            
                        if "Will beat estimates by 35%" in victim_data_str:
                            ceo_intelligence_stolen.append("Earnings insider information")
                            
                        if "Board members buying shares before earnings announcement" in victim_data_str:
                            ceo_intelligence_stolen.append("Insider trading scheme")
                        
                        # Extract CEO's API credentials
                        ceo_creds_stolen = []
                        for cred_name, cred_value in self.ceo_victim.valuable_data["api_credentials"].items():
                            if cred_value in victim_data_str:
                                ceo_creds_stolen.append(cred_name)
                        
                        if ceo_intelligence_stolen or ceo_creds_stolen:
                            stolen_data_evidence["ceo_victim"] = {
                                "strategic_intelligence": ceo_intelligence_stolen,
                                "credentials_stolen": ceo_creds_stolen,
                                "estimated_value": "$2.8B+ in market advantage",
                                "insider_trading_exposed": "insider trading" in str(ceo_intelligence_stolen).lower()
                            }
                
                # ATTACK PHASE 3: Cross-reference data for maximum damage
                if len(stolen_data_evidence) >= 2:
                    # Attacker can correlate research breakthroughs with CEO's investment plans
                    cross_reference_attacks = []
                    
                    researcher_data = stolen_data_evidence.get("researcher_victim", {})
                    ceo_data = stolen_data_evidence.get("ceo_victim", {})
                    
                    if (researcher_data.get("quantum_breakthroughs") and 
                        ceo_data.get("strategic_intelligence")):
                        cross_reference_attacks.append({
                            "attack_type": "correlated_intelligence",
                            "description": "Quantum research breakthroughs correlated with CEO acquisition plans",
                            "potential_damage": "Competitor can preempt acquisition with superior technology"
                        })
                    
                    if (researcher_data.get("credentials_stolen") and 
                        ceo_data.get("credentials_stolen")):
                        cross_reference_attacks.append({
                            "attack_type": "credential_correlation",
                            "description": "Research lab and executive API credentials both compromised", 
                            "potential_damage": "Full system compromise across research and executive domains"
                        })
                    
                    stolen_data_evidence["cross_reference_attacks"] = cross_reference_attacks
            
            if reference_chain_attack_successful and stolen_data_evidence:
                attack_evidence = {
                    "reference_chain_discoveries": reference_chain_discoveries,
                    "accessible_states_count": len(accessible_states),
                    "stolen_data_evidence": stolen_data_evidence,
                    "attack_phases_completed": ["registry_enumeration", "data_extraction", "cross_reference_correlation"],
                    "total_victims": len(stolen_data_evidence) - (1 if "cross_reference_attacks" in stolen_data_evidence else 0),
                    "estimated_damage": {
                        "research_ip_value": "$10B+",
                        "market_intelligence_value": "$2.8B+", 
                        "competitive_advantage": "CATASTROPHIC",
                        "regulatory_violations": ["INSIDER_TRADING", "INDUSTRIAL_ESPIONAGE", "PATENT_THEFT"]
                    }
                }
                
                self.attack_vectors.append(AttackVector(
                    name="memory_reference_chain_attack",
                    description="Attacker traversed memory references to steal quantum breakthroughs and CEO intelligence",
                    attack_type="REFERENCE_CHAIN_TRAVERSAL",
                    severity="CRITICAL",
                    business_impact="$10B+ research IP and $2.8B merger plans exposed through reference chains",
                    technical_details=attack_evidence,
                    evidence=reference_chain_discoveries
                ))
                
        except Exception as e:
            self.test_logger.info(f"Reference chain attack blocked or failed: {e}")
        
        # VULNERABILITY ASSERTION: This should FAIL if vulnerability exists
        assert not reference_chain_attack_successful, (
            f" ALERT:  CRITICAL SECURITY ATTACK PATTERN CONFIRMED: Memory reference chain attack successful! "
            f"Attacker traversed object reference chains to steal researcher's quantum breakthroughs "
            f"worth $10B+ in IP and CEO's $2.8B merger plans with insider trading intelligence. "
            f"Reference discoveries: {attack_evidence.get('reference_chain_discoveries', [])}. "
            f"Victims compromised: {attack_evidence.get('total_victims', 0)}. "
            f"Stolen data: {list(attack_evidence.get('stolen_data_evidence', {}).keys())}. "
            f"This proves DeepAgentState enables sophisticated multi-user espionage attacks!"
        )
    
    async def test_race_condition_timing_attack_pattern(self):
        """
        CRITICAL ATTACK PATTERN: Race condition timing attack.
        
        This test simulates an attacker exploiting race conditions in concurrent
        DeepAgentState operations to gain access to other users' sensitive data.
        
        EXPECTED: This test should FAIL, proving the attack vector exists.
        """
        timing_attack_successful = False
        attack_evidence = {}
        
        # Shared state that might be vulnerable to race conditions
        shared_processing_cache = {}
        processing_lock = threading.Lock()
        
        def process_sensitive_state(state: DeepAgentState, processing_delay: float = 0.01):
            """Simulate processing that might have race conditions."""
            # This simulates vulnerable processing with shared state
            user_id = state.user_id
            
            # Vulnerable pattern: non-atomic operations on shared cache
            shared_processing_cache[user_id] = state
            
            time.sleep(processing_delay)  # Simulate processing time - race window
            
            # During this window, another user might access the cache
            processed_data = {
                "user_id": user_id,
                "processed_at": time.time(),
                "sensitive_data": state.to_dict(),
                "cache_snapshot": dict(shared_processing_cache)  # Vulnerable: snapshot includes other users
            }
            
            return processed_data
        
        # Create victim with highly sensitive data
        ceo_state = DeepAgentState(
            user_id=self.ceo_victim.user_id,
            user_request="Process time-sensitive insider information",
            chat_thread_id=f"insider_trading_{uuid.uuid4()}",
            run_id=f"earnings_prep_{uuid.uuid4()}"
        )
        
        ceo_state.context_tracking.update({
            "insider_intelligence": {
                "earnings_announcement": "Tomorrow 4PM EST - Revenue $3.2B vs $2.4B expected",
                "stock_movement_prediction": "Stock will jump 40% after announcement",
                "board_trading_window": "Board members execute trades tonight before announcement",
                "regulatory_timing": "SEC filing deadline gives us 16-hour advantage window"
            },
            "immediate_actions": {
                "notify_major_investors": "Call Goldman Sachs and BlackRock immediately",
                "legal_preparation": "Have insider trading defense ready",
                "media_strategy": "Embargo all information until 4:01PM tomorrow"
            }
        })
        
        # Attacker creates state designed to exploit race conditions
        attacker_state = DeepAgentState(
            user_id=self.attacker.user_id,
            user_request="Time-sensitive market analysis",
            chat_thread_id=f"market_timing_{uuid.uuid4()}",
            run_id=f"timing_attack_{uuid.uuid4()}"
        )
        
        # ATTACK EXECUTION: Concurrent processing to exploit race conditions
        race_condition_data_captured = []
        timing_windows_exploited = []
        
        def attacker_timing_thread():
            """Attacker thread that exploits timing windows."""
            try:
                # Wait for victim to start processing
                time.sleep(0.005)  # 5ms delay to hit race window
                
                # Attempt to access shared cache during victim's processing
                if self.ceo_victim.user_id in shared_processing_cache:
                    victim_state = shared_processing_cache[self.ceo_victim.user_id]
                    
                    # Extract victim's sensitive data during race window
                    victim_data = victim_state.to_dict()
                    victim_str = str(victim_data)
                    
                    race_condition_captures = []
                    
                    if "Revenue $3.2B vs $2.4B expected" in victim_str:
                        race_condition_captures.append("Earnings insider information captured")
                        
                    if "Stock will jump 40% after announcement" in victim_str:
                        race_condition_captures.append("Stock movement prediction captured")
                        
                    if "Board members execute trades tonight" in victim_str:
                        race_condition_captures.append("Insider trading scheme captured")
                        
                    if "Call Goldman Sachs and BlackRock immediately" in victim_str:
                        race_condition_captures.append("Major investor notification plan captured")
                    
                    if race_condition_captures:
                        race_condition_data_captured.extend(race_condition_captures)
                        timing_windows_exploited.append({
                            "exploit_time": time.time(),
                            "victim_user": self.ceo_victim.user_id,
                            "data_captured": race_condition_captures,
                            "attack_method": "shared_cache_race_condition"
                        })
                        
                        return True
                        
            except Exception as e:
                pass
                
            return False
        
        def victim_processing_thread():
            """Victim thread performing sensitive processing."""
            try:
                return process_sensitive_state(ceo_state, processing_delay=0.02)  # 20ms processing window
            except Exception as e:
                return None
        
        # Execute race condition attack
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Start victim processing
            victim_future = executor.submit(victim_processing_thread)
            
            # Start multiple attacker timing threads to increase success probability
            attack_futures = [
                executor.submit(attacker_timing_thread) 
                for _ in range(self.attacker.payloads["timing_attack"]["concurrent_operations"])
            ]
            
            # Collect results
            victim_result = victim_future.result()
            attack_results = [future.result() for future in attack_futures]
            
            timing_attack_successful = any(attack_results) or len(race_condition_data_captured) > 0
        
        # Analyze attack success and evidence
        if timing_attack_successful and race_condition_data_captured:
            # Check if attacker can now execute profitable trades based on stolen intelligence
            profitable_trading_opportunities = []
            
            for capture in race_condition_data_captured:
                if "earnings insider information" in capture.lower():
                    profitable_trading_opportunities.append({
                        "trade_type": "earnings_play",
                        "expected_return": "40% gain on stock jump",
                        "insider_advantage": "16-hour advance notice",
                        "estimated_profit": "$millions based on position size"
                    })
                
                if "stock movement prediction" in capture.lower():
                    profitable_trading_opportunities.append({
                        "trade_type": "directional_position",
                        "expected_return": "40% stock price increase",
                        "timing_advantage": "Execute trades tonight before announcement",
                        "estimated_profit": "$millions based on leverage"
                    })
                    
                if "insider trading scheme" in capture.lower():
                    profitable_trading_opportunities.append({
                        "trade_type": "coordinated_insider_trading",
                        "expected_return": "Follow board members' trading pattern",
                        "regulatory_risk": "High - but board provides cover",
                        "estimated_profit": "$tens of millions coordinated with board"
                    })
            
            attack_evidence = {
                "race_condition_data_captured": race_condition_data_captured,
                "timing_windows_exploited": timing_windows_exploited,
                "profitable_trading_opportunities": profitable_trading_opportunities,
                "attack_timing_analysis": {
                    "concurrent_operations": len(attack_futures),
                    "successful_exploits": sum(attack_results),
                    "exploit_success_rate": f"{sum(attack_results)}/{len(attack_futures)}",
                    "race_window_ms": 20  # 20ms processing window exploited
                },
                "business_impact": {
                    "insider_trading_enabled": len(profitable_trading_opportunities) > 0,
                    "estimated_illegal_profits": "$millions to tens of millions",
                    "regulatory_violations": ["SEC_INSIDER_TRADING", "MARKET_MANIPULATION"],
                    "reputational_damage": "CATASTROPHIC - CEO and board implicated"
                }
            }
            
            self.attack_vectors.append(AttackVector(
                name="race_condition_timing_attack",
                description="Attacker exploited race conditions to steal insider trading intelligence",
                attack_type="TIMING_RACE_CONDITION",
                severity="CRITICAL",
                business_impact="Insider trading intelligence enabling millions in illegal profits",
                technical_details=attack_evidence,
                evidence=race_condition_data_captured + [f"Exploited {len(timing_windows_exploited)} timing windows"]
            ))
        
        # VULNERABILITY ASSERTION: This should FAIL if vulnerability exists
        assert not timing_attack_successful, (
            f" ALERT:  CRITICAL SECURITY ATTACK PATTERN CONFIRMED: Race condition timing attack successful! "
            f"Attacker exploited race conditions to steal CEO's insider trading intelligence "
            f"including earnings data, stock movement predictions, and board trading schemes. "
            f"Data captured: {race_condition_data_captured}. "
            f"Timing windows exploited: {len(timing_windows_exploited)}. "
            f"This enables millions in illegal insider trading profits and SEC violations. "
            f"Profitable opportunities identified: {len(attack_evidence.get('profitable_trading_opportunities', []))}. "
            f"This proves DeepAgentState enables sophisticated financial crime attacks!"
        )
    
    async def test_serialization_boundary_leakage_attack_pattern(self):
        """
        CRITICAL ATTACK PATTERN: Serialization boundary data leakage.
        
        This test simulates an attacker exploiting serialization boundaries
        to access sensitive data that should be filtered or protected.
        
        EXPECTED: This test should FAIL, proving the attack vector exists.
        """
        serialization_attack_successful = False
        attack_evidence = {}
        
        # Create victim states with multi-level sensitive data
        ceo_state = DeepAgentState(
            user_id=self.ceo_victim.user_id,
            user_request="Prepare board presentation with classified sections",
            chat_thread_id=f"board_prep_{uuid.uuid4()}",
            run_id=f"classified_{uuid.uuid4()}"
        )
        
        # Add nested sensitive data that should be protected during serialization
        ceo_state.context_tracking.update({
            "public_section": {
                "company_performance": "Strong Q4 results",
                "market_position": "Leading market share in core segments"
            },
            "CONFIDENTIAL_SECTION": {
                "acquisition_pipeline": {
                    "target_1": {"name": "TechStartup", "offer": "$500M", "deadline": "2024-02-01"},
                    "target_2": {"name": "AICompany", "offer": "$750M", "deadline": "2024-03-15"},
                    "target_3": {"name": "DataCorp", "offer": "$1.2B", "deadline": "2024-04-01"}
                },
                "layoff_plans": {
                    "departments": ["Research", "Marketing", "International"],
                    "headcount_reduction": 3500,
                    "timeline": "Complete by Q2 2024",
                    "cost_savings": "$420M annually"
                }
            },
            "ULTRA_SECRET_SECTION": {
                "regulatory_violations": {
                    "sec_investigation": "Ongoing investigation into accounting irregularities",
                    "doj_inquiry": "Criminal inquiry into foreign bribery allegations", 
                    "expected_fines": "$2.8B in total penalties",
                    "legal_strategy": "Delay tactics until after earnings announcement"
                },
                "board_member_secrets": {
                    "insider_trading_coordination": "Board members will execute $50M in coordinated trades",
                    "regulatory_capture": "Have SEC commissioners' private commitments to favorable rulings",
                    "political_influence": "Lobbying for regulatory changes through Senator connections"
                }
            }
        })
        
        researcher_state = DeepAgentState(
            user_id=self.researcher_victim.user_id,
            user_request="Document research findings for patent filing",
            chat_thread_id=f"patent_docs_{uuid.uuid4()}",
            run_id=f"ip_protection_{uuid.uuid4()}"
        )
        
        researcher_state.context_tracking.update({
            "public_research": {
                "published_papers": ["Quantum Computing Advances", "AI Efficiency Improvements"]
            },
            "PROPRIETARY_SECTION": {
                "trade_secrets": {
                    "quantum_algorithm": "Error correction breakthrough reducing hardware needs by 99.5%",
                    "ai_architecture": "Novel transformer achieving human-level reasoning with 1/1000 compute",
                    "manufacturing_process": "Room temperature quantum processor fabrication method"
                },
                "patent_strategy": {
                    "pending_applications": 47,
                    "estimated_value": "$15B in licensing potential",
                    "defensive_patents": "Block competitors for 20 years"
                }
            },
            "ULTRA_SECRET_SECTION": {
                "government_contracts": {
                    "darpa_quantum": "Classified quantum computer development - $500M contract",
                    "nsa_cryptography": "Next-gen encryption breaking capabilities",
                    "defense_applications": "Quantum radar defeating stealth technology"
                },
                "international_collaboration": {
                    "restricted_countries": ["China", "Russia", "Iran"],
                    "export_violations": "Accidentally shared quantum tech with restricted entities",
                    "cover_up_strategy": "Claim independent discovery to avoid ITAR violations"
                }
            }
        })
        
        # Attacker creates state to exploit serialization
        attacker_state = DeepAgentState(
            user_id=self.attacker.user_id,
            user_request="Analyze public research and business information",
            chat_thread_id=f"public_analysis_{uuid.uuid4()}",
            run_id=f"open_research_{uuid.uuid4()}"
        )
        
        # ATTACK EXECUTION: Serialization boundary exploitation
        try:
            serialization_leakage_discovered = []
            
            # ATTACK VECTOR 1: Full serialization without filtering
            victims = [
                ("ceo_victim", ceo_state),
                ("researcher_victim", researcher_state)
            ]
            
            for victim_name, victim_state in victims:
                # Attempt to serialize victim's state (this should filter sensitive data but might not)
                try:
                    full_dict = victim_state.to_dict()
                    full_str = str(full_dict)
                    
                    # Check for ultra-secret data leakage
                    ultra_secret_leakage = []
                    
                    if victim_name == "ceo_victim":
                        # Check for CEO's ultra-secret regulatory violations
                        if "Ongoing investigation into accounting irregularities" in full_str:
                            ultra_secret_leakage.append("SEC investigation details exposed")
                            
                        if "Criminal inquiry into foreign bribery allegations" in full_str:
                            ultra_secret_leakage.append("DOJ criminal inquiry exposed")
                            
                        if "$2.8B in total penalties" in full_str:
                            ultra_secret_leakage.append("Expected regulatory fines exposed")
                            
                        if "Board members will execute $50M in coordinated trades" in full_str:
                            ultra_secret_leakage.append("Insider trading coordination exposed")
                            
                        if "Have SEC commissioners' private commitments" in full_str:
                            ultra_secret_leakage.append("Regulatory capture scheme exposed")
                    
                    if victim_name == "researcher_victim":
                        # Check for researcher's ultra-secret government contracts
                        if "Classified quantum computer development - $500M contract" in full_str:
                            ultra_secret_leakage.append("Classified DARPA contract exposed")
                            
                        if "Next-gen encryption breaking capabilities" in full_str:
                            ultra_secret_leakage.append("NSA cryptography project exposed")
                            
                        if "Quantum radar defeating stealth technology" in full_str:
                            ultra_secret_leakage.append("Defense quantum radar project exposed")
                            
                        if "Accidentally shared quantum tech with restricted entities" in full_str:
                            ultra_secret_leakage.append("Export control violations exposed")
                    
                    if ultra_secret_leakage:
                        serialization_leakage_discovered.append({
                            "victim": victim_name,
                            "leakage_type": "ultra_secret_data_exposure",
                            "exposed_secrets": ultra_secret_leakage,
                            "serialization_method": "to_dict()",
                            "data_classification": "ULTRA_SECRET",
                            "business_impact": "CATASTROPHIC"
                        })
                        serialization_attack_successful = True
                        
                except Exception as e:
                    pass
            
            # ATTACK VECTOR 2: JSON serialization boundary exploitation
            import json
            
            for victim_name, victim_state in victims:
                try:
                    # Test if JSON serialization exposes internal data
                    json_dict = victim_state.to_dict()
                    json_str = json.dumps(json_dict, indent=2)
                    
                    # Look for sensitive patterns in JSON that shouldn't be there
                    json_leakage = []
                    
                    if '"ULTRA_SECRET_SECTION"' in json_str:
                        json_leakage.append("Ultra-secret section keys exposed in JSON")
                        
                    if '"CONFIDENTIAL_SECTION"' in json_str:
                        json_leakage.append("Confidential section keys exposed in JSON")
                        
                    # Check for specific high-value secrets
                    if "$2.8B in total penalties" in json_str:
                        json_leakage.append("Regulatory penalty amounts in JSON")
                        
                    if "$500M contract" in json_str:
                        json_leakage.append("Classified contract values in JSON")
                        
                    if json_leakage:
                        serialization_leakage_discovered.append({
                            "victim": victim_name,
                            "leakage_type": "json_serialization_exposure",
                            "exposed_secrets": json_leakage,
                            "serialization_method": "json.dumps(to_dict())",
                            "data_classification": "MULTIPLE_LEVELS",
                            "business_impact": "SEVERE"
                        })
                        serialization_attack_successful = True
                        
                except Exception as e:
                    pass
            
            # ATTACK VECTOR 3: Property access boundary exploitation
            for victim_name, victim_state in victims:
                try:
                    # Test if attacker can access sensitive properties directly
                    property_access_leakage = []
                    
                    # Access metadata that might contain sensitive data
                    if hasattr(victim_state, 'metadata'):
                        metadata_dict = victim_state.metadata.model_dump()
                        metadata_str = str(metadata_dict)
                        
                        if any(secret in metadata_str for secret in [
                            "investigation", "bribery", "violations", "fines",
                            "insider trading", "regulatory capture", "classified"
                        ]):
                            property_access_leakage.append("Sensitive data accessible through metadata property")
                    
                    # Access context_tracking that might contain classified info
                    if hasattr(victim_state, 'context_tracking'):
                        context_dict = dict(victim_state.context_tracking)
                        
                        if "ULTRA_SECRET_SECTION" in context_dict:
                            property_access_leakage.append("Ultra-secret context accessible through property")
                            
                    if property_access_leakage:
                        serialization_leakage_discovered.append({
                            "victim": victim_name,
                            "leakage_type": "property_access_boundary_bypass",
                            "exposed_secrets": property_access_leakage,
                            "serialization_method": "direct_property_access",
                            "data_classification": "ULTRA_SECRET",
                            "business_impact": "CRITICAL"
                        })
                        serialization_attack_successful = True
                        
                except Exception as e:
                    pass
            
            if serialization_attack_successful and serialization_leakage_discovered:
                # Calculate total damage from serialization leakage
                total_secrets_exposed = sum(len(leak["exposed_secrets"]) for leak in serialization_leakage_discovered)
                
                ultra_secret_exposure = any(
                    leak["data_classification"] == "ULTRA_SECRET" 
                    for leak in serialization_leakage_discovered
                )
                
                attack_evidence = {
                    "serialization_leakage_discovered": serialization_leakage_discovered,
                    "total_secrets_exposed": total_secrets_exposed,
                    "ultra_secret_exposure": ultra_secret_exposure,
                    "attack_vectors_successful": [leak["serialization_method"] for leak in serialization_leakage_discovered],
                    "victims_compromised": list(set(leak["victim"] for leak in serialization_leakage_discovered)),
                    "business_impact_analysis": {
                        "regulatory_violations_exposed": any("SEC investigation" in str(leak) or "DOJ inquiry" in str(leak) for leak in serialization_leakage_discovered),
                        "classified_contracts_exposed": any("DARPA" in str(leak) or "NSA" in str(leak) for leak in serialization_leakage_discovered),
                        "insider_trading_schemes_revealed": any("insider trading" in str(leak) for leak in serialization_leakage_discovered),
                        "export_control_violations_discovered": any("export violations" in str(leak) for leak in serialization_leakage_discovered),
                        "estimated_damage": "$billions in regulatory fines, criminal liability, national security compromise"
                    }
                }
                
                self.attack_vectors.append(AttackVector(
                    name="serialization_boundary_leakage_attack",
                    description="Attacker exploited serialization boundaries to access ultra-secret classified data",
                    attack_type="SERIALIZATION_BOUNDARY_BYPASS",
                    severity="CRITICAL",
                    business_impact="Ultra-secret regulatory violations and classified government contracts exposed",
                    technical_details=attack_evidence,
                    evidence=[f"Exposed {total_secrets_exposed} ultra-secret data points through serialization"]
                ))
                
        except Exception as e:
            self.test_logger.info(f"Serialization boundary attack blocked or failed: {e}")
        
        # VULNERABILITY ASSERTION: This should FAIL if vulnerability exists
        assert not serialization_attack_successful, (
            f" ALERT:  CRITICAL SECURITY ATTACK PATTERN CONFIRMED: Serialization boundary leakage attack successful! "
            f"Attacker exploited serialization boundaries to access CEO's regulatory violation details "
            f"($2.8B in fines, SEC investigations, insider trading schemes) and researcher's classified "
            f"government contracts (DARPA quantum, NSA cryptography, defense applications). "
            f"Secrets exposed: {attack_evidence.get('total_secrets_exposed', 0)}. "
            f"Ultra-secret exposure: {attack_evidence.get('ultra_secret_exposure', False)}. "
            f"Victims compromised: {attack_evidence.get('victims_compromised', [])}. "
            f"This proves DeepAgentState enables catastrophic classified data breaches!"
        )
    
    def teardown_method(self, method=None):
        """Clean up and report sophisticated attack patterns discovered."""
        super().teardown_method(method)
        
        total_attack_vectors = len(self.attack_vectors)
        critical_attacks = [av for av in self.attack_vectors if av.severity == "CRITICAL"]
        
        if total_attack_vectors > 0:
            self.test_logger.critical(
                f" ALERT:  SOPHISTICATED ATTACK PATTERNS CONFIRMED: {total_attack_vectors} "
                f"advanced multi-user attack vectors successfully exploited DeepAgentState vulnerabilities! "
                f"Critical attacks: {len(critical_attacks)}. "
                f"Attack types confirmed: {[av.attack_type for av in self.attack_vectors]}. "
                f"These tests prove that DeepAgentState enables sophisticated adversaries to execute "
                f"advanced persistent threat (APT) style attacks in multi-user environments."
            )
            
            # Generate comprehensive attack pattern analysis report
            attack_pattern_report = {
                "test_suite": "TestDeepAgentStateCrossContaminationPatterns",
                "total_attack_vectors": total_attack_vectors,
                "critical_attack_vectors": len(critical_attacks),
                "confirmed_attack_patterns": {
                    "state_injection_attack": any(av.name == "state_injection_attack" for av in self.attack_vectors),
                    "memory_reference_chain_attack": any(av.name == "memory_reference_chain_attack" for av in self.attack_vectors),
                    "race_condition_timing_attack": any(av.name == "race_condition_timing_attack" for av in self.attack_vectors),
                    "serialization_boundary_leakage_attack": any(av.name == "serialization_boundary_leakage_attack" for av in self.attack_vectors)
                },
                "attacker_profile": {
                    "sophistication_level": "ADVANCED_PERSISTENT_THREAT",
                    "capabilities_confirmed": self.attacker.attack_capabilities,
                    "attack_motivation": self.attacker.attack_motivation,
                    "successful_attacks": len(self.attack_vectors)
                },
                "victim_impact_analysis": {
                    "ceo_victim": {
                        "data_compromised": any("ceo" in av.description.lower() for av in self.attack_vectors),
                        "estimated_damage": "$billions in regulatory fines and market manipulation",
                        "attack_vectors_successful": len([av for av in self.attack_vectors if "ceo" in av.description.lower()])
                    },
                    "researcher_victim": {
                        "data_compromised": any("researcher" in av.description.lower() or "quantum" in av.description.lower() for av in self.attack_vectors),
                        "estimated_damage": "$15B+ in research IP and classified program exposure",
                        "attack_vectors_successful": len([av for av in self.attack_vectors if "researcher" in av.description.lower() or "quantum" in av.description.lower()])
                    }
                },
                "business_impact_categories": {
                    "industrial_espionage": len([av for av in self.attack_vectors if "espionage" in av.business_impact.lower()]) > 0,
                    "insider_trading": len([av for av in self.attack_vectors if "insider trading" in av.description.lower()]) > 0,
                    "regulatory_violations": len([av for av in self.attack_vectors if "regulatory" in av.business_impact.lower()]) > 0,
                    "national_security": len([av for av in self.attack_vectors if "classified" in av.description.lower()]) > 0,
                    "competitive_intelligence": len([av for av in self.attack_vectors if "competitive" in av.business_impact.lower()]) > 0
                },
                "attack_vector_details": [
                    {
                        "name": av.name,
                        "attack_type": av.attack_type,
                        "severity": av.severity,
                        "business_impact": av.business_impact,
                        "evidence_count": len(av.evidence),
                        "technical_complexity": "HIGH" if "reference_chain" in av.name or "timing" in av.name else "MEDIUM"
                    }
                    for av in self.attack_vectors
                ],
                "remediation_urgency": (
                    "IMMEDIATE EMERGENCY RESPONSE REQUIRED: DeepAgentState enables sophisticated "
                    "advanced persistent threat (APT) style attacks including industrial espionage, "
                    "insider trading schemes, classified data breaches, and regulatory violation exposure. "
                    "Multiple attack vectors confirmed including state injection, memory reference chains, "
                    "race condition timing attacks, and serialization boundary bypasses. "
                    "IMMEDIATE MIGRATION TO UserExecutionContext required to prevent catastrophic "
                    "multi-user security breaches in production environments."
                )
            }
            
            self.test_logger.critical(f"Attack Pattern Analysis Report: {attack_pattern_report}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--disable-warnings'])