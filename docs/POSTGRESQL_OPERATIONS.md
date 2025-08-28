# PostgreSQL Operations Guide

## Quick Reference

### Health Monitoring
```bash
# Check overall PostgreSQL health
python scripts/postgres_health_monitor.py

# Check container status
docker ps --filter name=netra-postgres

# View recent logs
docker logs netra-postgres --tail 50
```

### Graceful Shutdown
```bash
# For planned maintenance - use this instead of docker stop
python scripts/graceful_postgres_shutdown.py

# Emergency stop (fallback)
docker stop --time 30 netra-postgres
```

### Recovery Detection
The health monitor automatically detects recovery scenarios. Look for:
- `[WARNING] Recovery Detected` in health reports
- Log entries containing "automatic recovery in progress"
- Log entries containing "checkpoint starting: end-of-recovery"

### Common Issues and Solutions

#### Issue: Recovery Detected
**Symptoms:** Health monitor shows recovery warning, logs contain recovery messages
**Cause:** Database was not properly shut down (container killed, system crash, etc.)
**Solution:** 
1. Verify data integrity with health monitor
2. Check all tables are present and accessible
3. Use graceful shutdown script for future shutdowns

#### Issue: Foreign Key Violations
**Symptoms:** Logs show "violates foreign key constraint" errors
**Cause:** Application attempting to insert records with non-existent foreign keys
**Solution:** 
1. Check if referenced records exist in parent tables
2. Verify application logic for entity creation order
3. Consider using database transactions for related inserts

#### Issue: High Connection Count
**Symptoms:** Health monitor warns about high active connections
**Cause:** Connection pool exhaustion or connection leaks
**Solution:**
1. Check application connection handling
2. Review connection pool configuration
3. Restart services if needed to reset connections

### Configuration Files
- `docker-compose.dev.yml`: PostgreSQL container configuration with graceful shutdown
- `scripts/graceful_postgres_shutdown.py`: Planned shutdown procedures
- `scripts/postgres_health_monitor.py`: Health monitoring and recovery detection
- `SPEC/learnings/database.xml`: Comprehensive database learnings and troubleshooting

### Best Practices
1. **Always use graceful shutdown script** for planned maintenance
2. **Monitor health regularly** to detect issues early
3. **Check logs after restarts** to ensure no recovery occurred
4. **Validate data integrity** after any recovery scenarios
5. **Use proper Docker signals** (SIGTERM) for container shutdown

### Emergency Procedures

#### Data Integrity Check
```bash
# Quick integrity verification
docker exec netra-postgres psql -U netra -d netra_dev -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';"

# Detailed table check
docker exec netra-postgres psql -U netra -d netra_dev -c "\dt"
```

#### Recovery Status Check
```bash
# Check for recent recovery in logs
docker logs netra-postgres 2>&1 | grep -i "recovery\|crash\|restart\|shutdown"
```

#### Connection Reset
```bash
# If connection issues persist, restart the container gracefully
python scripts/graceful_postgres_shutdown.py
docker-compose -f docker-compose.dev.yml up -d postgres
```

---
**Last Updated:** 2025-08-28  
**Related Documentation:** SPEC/learnings/database.xml