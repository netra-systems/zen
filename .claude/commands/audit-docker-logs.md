---
allowed-tools: ["Bash", "Task"]
description: "Audit Docker logs for errors, warnings, and performance issues"
argument-hint: "[service-name] [lines]"
---

# 🔍 Docker Logs Audit

Comprehensive Docker logs analysis for debugging and monitoring.

## Configuration
- **Service:** ${1:-all}
- **Lines:** ${2:-100}
- **Mode:** Audit with pattern detection

## Execution Steps

### 1. Service Status Overview
!echo "📊 Docker Service Status Overview:"
!docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Service}}"

### 2. Collect Logs
if [[ "${1:-all}" == "all" ]]; then
    !echo "\n🔍 Collecting logs from ALL services (last ${2:-100} lines each)..."
    !for service in postgres redis clickhouse auth backend frontend; do
        echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📦 Service: dev-$service"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        docker compose logs dev-$service --tail ${2:-100} 2>&1 || echo "Service not running"
    done
else
    !echo "\n🔍 Collecting logs from $1 (last ${2:-100} lines)..."
    !docker compose logs $1 --tail ${2:-100}
fi

### 3. Error Pattern Detection
!echo "\n⚠️ ERROR PATTERN ANALYSIS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

!echo "\n🔴 Critical Errors:"
!docker compose logs --tail 1000 2>&1 | grep -iE "(FATAL|CRITICAL|PANIC|Emergency)" | tail -10 || echo "✅ No critical errors found"

!echo "\n🟠 Standard Errors:"
!docker compose logs --tail 1000 2>&1 | grep -iE "(ERROR|Exception|Failed|Traceback)" | tail -10 || echo "✅ No standard errors found"

!echo "\n🟡 Warnings:"
!docker compose logs --tail 500 2>&1 | grep -iE "(WARNING|WARN|Deprecated)" | tail -5 || echo "✅ No warnings found"

### 4. Performance Indicators
!echo "\n📈 PERFORMANCE INDICATORS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

!echo "\n⏱️ Slow Operations:"
!docker compose logs --tail 500 2>&1 | grep -iE "(slow|timeout|took [0-9]+ms|latency)" | tail -5 || echo "✅ No slow operations detected"

!echo "\n💾 Memory Issues:"
!docker compose logs --tail 500 2>&1 | grep -iE "(memory|heap|OOM|allocation)" | tail -5 || echo "✅ No memory issues detected"

### 5. Connection & Network Issues
!echo "\n🌐 CONNECTION ANALYSIS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

!echo "\n🔌 Connection Failures:"
!docker compose logs --tail 500 2>&1 | grep -iE "(connection refused|connection reset|network|unreachable)" | tail -5 || echo "✅ No connection issues found"

!echo "\n🔐 Authentication Issues:"
!docker compose logs --tail 500 2>&1 | grep -iE "(unauthorized|forbidden|401|403|auth)" | tail -5 || echo "✅ No auth issues found"

### 6. Audit Summary
!echo "\n📋 AUDIT SUMMARY:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
!echo "Timestamp: $(date)"
!echo "Services Audited: ${1:-all}"
!echo "Log Lines Analyzed: ${2:-100} per service"

### 7. Spawn Task Agent for Deep Analysis (Optional)
@Task: If critical errors found, analyze root cause
If the audit reveals critical issues, spawn an analysis agent:
- Identify error patterns
- Trace error origins
- Suggest fixes
- Check for cascade failures

## Usage Examples
- `/audit-docker-logs` - Audit all services (last 100 lines)
- `/audit-docker-logs backend 500` - Audit backend (last 500 lines)
- `/audit-docker-logs auth` - Audit auth service