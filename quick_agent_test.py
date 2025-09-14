#!/usr/bin/env python3
"""
Quick Agent Test Collection Analyzer
Tests a representative sample of agent files to identify patterns of failures.
"""

import subprocess
import sys
from pathlib import Path

def test_collection_sample():
    """Test a representative sample of agent test files."""
    
    # Get sample files from each directory type
    samples = [
        # Unit tests
        "/Users/anthony/Desktop/netra-apex/tests/unit/agents/test_message_router_unit.py",
        "/Users/anthony/Desktop/netra-apex/tests/unit/agents/test_agent_execution_message_validation.py", 
        "/Users/anthony/Desktop/netra-apex/tests/unit/agents/test_import_ssot_validation.py",
        "/Users/anthony/Desktop/netra-apex/tests/unit/agents/supervisor/test_execution_prerequisites.py",
        
        # Integration tests
        "/Users/anthony/Desktop/netra-apex/tests/integration/agents/test_agent_instance_factory_comprehensive_integration.py",
        "/Users/anthony/Desktop/netra-apex/tests/integration/agents/test_agent_execution_ssot_integration.py",
        "/Users/anthony/Desktop/netra-apex/tests/integration/agents/test_chat_orchestrator_workflows_integration.py",
        
        # Netra backend unit tests  
        "/Users/anthony/Desktop/netra-apex/netra_backend/tests/unit/agents/test_tool_dispatcher_core_comprehensive_unit.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/tests/unit/agents/test_agent_execution_core.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/tests/unit/agents/test_supervisor_agent_comprehensive.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/tests/unit/agents/supervisor/test_agent_registry_comprehensive.py"
    ]
    
    print("🔍 Quick Agent Test Collection Analysis")
    print("=" * 50)
    
    success_count = 0
    failure_count = 0
    failures = []
    
    for i, file_path in enumerate(samples, 1):
        file_name = Path(file_path).name
        print(f"[{i:2d}/11] Testing: {file_name[:50]:<50}", end="")
        
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", file_path, "--collect-only", "-q"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                # Count tests collected
                test_lines = [line for line in result.stdout.split('\n') if '::' in line and 'test_' in line]
                test_count = len(test_lines)
                print(f"✅ SUCCESS ({test_count} tests)")
                success_count += 1
            else:
                print(f"❌ FAILED")
                failure_count += 1
                
                # Categorize error
                error = result.stderr
                if "ModuleNotFoundError" in error or "ImportError" in error:
                    category = "missing_module"
                elif "SyntaxError" in error:
                    category = "syntax_error"  
                else:
                    category = "collection_error"
                    
                failures.append((file_name, category, error.split('\n')[0] if error else "Unknown error"))
                
        except subprocess.TimeoutExpired:
            print(f"❌ TIMEOUT")
            failure_count += 1
            failures.append((file_name, "timeout", "Collection timeout after 30s"))
        except Exception as e:
            print(f"❌ EXCEPTION")
            failure_count += 1
            failures.append((file_name, "exception", str(e)))
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {success_count} success, {failure_count} failures")
    
    if failures:
        print(f"\n❌ FAILED FILES:")
        for i, (file_name, category, error) in enumerate(failures, 1):
            print(f"{i:2d}. {category:15s} | {file_name}")
            print(f"    Error: {error[:100]}{'...' if len(error) > 100 else ''}")
            print()
    
    # Now try to get broader statistics
    print(f"\n🔍 BROADER STATISTICS:")
    try:
        # Count total agent files
        result = subprocess.run([
            "find", "/Users/anthony/Desktop/netra-apex", 
            "-path", "*/tests/unit/agents/*test*.py",
            "-o", "-path", "*/tests/integration/agents/*test*.py", 
            "-o", "-path", "*/netra_backend/tests/unit/agents/*test*.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            total_files = len([f for f in result.stdout.strip().split('\n') if f])
            print(f"   Total agent test files found: {total_files}")
            
            success_rate = (success_count / len(samples)) * 100
            print(f"   Sample success rate: {success_rate:.1f}%")
            
            if success_rate < 100:
                estimated_failures = int((total_files * (100 - success_rate)) / 100)
                print(f"   Estimated total failures: ~{estimated_failures} files")
        
    except Exception as e:
        print(f"   Could not get broader statistics: {e}")

if __name__ == "__main__":
    test_collection_sample()