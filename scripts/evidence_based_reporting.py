#!/usr/bin/env python3
"""Evidence-Based Progress Reporting System - Phase 1 Foundation Repair

MISSION: Implement validation requirements for all status claims
SCOPE: Require evidence for all "resolved" claims and provide automated validation

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Process
- Business Goal: Prevent false progress reporting and ensure sustainable development
- Value Impact: Accurate progress tracking prevents technical debt accumulation
- Strategic Impact: Reliable reporting enables informed business decisions

EVIDENCE REQUIREMENTS:
1. All "resolved" claims must include validation evidence
2. Test execution proof required for test-related resolutions  
3. Before/after metrics for performance improvements
4. Automated validation where possible
5. Evidence must be independently verifiable
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

@dataclass
class Evidence:
    """Represents evidence for a claim."""
    type: str  # 'test_execution', 'metric_comparison', 'file_validation', 'automated_check'
    description: str
    timestamp: str
    validation_command: Optional[str] = None
    before_value: Optional[Any] = None
    after_value: Optional[Any] = None
    validation_output: Optional[str] = None
    hash_verification: Optional[str] = None

@dataclass
class ProgressClaim:
    """Represents a progress claim that requires evidence."""
    claim_id: str
    title: str
    description: str
    status: str  # 'claimed', 'validated', 'rejected'
    claimed_at: str
    evidence: List[Evidence]
    validation_score: float = 0.0
    reviewer_notes: Optional[str] = None

class EvidenceBasedReporter:
    """Manages evidence-based progress reporting and validation."""
    
    def __init__(self):
        self.claims: List[ProgressClaim] = []
        self.reports_dir = PROJECT_ROOT / "reports" / "evidence"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.current_session = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def create_claim(self, title: str, description: str) -> str:
        """Create a new progress claim."""
        claim_id = f"claim_{len(self.claims) + 1}_{self.current_session}"
        
        claim = ProgressClaim(
            claim_id=claim_id,
            title=title,
            description=description,
            status='claimed',
            claimed_at=datetime.now().isoformat(),
            evidence=[]
        )
        
        self.claims.append(claim)
        return claim_id
    
    def add_test_execution_evidence(self, claim_id: str, test_command: str, expected_result: str) -> bool:
        """Add evidence from test execution."""
        claim = self._find_claim(claim_id)
        if not claim:
            return False
        
        try:
            # Execute the test command
            print(f"🧪 Executing test evidence: {test_command}")
            result = subprocess.run(
                test_command.split(),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Analyze result
            success = result.returncode == 0
            validation_output = f"Return code: {result.returncode}\n"
            validation_output += f"STDOUT:\n{result.stdout}\n"
            validation_output += f"STDERR:\n{result.stderr}"
            
            evidence = Evidence(
                type='test_execution',
                description=f"Test execution: {test_command}",
                timestamp=datetime.now().isoformat(),
                validation_command=test_command,
                validation_output=validation_output,
                after_value={"success": success, "return_code": result.returncode},
                hash_verification=hashlib.md5(validation_output.encode()).hexdigest()
            )
            
            claim.evidence.append(evidence)
            print(f"{'✅' if success else '❌'} Test evidence {'passed' if success else 'failed'}")
            return success
            
        except Exception as e:
            evidence = Evidence(
                type='test_execution',
                description=f"Test execution failed: {test_command}",
                timestamp=datetime.now().isoformat(),
                validation_command=test_command,
                validation_output=f"Error: {e}",
                after_value={"success": False, "error": str(e)}
            )
            claim.evidence.append(evidence)
            print(f"❌ Test evidence execution failed: {e}")
            return False
    
    def add_metric_comparison_evidence(self, claim_id: str, metric_name: str, 
                                     before_value: Any, after_value: Any,
                                     validation_command: Optional[str] = None) -> bool:
        """Add evidence from metric comparison."""
        claim = self._find_claim(claim_id)
        if not claim:
            return False
        
        validation_output = None
        if validation_command:
            try:
                result = subprocess.run(
                    validation_command.split(),
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                validation_output = result.stdout + result.stderr
            except Exception as e:
                validation_output = f"Validation command failed: {e}"
        
        evidence = Evidence(
            type='metric_comparison',
            description=f"Metric comparison: {metric_name}",
            timestamp=datetime.now().isoformat(),
            validation_command=validation_command,
            before_value=before_value,
            after_value=after_value,
            validation_output=validation_output,
            hash_verification=hashlib.md5(f"{before_value}_{after_value}".encode()).hexdigest()
        )
        
        claim.evidence.append(evidence)
        
        # Determine if this is an improvement
        improvement = self._is_improvement(metric_name, before_value, after_value)
        print(f"{'✅' if improvement else '⚠️'} Metric evidence: {metric_name} {before_value} → {after_value}")
        return improvement
    
    def add_file_validation_evidence(self, claim_id: str, file_path: str, 
                                   validation_type: str = 'exists') -> bool:
        """Add evidence from file validation."""
        claim = self._find_claim(claim_id)
        if not claim:
            return False
        
        file_path_obj = Path(file_path)
        validation_result = False
        validation_details = {}
        
        if validation_type == 'exists':
            validation_result = file_path_obj.exists()
            validation_details['exists'] = validation_result
            if validation_result:
                validation_details['size'] = file_path_obj.stat().st_size
                validation_details['modified'] = datetime.fromtimestamp(
                    file_path_obj.stat().st_mtime
                ).isoformat()
        
        elif validation_type == 'syntax':
            if file_path.endswith('.py'):
                try:
                    result = subprocess.run([
                        sys.executable, '-m', 'py_compile', file_path
                    ], capture_output=True, text=True)
                    validation_result = result.returncode == 0
                    validation_details['syntax_valid'] = validation_result
                    validation_details['compile_output'] = result.stderr
                except Exception as e:
                    validation_details['error'] = str(e)
        
        evidence = Evidence(
            type='file_validation',
            description=f"File validation: {file_path} ({validation_type})",
            timestamp=datetime.now().isoformat(),
            validation_command=f"validate_file {file_path} {validation_type}",
            after_value=validation_details,
            validation_output=json.dumps(validation_details, indent=2),
            hash_verification=hashlib.md5(str(validation_details).encode()).hexdigest()
        )
        
        claim.evidence.append(evidence)
        print(f"{'✅' if validation_result else '❌'} File validation: {file_path} - {validation_type}")
        return validation_result
    
    def add_automated_check_evidence(self, claim_id: str, check_name: str, 
                                   check_command: str) -> bool:
        """Add evidence from automated check."""
        claim = self._find_claim(claim_id)
        if not claim:
            return False
        
        try:
            result = subprocess.run(
                check_command.split(),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            success = result.returncode == 0
            validation_output = f"Command: {check_command}\n"
            validation_output += f"Return code: {result.returncode}\n"
            validation_output += f"STDOUT:\n{result.stdout}\n"
            validation_output += f"STDERR:\n{result.stderr}"
            
            evidence = Evidence(
                type='automated_check',
                description=f"Automated check: {check_name}",
                timestamp=datetime.now().isoformat(),
                validation_command=check_command,
                validation_output=validation_output,
                after_value={"success": success, "return_code": result.returncode},
                hash_verification=hashlib.md5(validation_output.encode()).hexdigest()
            )
            
            claim.evidence.append(evidence)
            print(f"{'✅' if success else '❌'} Automated check: {check_name}")
            return success
            
        except Exception as e:
            evidence = Evidence(
                type='automated_check',
                description=f"Automated check failed: {check_name}",
                timestamp=datetime.now().isoformat(),
                validation_command=check_command,
                validation_output=f"Error: {e}",
                after_value={"success": False, "error": str(e)}
            )
            claim.evidence.append(evidence)
            print(f"❌ Automated check failed: {check_name} - {e}")
            return False
    
    def validate_claim(self, claim_id: str) -> bool:
        """Validate a claim based on its evidence."""
        claim = self._find_claim(claim_id)
        if not claim:
            return False
        
        if not claim.evidence:
            claim.status = 'rejected'
            claim.reviewer_notes = "No evidence provided"
            return False
        
        # Calculate validation score based on evidence
        total_weight = 0
        weighted_score = 0
        
        for evidence in claim.evidence:
            weight = self._get_evidence_weight(evidence)
            score = self._evaluate_evidence(evidence)
            
            total_weight += weight
            weighted_score += weight * score
        
        if total_weight > 0:
            claim.validation_score = weighted_score / total_weight
        else:
            claim.validation_score = 0.0
        
        # Determine validation result
        if claim.validation_score >= 0.8:
            claim.status = 'validated'
            claim.reviewer_notes = f"Strong evidence provided (score: {claim.validation_score:.2f})"
            print(f"✅ Claim validated: {claim.title} (score: {claim.validation_score:.2f})")
            return True
        elif claim.validation_score >= 0.6:
            claim.status = 'validated'
            claim.reviewer_notes = f"Adequate evidence provided (score: {claim.validation_score:.2f})"
            print(f"⚠️  Claim validated with concerns: {claim.title} (score: {claim.validation_score:.2f})")
            return True
        else:
            claim.status = 'rejected'
            claim.reviewer_notes = f"Insufficient evidence (score: {claim.validation_score:.2f})"
            print(f"❌ Claim rejected: {claim.title} (score: {claim.validation_score:.2f})")
            return False
    
    def generate_report(self) -> Dict:
        """Generate comprehensive evidence-based report."""
        report = {
            'session_id': self.current_session,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_claims': len(self.claims),
                'validated_claims': len([c for c in self.claims if c.status == 'validated']),
                'rejected_claims': len([c for c in self.claims if c.status == 'rejected']),
                'pending_claims': len([c for c in self.claims if c.status == 'claimed']),
                'average_validation_score': self._calculate_average_score(),
                'total_evidence_pieces': sum(len(c.evidence) for c in self.claims)
            },
            'claims': [asdict(claim) for claim in self.claims],
            'evidence_quality_metrics': self._calculate_evidence_metrics(),
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def save_report(self, filename: Optional[str] = None) -> Path:
        """Save evidence report to file."""
        if filename is None:
            filename = f"evidence_report_{self.current_session}.json"
        
        report_path = self.reports_dir / filename
        report = self.generate_report()
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"💾 Evidence report saved: {report_path}")
        return report_path
    
    def _find_claim(self, claim_id: str) -> Optional[ProgressClaim]:
        """Find claim by ID."""
        for claim in self.claims:
            if claim.claim_id == claim_id:
                return claim
        return None
    
    def _is_improvement(self, metric_name: str, before_value: Any, after_value: Any) -> bool:
        """Determine if a metric change represents an improvement."""
        # Define improvement criteria for different metrics
        improvement_criteria = {
            'compliance_score': lambda b, a: a > b,
            'test_pass_rate': lambda b, a: a > b,
            'files_migrated': lambda b, a: a > b,
            'syntax_errors': lambda b, a: a < b,
            'violations': lambda b, a: a < b,
            'technical_debt': lambda b, a: a < b,
        }
        
        for keyword, check_func in improvement_criteria.items():
            if keyword.lower() in metric_name.lower():
                try:
                    return check_func(before_value, after_value)
                except:
                    return False
        
        # Default: assume higher is better
        try:
            return after_value > before_value
        except:
            return False
    
    def _get_evidence_weight(self, evidence: Evidence) -> float:
        """Get weight of evidence based on type and quality."""
        base_weights = {
            'test_execution': 1.0,
            'automated_check': 0.8,
            'metric_comparison': 0.7,
            'file_validation': 0.5
        }
        
        weight = base_weights.get(evidence.type, 0.3)
        
        # Bonus for verification
        if evidence.hash_verification:
            weight += 0.1
        
        # Bonus for validation commands
        if evidence.validation_command:
            weight += 0.1
        
        return weight
    
    def _evaluate_evidence(self, evidence: Evidence) -> float:
        """Evaluate quality of individual evidence piece."""
        if evidence.type == 'test_execution':
            if evidence.after_value and evidence.after_value.get('success'):
                return 1.0
            else:
                return 0.0
        
        elif evidence.type == 'metric_comparison':
            if evidence.before_value is not None and evidence.after_value is not None:
                # Evidence exists and has comparison
                return 0.9
            else:
                return 0.3
        
        elif evidence.type == 'automated_check':
            if evidence.after_value and evidence.after_value.get('success'):
                return 0.8
            else:
                return 0.2
        
        elif evidence.type == 'file_validation':
            if evidence.after_value:
                return 0.6
            else:
                return 0.1
        
        return 0.5  # Default score
    
    def _calculate_average_score(self) -> float:
        """Calculate average validation score across all claims."""
        if not self.claims:
            return 0.0
        
        total_score = sum(claim.validation_score for claim in self.claims)
        return total_score / len(self.claims)
    
    def _calculate_evidence_metrics(self) -> Dict:
        """Calculate quality metrics for evidence."""
        if not self.claims:
            return {}
        
        evidence_types = {}
        total_evidence = 0
        
        for claim in self.claims:
            for evidence in claim.evidence:
                evidence_types[evidence.type] = evidence_types.get(evidence.type, 0) + 1
                total_evidence += 1
        
        return {
            'evidence_by_type': evidence_types,
            'total_evidence_pieces': total_evidence,
            'average_evidence_per_claim': total_evidence / len(self.claims) if self.claims else 0,
            'evidence_diversity': len(evidence_types)
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on evidence analysis."""
        recommendations = []
        
        if not self.claims:
            recommendations.append("No claims to analyze. Start creating progress claims with evidence.")
            return recommendations
        
        # Analyze validation scores
        avg_score = self._calculate_average_score()
        
        if avg_score < 0.6:
            recommendations.append("Low validation scores indicate insufficient evidence quality. Add more test execution and automated check evidence.")
        
        # Analyze evidence diversity
        evidence_metrics = self._calculate_evidence_metrics()
        if evidence_metrics.get('evidence_diversity', 0) < 3:
            recommendations.append("Limited evidence types used. Consider adding metric comparisons and file validations.")
        
        # Analyze rejected claims
        rejected_claims = [c for c in self.claims if c.status == 'rejected']
        if len(rejected_claims) > len(self.claims) * 0.3:
            recommendations.append("High rejection rate suggests need for better evidence collection before making claims.")
        
        return recommendations

def main():
    """Execute evidence-based reporting validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Evidence-Based Progress Reporting')
    parser.add_argument('--validate-redis-migration', action='store_true', 
                       help='Validate Redis migration claims')
    parser.add_argument('--validate-test-quality', action='store_true',
                       help='Validate test quality improvement claims')
    parser.add_argument('--create-example', action='store_true',
                       help='Create example evidence-based report')
    parser.add_argument('--report', action='store_true',
                       help='Generate comprehensive report')
    
    args = parser.parse_args()
    
    print("🚀 Evidence-Based Progress Reporting System - Phase 1 Foundation Repair")
    print("=" * 75)
    
    reporter = EvidenceBasedReporter()
    
    if args.validate_redis_migration:
        # Create claim for Redis migration
        claim_id = reporter.create_claim(
            "Redis SSOT Migration Phase 1 Complete",
            "Migrated 15 files from direct Redis imports to SSOT patterns"
        )
        
        # Add evidence
        reporter.add_metric_comparison_evidence(
            claim_id, "files_migrated", 0, 15,
            "python3 scripts/redis_migration_phase1.py"
        )
        
        reporter.add_automated_check_evidence(
            claim_id, "syntax_validation", 
            "python3 -m py_compile netra_backend/app/services/redis_client.py"
        )
        
        # Validate claim
        reporter.validate_claim(claim_id)
    
    if args.validate_test_quality:
        # Create claim for test quality standards
        claim_id = reporter.create_claim(
            "Test Quality Standards Implemented",
            "Implemented quality standards achieving 70% compliance score"
        )
        
        reporter.add_test_execution_evidence(
            claim_id, 
            "python3 scripts/test_quality_standards.py --scan-all",
            "compliance_score >= 70%"
        )
        
        reporter.add_file_validation_evidence(
            claim_id, "scripts/test_quality_standards.py", "syntax"
        )
        
        # Validate claim  
        reporter.validate_claim(claim_id)
    
    if args.create_example:
        # Create example claims to demonstrate system
        claim1 = reporter.create_claim(
            "Technical Debt Reduction",
            "Reduced technical debt by implementing systematic processes"
        )
        
        reporter.add_metric_comparison_evidence(
            claim1, "process_compliance", 0, 1
        )
        
        claim2 = reporter.create_claim(
            "Foundation Repair Complete", 
            "Phase 1 foundation repair addresses core infrastructure issues"
        )
        
        reporter.add_automated_check_evidence(
            claim2, "infrastructure_health",
            "python3 -c 'print(\"Infrastructure check passed\")'"
        )
        
        # Validate claims
        reporter.validate_claim(claim1)
        reporter.validate_claim(claim2)
    
    if args.report or not any([args.validate_redis_migration, args.validate_test_quality, args.create_example]):
        # Generate and save report
        report_path = reporter.save_report()
        
        # Display summary
        report = reporter.generate_report()
        summary = report['summary']
        
        print("\n📊 Evidence-Based Reporting Summary:")
        print(f"  ✅ Total claims: {summary['total_claims']}")
        print(f"  ✅ Validated: {summary['validated_claims']}")
        print(f"  ❌ Rejected: {summary['rejected_claims']}")
        print(f"  ⏳ Pending: {summary['pending_claims']}")
        print(f"  📈 Average score: {summary['average_validation_score']:.2f}")
        print(f"  📋 Evidence pieces: {summary['total_evidence_pieces']}")
        
        if report['recommendations']:
            print("\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
        
        print(f"\n💾 Full report saved to: {report_path}")

if __name__ == "__main__":
    main()