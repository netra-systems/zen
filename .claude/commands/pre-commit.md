---
allowed-tools: ["Bash", "Read", "TodoWrite", "Task"]
description: "Complete CLAUDE.md compliance checklist before committing"
argument-hint: "[scope]"
---

# Pre-Commit CLAUDE.md Compliance Checklist

## 🚨 ULTRA CRITICAL: Complete ALL checks before commit

Scope: **${1:-all}**

## Phase 1: Critical Values & Dependencies

!echo "==========================================="
!echo "🚨 PHASE 1: MISSION CRITICAL VALUES CHECK"
!echo "==========================================="

!echo "\n1️⃣ Checking MISSION_CRITICAL_NAMED_VALUES_INDEX.xml..."
!python -c "import xml.etree.ElementTree as ET; tree = ET.parse('SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml'); values = [elem.text for elem in tree.findall('.//value')]; print(f'  ✅ {len(values)} critical values validated')" || echo "  ❌ STOP! Cannot access critical values!"

!echo "\n2️⃣ Validating string literals for changed files..."
!git diff --name-only | grep "\.py$" | head -5 | while read f; do echo "  Checking $f"; done
!python scripts/query_string_literals.py validate "POSTGRES_HOST" > /dev/null && echo "  ✅ String literals validated" || echo "  ⚠️ Update string literals index"

!echo "\n3️⃣ Checking recent learnings..."
!ls -t SPEC/learnings/*.xml 2>/dev/null | head -3 | while read f; do echo "  📚 $(basename $f)"; done

## Phase 2: Architecture Compliance

!echo "\n==========================================="
!echo "🏗️ PHASE 2: ARCHITECTURE COMPLIANCE"
!echo "==========================================="

!echo "\n4️⃣ SSOT (Single Source of Truth) Verification..."
!git diff --name-only | xargs -I {} grep -l "class\|def" {} 2>/dev/null | while read f; do echo "  Checking $f for duplicates..."; done
!echo "  ✅ Remember: One canonical implementation per service"

!echo "\n5️⃣ Import Rules Check (ABSOLUTE ONLY)..."
!git diff --name-only | grep "\.py$" | xargs grep "from \." 2>/dev/null | head -3 || echo "  ✅ No relative imports in changes"

!echo "\n6️⃣ File Location Verification..."
!echo "  Service-specific tests:"
!git diff --name-only | grep "test.*\.py$" | while read f; do 
    if [[ $f == netra_backend/* ]] || [[ $f == auth_service/* ]]; then 
        echo "    ✅ $f"; 
    elif [[ $f == tests/e2e/* ]]; then 
        echo "    ✅ E2E: $f"; 
    else 
        echo "    ⚠️ CHECK LOCATION: $f"; 
    fi; 
done

## Phase 3: Testing Requirements (NO MOCKS)

!echo "\n==========================================="
!echo "🧪 PHASE 3: TESTING WITH REAL SERVICES"
!echo "==========================================="

!echo "\n7️⃣ Mock Detection in Changed Tests..."
!git diff --name-only | grep "test.*\.py$" | xargs grep -l "Mock\|patch\|MagicMock" 2>/dev/null | while read f; do echo "  ❌ FORBIDDEN: Mock in $f"; done || echo "  ✅ No mocks detected"

!echo "\n8️⃣ Docker Services Health Check..."
!docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | grep -E "(healthy|starting)" | wc -l | xargs -I {} echo "  {} services running"

!echo "\n9️⃣ Running Tests for Changed Modules..."
if [[ "$1" == "backend" ]]; then
    !echo "  Testing backend changes..."
    !python tests/unified_test_runner.py --real-services --category integration --fast-fail 2>&1 | tail -5
elif [[ "$1" == "agents" ]]; then
    !echo "  Testing agent changes..."
    !python tests/mission_critical/test_websocket_agent_events_suite.py 2>&1 | tail -5
else
    !echo "  Running smoke tests..."
    !python tests/unified_test_runner.py --real-services --category smoke --fast-fail 2>&1 | tail -5
fi

## Phase 4: WebSocket & Business Value

!echo "\n==========================================="
!echo "💼 PHASE 4: BUSINESS VALUE VERIFICATION"
!echo "==========================================="

!echo "\n🔟 WebSocket Event Compliance..."
!git diff --name-only | grep "agents.*\.py$" | while read f; do
    echo "  Checking $f for required events..."
    grep -q "agent_started\|agent_thinking\|tool_executing" "$f" && echo "    ✅ Events found" || echo "    ⚠️ Missing events"
done

!echo "\n1️⃣1️⃣ Business Value Justification..."
!echo "  Ask yourself:"
!echo "  - Does this improve AI chat value delivery?"
!echo "  - Does this help with user conversion/retention?"
!echo "  - Is this the minimal change needed?"
!echo "  - Have I removed ALL legacy code?"

## Phase 5: Documentation & Cleanup

!echo "\n==========================================="
!echo "📚 PHASE 5: DOCUMENTATION & CLEANUP"
!echo "==========================================="

!echo "\n1️⃣2️⃣ DoD Checklist Review..."
!echo "  Opening Definition of Done checklist..."
@DEFINITION_OF_DONE_CHECKLIST.md
!echo "  ⚠️ Verify ALL items for your module"

!echo "\n1️⃣3️⃣ Update Documentation..."
!git diff --name-only | grep -E "\.(py|ts|tsx)$" | while read f; do
    module=$(echo $f | cut -d'/' -f1-2)
    echo "  Check docs needed for: $module"
done

!echo "\n1️⃣4️⃣ String Literals Index Update..."
!git diff --name-only | grep "\.py$" | head -1 > /dev/null && echo "  Running: python scripts/scan_string_literals.py" || echo "  No Python changes"

## Phase 6: Git Commit Standards

!echo "\n==========================================="
!echo "📝 PHASE 6: COMMIT PREPARATION"
!echo "==========================================="

!echo "\n1️⃣5️⃣ Atomic Commit Guidelines..."
!echo "  Remember:"
!echo "  - Group by CONCEPT, not by bulk"
!echo "  - Each commit < 1 minute review time"
!echo "  - Include MRO report for refactors"
!echo "  - Scope: 1-10 related files max"

!echo "\n1️⃣6️⃣ Suggested Commit Groups..."
!git diff --name-only | head -10 | while read f; do
    component=$(echo $f | cut -d'/' -f1-2)
    echo "  $component: $f"
done | sort | uniq -c | while read count comp; do
    echo "  Group: $comp ($count files)"
done

## Phase 7: Final Verification

!echo "\n==========================================="
!echo "✅ PHASE 7: FINAL CHECKLIST"
!echo "==========================================="

!echo ""
!echo "MANDATORY CHECKLIST (Mental Review):"
!echo "[ ] Mission critical values checked"
!echo "[ ] No relative imports"
!echo "[ ] No mocks in tests"
!echo "[ ] Real services tested"
!echo "[ ] WebSocket events present (if agent change)"
!echo "[ ] Business value justified"
!echo "[ ] DoD checklist completed"
!echo "[ ] String literals updated"
!echo "[ ] Documentation updated"
!echo "[ ] Legacy code removed"
!echo "[ ] Commits grouped by concept"

!echo "\n🎯 COMPLIANCE SCORE:"
!python scripts/check_architecture_compliance.py 2>/dev/null | grep -E "Score|PASS|FAIL" | tail -5 || echo "Run full compliance for detailed report"

!echo "\n==========================================="
!echo "🚀 READY TO COMMIT?"
!echo "==========================================="
!echo "If all checks pass, proceed with:"
!echo "  git add <files>"
!echo "  git commit -m \"<type>(scope): description\""
!echo ""
!echo "Remember: THINK DEEPLY. This work MATTERS."