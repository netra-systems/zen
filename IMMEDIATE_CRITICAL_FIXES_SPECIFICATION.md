# Immediate Critical Fixes Specification

## Overview

While the SSOT context generation fix addresses the root architectural cause, these immediate critical fixes provide rapid relief for the WebSocket resource leak issue and improve user experience while the deeper architectural changes are implemented.

## Fix 1: Emergency Cleanup Enhancement (ULTRA-CRITICAL)

### Current State
- Emergency cleanup timeout: 30 seconds (improved from 5 minutes)
- Triggered at 70% capacity (14/20 managers)
- Background cleanup intervals: Dev 1min, Prod 2min

### Required Enhancement
- **Reduce timeout to 10 seconds** for immediate user relief
- **Trigger at 60% capacity** (12/20 managers) for earlier prevention
- **Add immediate cleanup on connection close**

### Implementation

**File**: `/netra_backend/app/websocket_core/websocket_manager_factory.py`

```python
# Update configuration constants
class WebSocketManagerFactory:
    def __init__(self):
        # CRITICAL: Reduce timeouts for faster user experience
        self.EMERGENCY_CLEANUP_TIMEOUT = 10.0  # seconds (was 30)
        self.CLEANUP_TRIGGER_THRESHOLD = 0.6   # 60% (was 70%)
        self.MAX_CLEANUP_RETRIES = 3
        
        # Environment-specific intervals
        env = get_env('NETRA_ENV', 'development')
        if env == 'production':
            self.BACKGROUND_CLEANUP_INTERVAL = 60  # 1 minute (was 2 min)
        else:
            self.BACKGROUND_CLEANUP_INTERVAL = 30  # 30 seconds (was 1 min)

    async def _emergency_cleanup_with_timeout(self, user_id: str) -> int:
        """Enhanced emergency cleanup with faster timeout"""
        logger.warning(f"EMERGENCY CLEANUP: Starting for user {user_id} with {self.EMERGENCY_CLEANUP_TIMEOUT}s timeout")
        
        start_time = asyncio.get_event_loop().time()
        retry_count = 0
        
        while retry_count < self.MAX_CLEANUP_RETRIES:
            try:
                cleaned_count = await asyncio.wait_for(
                    self._perform_emergency_cleanup(user_id),
                    timeout=self.EMERGENCY_CLEANUP_TIMEOUT / self.MAX_CLEANUP_RETRIES
                )
                
                logger.info(f"EMERGENCY CLEANUP: Cleaned {cleaned_count} managers for user {user_id} (attempt {retry_count + 1})")
                return cleaned_count
                
            except asyncio.TimeoutError:
                retry_count += 1
                elapsed = asyncio.get_event_loop().time() - start_time
                logger.warning(f"EMERGENCY CLEANUP: Timeout on attempt {retry_count} for user {user_id} (elapsed: {elapsed:.1f}s)")
                
                if retry_count >= self.MAX_CLEANUP_RETRIES:
                    logger.error(f"EMERGENCY CLEANUP: Failed after {self.MAX_CLEANUP_RETRIES} attempts for user {user_id}")
                    break
                    
            except Exception as e:
                logger.error(f"EMERGENCY CLEANUP: Error on attempt {retry_count + 1} for user {user_id}: {e}")
                retry_count += 1
                
        return 0

    async def _perform_emergency_cleanup(self, user_id: str) -> int:
        """Aggressive cleanup with multiple strategies"""
        cleaned_count = 0
        
        # Strategy 1: Clean disconnected managers
        cleaned_count += await self._cleanup_disconnected_managers(user_id)
        
        # Strategy 2: Clean idle managers (>5 minutes inactive)
        cleaned_count += await self._cleanup_idle_managers(user_id, max_idle_time=300)
        
        # Strategy 3: Clean managers with connection errors
        cleaned_count += await self._cleanup_error_state_managers(user_id)
        
        # Strategy 4: Force cleanup oldest managers if still over limit
        if await self.get_user_manager_count(user_id) > self.max_managers_per_user * self.CLEANUP_TRIGGER_THRESHOLD:
            cleaned_count += await self._force_cleanup_oldest_managers(user_id, target_count=5)
            
        return cleaned_count

    async def _cleanup_disconnected_managers(self, user_id: str) -> int:
        """Clean managers with disconnected WebSocket connections"""
        cleaned_count = 0
        managers_to_cleanup = []
        
        async with self._managers_lock:
            for isolation_key, manager_ref in list(self._active_managers.items()):
                if isolation_key.startswith(f"{user_id}:"):
                    manager = manager_ref()
                    if manager and not await self._is_connection_active(manager):
                        managers_to_cleanup.append(isolation_key)
        
        for isolation_key in managers_to_cleanup:
            try:
                await self._cleanup_single_manager(isolation_key)
                cleaned_count += 1
                logger.debug(f"Cleaned disconnected manager: {isolation_key}")
            except Exception as e:
                logger.warning(f"Failed to clean disconnected manager {isolation_key}: {e}")
                
        return cleaned_count

    async def _is_connection_active(self, manager) -> bool:
        """Check if manager's WebSocket connection is still active"""
        try:
            if hasattr(manager, 'websocket') and manager.websocket:
                # Try to ping the connection
                await manager.websocket.ping()
                return True
        except Exception:
            pass
        return False
```

## Fix 2: Isolation Key Standardization

### Current Issue
Isolation keys may use different patterns, causing lookup failures during cleanup.

### Solution
Standardize all isolation key generation to use `{user_id}:{thread_id}` pattern exclusively.

### Implementation

**File**: `/netra_backend/app/websocket_core/websocket_manager_factory.py`

```python
def _generate_isolation_key(self, user_context: UserExecutionContext) -> str:
    """
    STANDARDIZED isolation key generation
    
    CRITICAL: Always use thread_id for consistency. Never use connection_id
    or other fallbacks that may not exist during cleanup.
    """
    if not user_context.thread_id:
        raise ValueError(f"UserExecutionContext missing thread_id for user {user_context.user_id}")
    
    isolation_key = f"{user_context.user_id}:{user_context.thread_id}"
    
    # Validation: Ensure key follows expected pattern
    if not self._validate_isolation_key(isolation_key):
        raise ValueError(f"Generated invalid isolation key: {isolation_key}")
    
    return isolation_key

def _validate_isolation_key(self, isolation_key: str) -> bool:
    """Validate isolation key follows expected pattern"""
    parts = isolation_key.split(":", 1)
    if len(parts) != 2:
        return False
        
    user_id, thread_id = parts
    if not user_id or not thread_id:
        return False
        
    # thread_id should start with "thread_"
    if not thread_id.startswith("thread_"):
        return False
        
    return True

# Update all cleanup methods to use standardized key generation
async def cleanup_manager_by_context(self, user_context: UserExecutionContext) -> bool:
    """Cleanup manager using standardized isolation key from context"""
    isolation_key = self._generate_isolation_key(user_context)
    return await self.cleanup_manager(isolation_key)

async def cleanup_all_user_managers(self, user_id: str) -> int:
    """Cleanup all managers for a user using standardized key patterns"""
    cleaned_count = 0
    user_prefix = f"{user_id}:"
    
    async with self._managers_lock:
        keys_to_cleanup = [
            key for key in self._active_managers.keys() 
            if key.startswith(user_prefix) and self._validate_isolation_key(key)
        ]
    
    for isolation_key in keys_to_cleanup:
        try:
            if await self.cleanup_manager(isolation_key):
                cleaned_count += 1
        except Exception as e:
            logger.warning(f"Failed to cleanup manager {isolation_key}: {e}")
    
    return cleaned_count
```

## Fix 3: Immediate Cleanup on Connection Close

### Current Issue
WebSocket connections close but managers aren't immediately cleaned up, waiting for background cleanup cycles.

### Solution
Link WebSocket disconnection events directly to immediate manager cleanup.

### Implementation

**File**: `/netra_backend/app/core/websocket_message_handler.py`

```python
class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocketConnectionInfo] = {}
        self.factory = WebSocketManagerFactory()

    async def connect(self, websocket: WebSocket, user_context: UserExecutionContext):
        """Establish WebSocket connection with immediate cleanup registration"""
        await websocket.accept()
        
        connection_info = WebSocketConnectionInfo(
            websocket=websocket,
            user_context=user_context,
            connect_time=datetime.utcnow()
        )
        
        # Register connection for tracking
        isolation_key = self.factory._generate_isolation_key(user_context)
        self.active_connections[isolation_key] = connection_info
        
        logger.info(f"WebSocket connected: {isolation_key}")

    async def disconnect(self, user_context: UserExecutionContext):
        """Handle WebSocket disconnection with immediate cleanup"""
        isolation_key = self.factory._generate_isolation_key(user_context)
        
        # Remove from active connections
        if isolation_key in self.active_connections:
            del self.active_connections[isolation_key]
        
        # IMMEDIATE cleanup of associated manager
        try:
            cleanup_success = await self.factory.cleanup_manager_by_context(user_context)
            if cleanup_success:
                logger.info(f"IMMEDIATE CLEANUP: Success for {isolation_key}")
            else:
                logger.warning(f"IMMEDIATE CLEANUP: Failed for {isolation_key}, will retry in background")
        except Exception as e:
            logger.error(f"IMMEDIATE CLEANUP: Error for {isolation_key}: {e}")

@dataclass
class WebSocketConnectionInfo:
    websocket: WebSocket
    user_context: UserExecutionContext
    connect_time: datetime
    last_activity: datetime = field(default_factory=datetime.utcnow)
```

## Fix 4: Proactive Resource Monitoring

### Implementation

**File**: `/netra_backend/app/websocket_core/resource_monitor.py`

```python
class WebSocketResourceMonitor:
    """Real-time monitoring and alerting for WebSocket resources"""
    
    def __init__(self, factory: WebSocketManagerFactory):
        self.factory = factory
        self.alert_thresholds = {
            "info": 0.4,      # 8 managers - informational
            "warning": 0.6,   # 12 managers - start proactive cleanup  
            "critical": 0.8,  # 16 managers - aggressive cleanup
            "emergency": 0.9  # 18 managers - emergency protocols
        }
        self.user_alerts: Dict[str, str] = {}  # Track alert levels per user

    async def check_user_resources(self, user_id: str) -> Dict[str, Any]:
        """Check resource usage and trigger appropriate actions"""
        manager_count = await self.factory.get_user_manager_count(user_id)
        usage_ratio = manager_count / self.factory.max_managers_per_user
        
        current_level = self._determine_alert_level(usage_ratio)
        previous_level = self.user_alerts.get(user_id, "normal")
        
        # Only act on level changes or critical+ levels
        if current_level != previous_level or usage_ratio >= self.alert_thresholds["critical"]:
            await self._handle_resource_alert(user_id, current_level, manager_count, usage_ratio)
            self.user_alerts[user_id] = current_level
        
        return {
            "user_id": user_id,
            "manager_count": manager_count,
            "usage_ratio": usage_ratio,
            "alert_level": current_level,
            "max_managers": self.factory.max_managers_per_user
        }

    def _determine_alert_level(self, usage_ratio: float) -> str:
        """Determine alert level based on usage ratio"""
        for level, threshold in reversed(self.alert_thresholds.items()):
            if usage_ratio >= threshold:
                return level
        return "normal"

    async def _handle_resource_alert(self, user_id: str, level: str, count: int, ratio: float):
        """Handle resource alerts with appropriate actions"""
        logger.info(f"RESOURCE ALERT: User {user_id} - {level} level ({count} managers, {ratio:.1%})")
        
        if level == "warning":
            # Proactive cleanup of idle managers
            await self._proactive_cleanup(user_id)
            
        elif level == "critical":
            # Aggressive cleanup with shorter timeout
            await self.factory._emergency_cleanup_with_timeout(user_id)
            
        elif level == "emergency":
            # Full emergency protocols
            await self._emergency_resource_recovery(user_id)

    async def _proactive_cleanup(self, user_id: str):
        """Proactive cleanup before hitting critical levels"""
        logger.info(f"PROACTIVE CLEANUP: Starting for user {user_id}")
        
        # Clean disconnected and idle managers
        cleaned = await self.factory._cleanup_disconnected_managers(user_id)
        cleaned += await self.factory._cleanup_idle_managers(user_id, max_idle_time=180)  # 3 minutes
        
        logger.info(f"PROACTIVE CLEANUP: Cleaned {cleaned} managers for user {user_id}")

    async def _emergency_resource_recovery(self, user_id: str):
        """Emergency resource recovery protocols"""
        logger.error(f"EMERGENCY RESOURCE RECOVERY: Starting for user {user_id}")
        
        # 1. Immediate aggressive cleanup
        cleaned = await self.factory._emergency_cleanup_with_timeout(user_id)
        
        # 2. If still over limit, force cleanup oldest managers
        remaining = await self.factory.get_user_manager_count(user_id)
        if remaining >= self.factory.max_managers_per_user * 0.8:
            forced_cleaned = await self.factory._force_cleanup_oldest_managers(
                user_id, 
                target_count=int(self.factory.max_managers_per_user * 0.5)  # Reduce to 50%
            )
            logger.warning(f"EMERGENCY: Force cleaned {forced_cleaned} managers for user {user_id}")
```

## Fix 5: Enhanced Background Cleanup

### Implementation

**File**: `/netra_backend/app/websocket_core/websocket_manager_factory.py`

```python
async def _enhanced_background_cleanup(self):
    """Enhanced background cleanup with multiple strategies"""
    logger.debug("Starting enhanced background cleanup cycle")
    
    start_time = time.time()
    total_cleaned = 0
    users_processed = 0
    
    try:
        # Get all active users
        active_users = await self._get_active_users()
        
        for user_id in active_users:
            try:
                # Check resource usage first
                manager_count = await self.get_user_manager_count(user_id)
                if manager_count == 0:
                    continue
                    
                users_processed += 1
                user_cleaned = 0
                
                # Strategy 1: Clean disconnected managers
                user_cleaned += await self._cleanup_disconnected_managers(user_id)
                
                # Strategy 2: Clean idle managers (>10 minutes)
                user_cleaned += await self._cleanup_idle_managers(user_id, max_idle_time=600)
                
                # Strategy 3: Clean managers with errors
                user_cleaned += await self._cleanup_error_state_managers(user_id)
                
                total_cleaned += user_cleaned
                
                if user_cleaned > 0:
                    logger.info(f"Background cleanup: Cleaned {user_cleaned} managers for user {user_id}")
                    
            except Exception as e:
                logger.error(f"Background cleanup error for user {user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Enhanced background cleanup error: {e}")
        
    finally:
        duration = time.time() - start_time
        logger.info(f"Background cleanup completed: {total_cleaned} managers cleaned "
                   f"across {users_processed} users in {duration:.1f}s")

async def _get_active_users(self) -> Set[str]:
    """Get list of users with active managers"""
    active_users = set()
    
    async with self._managers_lock:
        for isolation_key in self._active_managers.keys():
            user_id = isolation_key.split(":", 1)[0]
            active_users.add(user_id)
            
    return active_users

async def _cleanup_error_state_managers(self, user_id: str) -> int:
    """Clean managers that are in error states"""
    cleaned_count = 0
    managers_to_cleanup = []
    
    async with self._managers_lock:
        for isolation_key, manager_ref in list(self._active_managers.items()):
            if isolation_key.startswith(f"{user_id}:"):
                manager = manager_ref()
                if manager and await self._is_manager_in_error_state(manager):
                    managers_to_cleanup.append(isolation_key)
    
    for isolation_key in managers_to_cleanup:
        try:
            await self._cleanup_single_manager(isolation_key)
            cleaned_count += 1
            logger.debug(f"Cleaned error-state manager: {isolation_key}")
        except Exception as e:
            logger.warning(f"Failed to clean error-state manager {isolation_key}: {e}")
            
    return cleaned_count

async def _is_manager_in_error_state(self, manager) -> bool:
    """Check if manager is in an error state"""
    try:
        # Check various error conditions
        if hasattr(manager, '_connection_error') and manager._connection_error:
            return True
        if hasattr(manager, '_last_error_time') and manager._last_error_time:
            # Clean managers with errors from >5 minutes ago
            if time.time() - manager._last_error_time > 300:
                return True
        return False
    except Exception:
        return True  # If we can't check state, assume it's in error
```

## Configuration Updates

### Environment-Specific Settings

**File**: `/netra_backend/app/websocket_core/websocket_config.py`

```python
class WebSocketConfig:
    """Centralized WebSocket configuration with environment awareness"""
    
    def __init__(self):
        env = get_env('NETRA_ENV', 'development')
        
        # Base configuration
        self.MAX_MANAGERS_PER_USER = 20
        
        if env == 'production':
            self.EMERGENCY_CLEANUP_TIMEOUT = 10.0
            self.BACKGROUND_CLEANUP_INTERVAL = 60  # 1 minute
            self.PROACTIVE_CLEANUP_THRESHOLD = 0.6  # 60%
            self.IDLE_MANAGER_TIMEOUT = 600  # 10 minutes
            
        elif env == 'staging':
            self.EMERGENCY_CLEANUP_TIMEOUT = 5.0
            self.BACKGROUND_CLEANUP_INTERVAL = 30  # 30 seconds
            self.PROACTIVE_CLEANUP_THRESHOLD = 0.5  # 50%
            self.IDLE_MANAGER_TIMEOUT = 300  # 5 minutes
            
        else:  # development/test
            self.EMERGENCY_CLEANUP_TIMEOUT = 2.0
            self.BACKGROUND_CLEANUP_INTERVAL = 15  # 15 seconds
            self.PROACTIVE_CLEANUP_THRESHOLD = 0.4  # 40%
            self.IDLE_MANAGER_TIMEOUT = 120  # 2 minutes

    def get_cleanup_config(self) -> Dict[str, Any]:
        """Get cleanup configuration for current environment"""
        return {
            "emergency_timeout": self.EMERGENCY_CLEANUP_TIMEOUT,
            "background_interval": self.BACKGROUND_CLEANUP_INTERVAL,
            "proactive_threshold": self.PROACTIVE_CLEANUP_THRESHOLD,
            "idle_timeout": self.IDLE_MANAGER_TIMEOUT,
            "max_managers": self.MAX_MANAGERS_PER_USER
        }
```

## Success Metrics

### Key Performance Indicators
1. **Emergency Cleanup Time**: <10 seconds (target: <5 seconds)
2. **Background Cleanup Effectiveness**: >90% idle managers cleaned
3. **User Resource Alert Frequency**: <5% of users reach warning level
4. **Manager Accumulation Rate**: 0 net accumulation over 24-hour periods
5. **Connection Success Rate**: >99% after implementing fixes

### Monitoring Commands
```bash
# Check current resource usage
python -c "
from netra_backend.app.websocket_core.resource_monitor import WebSocketResourceMonitor
import asyncio
monitor = WebSocketResourceMonitor(factory)
asyncio.run(monitor.check_user_resources('target-user-id'))
"

# Trigger emergency cleanup test
python -c "
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
import asyncio
factory = WebSocketManagerFactory()
asyncio.run(factory._emergency_cleanup_with_timeout('test-user-id'))
"
```

These immediate critical fixes provide rapid relief for WebSocket resource leak symptoms while the deeper SSOT architectural fixes are implemented. They work in conjunction with the SSOT context generation fix to provide comprehensive resource leak prevention.

---

**Implementation Priority**: ULTRA-CRITICAL  
**Estimated Implementation Time**: 2-3 hours  
**Dependencies**: Can be implemented independently or alongside SSOT fix  
**Risk Level**: LOW (Enhances existing functionality)  
**Expected Impact**: 80% reduction in resource leak incidents