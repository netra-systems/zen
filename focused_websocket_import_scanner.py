#!/usr/bin/env python3
"""
Focused WebSocket Manager Import Scanner - Phase 1 Critical Areas Only

Scans only the most critical areas for WebSocket Manager import variations
to enable immediate Phase 1 remediation without scanning all 91,000 files.

FOCUS AREAS:
1. Backend routes (Golden Path)
2. WebSocket core modules
3. Agent supervisor (Business Logic)
4. Services (Infrastructure)
5. Mission critical tests
"""

import os
import re
import json
from collections import defaultdict, Counter
from pathlib import Path
from datetime import datetime

def scan_websocket_imports():
    """Focused scan of critical WebSocket import areas."""
    
    root_path = Path("/Users/anthony/Desktop/netra-apex")
    
    # Define critical scan areas only
    critical_areas = [
        "netra_backend/app/routes/",
        "netra_backend/app/websocket_core/",
        "netra_backend/app/agents/supervisor/",
        "netra_backend/app/services/",
        "tests/mission_critical/",
        "tests/e2e/websocket_core/",
        "netra_backend/tests/integration/websocket_core/",
    ]
    
    # WebSocket import patterns to find
    websocket_patterns = [
        r'from\s+netra_backend\.app\.websocket_core\.',
        r'import.*WebSocketManager',
        r'import.*UnifiedWebSocketManager',
        r'from.*websocket.*import',
        r'import.*websocket.*manager',
    ]
    
    violations = []
    files_scanned = 0
    
    print("Scanning critical WebSocket import areas...")
    
    for area in critical_areas:
        area_path = root_path / area
        if not area_path.exists():
            print(f"Skipping non-existent area: {area}")
            continue
            
        print(f"Scanning: {area}")
        
        for py_file in area_path.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".backup", ".bak"]):
                continue
                
            files_scanned += 1
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    if not line_stripped or line_stripped.startswith('#'):
                        continue
                    
                    for pattern in websocket_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append({
                                "file": str(py_file.relative_to(root_path)),
                                "line": line_num,
                                "import_statement": line_stripped,
                                "area": area,
                                "priority": "critical" if "routes" in area or "supervisor" in area else 
                                          "high" if "websocket_core" in area or "services" in area else "medium"
                            })
                            break
                            
            except Exception as e:
                print(f"Warning: Could not scan {py_file}: {e}")
    
    # Generate summary
    total_violations = len(violations)
    by_area = Counter(v["area"] for v in violations)
    by_priority = Counter(v["priority"] for v in violations)
    
    print(f"\n" + "="*60)
    print(f"FOCUSED WEBSOCKET IMPORT SCAN RESULTS")
    print(f"="*60)
    print(f"Files scanned: {files_scanned}")
    print(f"Total violations found: {total_violations}")
    
    print(f"\nBy Area:")
    for area, count in by_area.most_common():
        print(f"  {area:35}: {count:3} violations")
    
    print(f"\nBy Priority:")
    for priority, count in by_priority.most_common():
        print(f"  {priority:10}: {count:3} violations")
    
    print(f"\nTop 20 Critical Files:")
    critical_violations = [v for v in violations if v["priority"] == "critical"]
    for i, v in enumerate(critical_violations[:20]):
        print(f"  {i+1:2}. {v['file']}:{v['line']} - {v['import_statement'][:60]}...")
    
    # Save results
    results = {
        "scan_metadata": {
            "timestamp": datetime.now().isoformat(),
            "files_scanned": files_scanned,
            "total_violations": total_violations,
            "focus": "critical_areas_only"
        },
        "violations": violations,
        "summary": {
            "by_area": dict(by_area),
            "by_priority": dict(by_priority),
        }
    }
    
    output_file = f"focused_websocket_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    return violations, files_scanned

if __name__ == "__main__":
    violations, files_scanned = scan_websocket_imports()
    
    print(f"\nPhase 1 Recommendations:")
    print(f"1. Start with {len([v for v in violations if v['priority'] == 'critical'])} critical files")
    print(f"2. Focus on routes/ and supervisor/ areas first (Golden Path protection)")
    print(f"3. Implement compatibility shims before changing core websocket_core/ files") 
    print(f"4. Run mission critical tests after each batch")