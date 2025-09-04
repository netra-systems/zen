---
allowed-tools: ["Bash", "Task"]
description: "Audit Docker logs for errors, warnings, and performance issues with automatic debugging"
argument-hint: "[service-name] [lines]"
---

# 🔍 Docker Logs Audit with Auto-Debug

Comprehensive Docker logs analysis for debugging and monitoring, with automatic error debugging via Five Whys.

## Configuration
- **Service:** ${1:-all}
- **Lines:** ${2:-100}
- **Mode:** Audit with pattern detection and auto-debug

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

### 3. Error Pattern Detection & Collection
!echo "\n⚠️ ERROR PATTERN ANALYSIS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Collect critical errors
!echo "\n🔴 Critical Errors:"
!docker compose logs --tail 1000 2>&1 | grep -iE "(FATAL|CRITICAL|PANIC|Emergency)" > /tmp/critical_errors.log
!if [ -s /tmp/critical_errors.log ]; then
    cat /tmp/critical_errors.log | tail -10
    echo "CRITICAL_ERRORS_FOUND=true" > /tmp/error_status.env
else
    echo "✅ No critical errors found"
    echo "CRITICAL_ERRORS_FOUND=false" > /tmp/error_status.env
fi

# Collect standard errors
!echo "\n🟠 Standard Errors:"
!docker compose logs --tail 1000 2>&1 | grep -iE "(ERROR|Exception|Failed|Traceback)" > /tmp/standard_errors.log
!if [ -s /tmp/standard_errors.log ]; then
    cat /tmp/standard_errors.log | tail -10
    echo "STANDARD_ERRORS_FOUND=true" >> /tmp/error_status.env
else
    echo "✅ No standard errors found"
    echo "STANDARD_ERRORS_FOUND=false" >> /tmp/error_status.env
fi

# Collect warnings
!echo "\n🟡 Warnings:"
!docker compose logs --tail 500 2>&1 | grep -iE "(WARNING|WARN|Deprecated)" > /tmp/warnings.log
!if [ -s /tmp/warnings.log ]; then
    cat /tmp/warnings.log | tail -5
    echo "WARNINGS_FOUND=true" >> /tmp/error_status.env
else
    echo "✅ No warnings found"
    echo "WARNINGS_FOUND=false" >> /tmp/error_status.env
fi

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

### 7. Error Analysis & Prioritization
!echo "\n🎯 ERROR PRIORITIZATION:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Analyze error patterns and select most critical for debugging
!if [ -s /tmp/critical_errors.log ] || [ -s /tmp/standard_errors.log ]; then
    echo "🔍 Analyzing error patterns for debugging..."
    
    # Get the most recent critical error
    if [ -s /tmp/critical_errors.log ]; then
        CRITICAL_ERROR=$(tail -1 /tmp/critical_errors.log)
        echo "Most recent critical error: $CRITICAL_ERROR"
    fi
    
    # Get the most frequent standard error
    if [ -s /tmp/standard_errors.log ]; then
        FREQUENT_ERROR=$(cat /tmp/standard_errors.log | grep -oE "ERROR.*:" | sort | uniq -c | sort -rn | head -1 | sed 's/^[[:space:]]*[0-9]*[[:space:]]*//')
        echo "Most frequent error pattern: $FREQUENT_ERROR"
    fi
    
    # Select primary error for debugging
    if [ ! -z "$CRITICAL_ERROR" ]; then
        PRIMARY_ERROR="$CRITICAL_ERROR"
        ERROR_PRIORITY="CRITICAL"
    elif [ ! -z "$FREQUENT_ERROR" ]; then
        PRIMARY_ERROR="$FREQUENT_ERROR"
        ERROR_PRIORITY="FREQUENT"
    else
        PRIMARY_ERROR=$(tail -1 /tmp/standard_errors.log)
        ERROR_PRIORITY="RECENT"
    fi
    
    echo "\n📍 Primary error selected for debugging ($ERROR_PRIORITY):"
    echo "$PRIMARY_ERROR"
    echo "$PRIMARY_ERROR" > /tmp/primary_error.txt
    echo "ERRORS_FOUND=true" > /tmp/debug_trigger.env
else
    echo "✅ No errors requiring immediate debugging"
    echo "ERRORS_FOUND=false" > /tmp/debug_trigger.env
fi

### 8. Automatic Error Debugging Trigger

# Check if errors were found that need debugging
!source /tmp/debug_trigger.env 2>/dev/null || true
!if [ "$ERRORS_FOUND" = "true" ]; then
    echo "\n🚨 INITIATING AUTOMATIC ERROR DEBUGGING:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    PRIMARY_ERROR=$(cat /tmp/primary_error.txt 2>/dev/null || echo "Unknown error from Docker logs")
    echo "Launching Five Whys analysis with dynamic agent allocation..."
    echo ""
    echo "Error being debugged: $PRIMARY_ERROR"
    echo ""
    # Note: The actual /debug-error command will be invoked by the assistant
    echo "🤖 Invoking /debug-error command for deep analysis..."
fi

### 9. Conditional Debug-Error Invocation

@Task: Automatically debug critical errors if found
If critical or frequent errors were detected in the Docker logs:
1. Read /tmp/primary_error.txt to get the error description
2. Invoke the /debug-error slash command with that error
3. Use Five Whys methodology to find root cause
4. Dynamically allocate specialist agents based on error type
5. Implement fix with 80% consensus threshold

The debug-error command should be invoked as:
/debug-error "ERROR_FROM_DOCKER_LOGS"

Where ERROR_FROM_DOCKER_LOGS is the content from /tmp/primary_error.txt

### 10. Post-Audit Actions

!echo "\n📊 POST-AUDIT RECOMMENDATIONS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

!if [ -s /tmp/warnings.log ]; then
    echo "⚠️ Address warnings to prevent future errors"
fi

!if [ -s /tmp/standard_errors.log ] && [ "$ERRORS_FOUND" != "true" ]; then
    echo "🔍 Consider investigating non-critical errors"
fi

!echo "\nNext steps:"
!if [ "$ERRORS_FOUND" = "true" ]; then
    echo "1. ⏳ Automatic debugging in progress via /debug-error"
    echo "2. 📝 Review Five Whys analysis when complete"
    echo "3. 🔧 Apply consensus-approved fix"
else
    echo "1. ✅ System appears healthy"
    echo "2. 📊 Continue monitoring"
    echo "3. 🔄 Schedule regular audits"
fi

## Usage Examples
- `/audit-docker-logs` - Audit all services with auto-debug
- `/audit-docker-logs backend 500` - Audit backend (last 500 lines)
- `/audit-docker-logs auth` - Audit auth service

## Features
- **Comprehensive Analysis** - Errors, warnings, performance, connections
- **Auto-Debug Trigger** - Automatically invokes /debug-error for critical issues
- **Error Prioritization** - Selects most important error for debugging
- **Five Whys Integration** - Deep root cause analysis when errors found
- **Dynamic Agent Allocation** - Right expertise for each error type