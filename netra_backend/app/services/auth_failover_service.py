"""
Auth Failover Service
Provides high availability and failover capabilities for auth services
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuthFailoverService:
    """Service for managing auth service failover and high availability."""
    
    def __init__(self, service_registry: Optional[Dict[str, Any]] = None):
        """Initialize auth failover service."""
        self.failover_history: List[Dict[str, Any]] = []
        self.current_primary: Optional[str] = None
        self.service_registry = service_registry or {}
        
    async def initiate_failover(
        self, 
        failed_instance: str, 
        candidate_instances: List[str]
    ) -> Dict[str, Any]:
        """
        Initiate failover from failed instance to best candidate.
        
        Args:
            failed_instance: The instance that failed
            candidate_instances: List of candidate instances for failover
            
        Returns:
            Dict with failover result
        """
        logger.info(f"Initiating failover from {failed_instance}")
        
        # Select best candidate (first available for simplicity)
        new_primary = candidate_instances[0] if candidate_instances else None
        
        if not new_primary:
            return {
                'success': False,
                'error': 'No candidate instances available',
                'failed_instance': failed_instance
            }
        
        # Record failover
        failover_record = {
            'timestamp': time.time(),
            'failed_instance': failed_instance,
            'new_primary': new_primary,
            'candidates_considered': candidate_instances
        }
        self.failover_history.append(failover_record)
        self.current_primary = new_primary
        
        logger.info(f"Failover completed: {failed_instance} -> {new_primary}")
        
        return {
            'success': True,
            'new_primary': new_primary,
            'failed_instance': failed_instance,
            'failover_time': failover_record['timestamp']
        }
    
    async def notify_failover(self, old_primary: str, new_primary: str) -> Dict[str, Any]:
        """
        Notify about a completed failover.
        
        Args:
            old_primary: The previous primary instance
            new_primary: The new primary instance
            
        Returns:
            Dict with notification result
        """
        logger.info(f"Failover notification: {old_primary} -> {new_primary}")
        
        # Update current primary
        self.current_primary = new_primary
        
        # Record notification
        notification_record = {
            'timestamp': time.time(),
            'old_primary': old_primary,
            'new_primary': new_primary,
            'type': 'notification'
        }
        self.failover_history.append(notification_record)
        
        return {
            'success': True,
            'acknowledged': True,
            'current_primary': self.current_primary
        }
    
    async def reconcile_state(
        self, 
        instances: List[str], 
        conflict_resolution: str = 'last_write_wins'
    ) -> Dict[str, Any]:
        """
        Reconcile state conflicts between instances after partition heal.
        
        Args:
            instances: List of instances to reconcile
            conflict_resolution: Strategy for resolving conflicts
            
        Returns:
            Dict with reconciliation result
        """
        logger.info(f"Reconciling state for instances: {instances}")
        
        conflicts_detected = 0
        conflicts_resolved = 0
        
        # Get service instances for reconciliation
        services = []
        for instance_name in instances:
            service_key = f"{instance_name}_auth"
            if service_key in self.service_registry:
                services.append((instance_name, self.service_registry[service_key]))
        
        if len(services) < 2:
            logger.warning("Not enough services to reconcile")
            return {
                'success': False,
                'error': 'Insufficient services for reconciliation'
            }
        
        # Find conflicts in shared user data
        from netra_backend.app.services.user_auth_service import UserAuthService
        
        if UserAuthService._shared_user_data:
            conflicts_detected = len(UserAuthService._shared_user_data)
            
            # Apply conflict resolution based on strategy
            if conflict_resolution == 'last_write_wins':
                for user_id, data in UserAuthService._shared_user_data.items():
                    # Find the most recent update
                    latest_timestamp = data.get('updated_at', 0)
                    winning_data = data
                    
                    # Check all services for this user data
                    for instance_name, service in services:
                        user_data = await service.get_user_data(user_id)
                        if user_data and user_data.get('updated_at', 0) > latest_timestamp:
                            latest_timestamp = user_data['updated_at']
                            winning_data = user_data
                    
                    # Apply winning data to all services
                    for instance_name, service in services:
                        await service.update_user_data(user_id, winning_data)
                    
                    conflicts_resolved += 1
        
        # Record reconciliation
        reconciliation_record = {
            'timestamp': time.time(),
            'instances': instances,
            'conflict_resolution': conflict_resolution,
            'conflicts_detected': conflicts_detected,
            'conflicts_resolved': conflicts_resolved
        }
        self.failover_history.append(reconciliation_record)
        
        logger.info(f"State reconciliation completed: {conflicts_resolved} conflicts resolved")
        
        return {
            'success': True,
            'conflicts_detected': conflicts_detected,
            'conflicts_resolved': conflicts_resolved,
            'resolution_strategy': conflict_resolution,
            'reconciliation_time': reconciliation_record['timestamp']
        }
    
    def get_failover_history(self) -> List[Dict[str, Any]]:
        """Get the complete failover history."""
        return self.failover_history.copy()
    
    def get_current_primary(self) -> Optional[str]:
        """Get the current primary instance."""
        return self.current_primary


# Singleton instance
auth_failover_service = AuthFailoverService()