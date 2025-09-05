---
allowed-tools: ["Bash", "Read"]
description: "Check CLAUDE.md compliance requirements and system status"
---

# CLAUDE.md Architecture Compliance Check

## 🚨 MISSION CRITICAL VALUES CHECK
!echo "🚨 Checking MISSION_CRITICAL_NAMED_VALUES_INDEX..."
!python -c "import xml.etree.ElementTree as ET; tree = ET.parse('SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml'); print('✅ Critical values index accessible')" || echo "❌ CRITICAL: Cannot access values index!"

## 📋 Core Architecture Requirements

!echo "🏗️ 1. SINGLE SOURCE OF TRUTH (SSOT) Check..."
!python scripts/check_architecture_compliance.py | grep -i "ssot\|duplication" || echo "Running full compliance..."

!echo "📦 2. NO RELATIVE IMPORTS Check..."
!grep -r "from \.\." --include="*.py" netra_backend auth_service frontend 2>/dev/null | head -5 || echo "✅ No relative imports found"

!echo "🔤 3. STRING LITERALS Index Check..."
!python scripts/scan_string_literals.py
!python scripts/query_string_literals.py validate "POSTGRES_HOST" || echo "Sample validation"

!echo "📁 4. FOLDER STRUCTURE Rules Check..."
!echo "  Service-specific tests:"
!ls -d netra_backend/tests auth_service/tests 2>/dev/null || echo "  ⚠️ Service test directories"
!echo "  E2E tests location:"
!ls -d tests/e2e 2>/dev/null || echo "  ⚠️ E2E test directory"

## 🧪 Testing Standards (NO MOCKS)

!echo "🚫 5. NO MOCKS Policy Check..."
!grep -r "Mock\|MagicMock\|patch" --include="*.py" tests/ 2>/dev/null | head -3 || echo "✅ No mock usage detected"

!echo "🐳 6. Docker Services Status..."
!docker compose ps --services 2>/dev/null | head -5 || echo "⚠️ Docker not running"

## 🔌 WebSocket Mission Critical Events

!echo "📡 7. WebSocket Event Requirements..."
!grep -l "agent_started\|agent_thinking\|tool_executing" netra_backend/app/agents/*.py 2>/dev/null | wc -l | xargs -I {} echo "  Found {} files with WebSocket events"

## 🎯 Business Value Checks

!echo "💬 8. Chat UI/UX Value Delivery..."
!test -f netra_backend/app/websocket/manager.py && echo "✅ WebSocket manager exists" || echo "❌ Missing WebSocket manager"

!echo "🔐 9. Environment Management..."
!grep -l "IsolatedEnvironment" netra_backend/**/*.py 2>/dev/null | wc -l | xargs -I {} echo "  {} files using IsolatedEnvironment"

## 📊 Mega Class Exceptions

!echo "📏 10. Mega Class Size Check..."
!python -c "
import os
for root, dirs, files in os.walk('netra_backend'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as file:
                lines = len(file.readlines())
                if lines > 750:
                    print(f'  ⚠️ {path}: {lines} lines')
" 2>/dev/null | head -5 || echo "  Checking Python file sizes..."

## 🔄 Git Standards

!echo "📝 11. Atomic Commits Check..."
!git log -1 --oneline | cut -c1-70 || echo "No recent commits"

## ✅ Definition of Done

!echo "☑️ 12. DoD Checklist Status..."
!test -f DEFINITION_OF_DONE_CHECKLIST.md && echo "✅ DoD checklist exists" || echo "❌ Missing DoD checklist"

## 📚 Documentation Status

!echo "📖 13. Key Documentation Files..."
!ls -la USER_CONTEXT_ARCHITECTURE.md docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md docs/GOLDEN_AGENT_INDEX.md 2>/dev/null | wc -l | xargs -I {} echo "  {} critical docs found"

## 🏃 Test Runner Status

!echo "🧪 14. Test Infrastructure..."
!test -f tests/unified_test_runner.py && echo "✅ Unified test runner available" || echo "❌ Missing test runner"
!test -f tests/mission_critical/test_websocket_agent_events_suite.py && echo "✅ WebSocket tests available" || echo "❌ Missing critical WebSocket tests"

## 📈 Final Compliance Score

!echo "===================="
!echo "🎯 COMPLIANCE SUMMARY"
!echo "===================="
!python scripts/check_architecture_compliance.py 2>/dev/null | tail -10 || echo "Run full compliance check for detailed report"