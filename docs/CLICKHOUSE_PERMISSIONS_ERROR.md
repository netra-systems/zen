# ClickHouse Permissions Error - Resolution Guide

## Error Message
```
Failed to create workload_events table: HTTPDriver for https://xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443 
received ClickHouse error code 497
Code: 497. DB::Exception: development_user: Not enough privileges. 
To execute this query, it's necessary to have the grant CREATE TABLE ON development.workload_events. (ACCESS_DENIED)
```

## Problem
The `development_user` account lacks the necessary privileges to create tables in the ClickHouse `development` database.

## Solution

### Quick Fix
Connect to ClickHouse as an admin user and grant the required permission:

```sql
GRANT CREATE TABLE ON development.* TO development_user;
```

### Comprehensive Development Permissions
For a development environment, grant a complete set of permissions:

```sql
GRANT CREATE, ALTER, DROP, INSERT, SELECT, DELETE, UPDATE ON development.* TO development_user;
```

## Step-by-Step Resolution

### 1. Connect as Admin
Use the ClickHouse Cloud console or CLI with admin credentials:

```bash
clickhouse-client --host xedvrr4c3r.us-central1.gcp.clickhouse.cloud \
                  --port 8443 \
                  --user admin_user \
                  --password YOUR_ADMIN_PASSWORD \
                  --secure
```

### 2. Verify Current Permissions
Check existing permissions for the user:

```sql
SHOW GRANTS FOR development_user;
```

### 3. Grant Required Permissions
Execute the grant statement:

```sql
-- Minimum required for table creation
GRANT CREATE TABLE ON development.* TO development_user;

-- Recommended for development work
GRANT ALL ON development.* TO development_user;
```

### 4. Verify Permissions Applied
Confirm the grants were successful:

```sql
SHOW GRANTS FOR development_user;
```

## Alternative Solutions

### If You Don't Have Admin Access

1. **Contact Database Administrator**: Request the necessary permissions be granted
2. **Use a Different User**: If available, use credentials with appropriate permissions
3. **Update Environment Variables**: Ensure `CLICKHOUSE_USER` points to a user with correct privileges

### Environment Configuration
Update your `.env` file if using a different user:

```env
CLICKHOUSE_URL=https://xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443
CLICKHOUSE_USER=user_with_permissions
CLICKHOUSE_PASSWORD=secure_password
CLICKHOUSE_DATABASE=development
```

## Prevention

### Best Practices for Development Setup

1. **Initial User Setup**: When creating development users, grant appropriate permissions immediately:
   ```sql
   CREATE USER IF NOT EXISTS development_user IDENTIFIED BY 'password';
   GRANT ALL ON development.* TO development_user;
   ```

2. **Role-Based Access**: Create a development role with standard permissions:
   ```sql
   CREATE ROLE developer;
   GRANT CREATE, ALTER, DROP, INSERT, SELECT, DELETE, UPDATE ON development.* TO developer;
   GRANT developer TO development_user;
   ```

3. **Document Permissions**: Maintain a list of required permissions in your project documentation

## Related Configuration Files

- `app/db/clickhouse.py` - ClickHouse connection configuration
- `app/config.py` - Database URL and credentials configuration
- `.env` - Environment variables for database connection

## Troubleshooting

### Common Issues

1. **Permission Denied After Grant**: 
   - Ensure you're granting on the correct database (`development.*` not just `development`)
   - Check if the user needs to reconnect for permissions to take effect

2. **Cannot Connect as Admin**:
   - Verify admin credentials with your ClickHouse Cloud dashboard
   - Check network connectivity and firewall rules

3. **Grant Command Fails**:
   - Ensure the granting user has `GRANT OPTION` privilege
   - Verify the target user exists: `SHOW USERS`

## Reference
- [ClickHouse Access Rights Documentation](https://clickhouse.com/docs/en/operations/access-rights)
- [ClickHouse Cloud Management](https://clickhouse.cloud)