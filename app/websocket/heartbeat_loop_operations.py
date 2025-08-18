"""Heartbeat loop operations and ping/pong handling."""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.logging_config import central_logger
from .connection import ConnectionInfo
from . import heartbeat_utils as utils

logger = central_logger.get_logger(__name__)


class HeartbeatLoopOperations:
    """Handles heartbeat loop operations and ping/pong logic."""
    
    def __init__(self, connection_manager, config, statistics, missed_heartbeats):
        """Initialize loop operations handler."""
        self.connection_manager = connection_manager
        self.config = config
        self.statistics = statistics
        self.missed_heartbeats = missed_heartbeats
    
    async def run_heartbeat_monitoring(self, conn_info: ConnectionInfo) -> None:
        """Run main heartbeat monitoring loop."""
        while self.connection_manager.is_connection_alive(conn_info):
            should_continue = await self._handle_heartbeat_cycle(conn_info)
            if not should_continue:
                break
    
    async def _handle_heartbeat_cycle(self, conn_info: ConnectionInfo) -> bool:
        """Handle single heartbeat cycle with error management."""
        try:
            should_continue = await self._execute_heartbeat_cycle(conn_info)
            return should_continue
        except asyncio.CancelledError:
            raise
        except ConnectionError as e:
            return self._handle_connection_error(conn_info, e)
        except Exception as e:
            return not self._should_break_on_error(conn_info, e)
    
    def _handle_connection_error(self, conn_info: ConnectionInfo, error: ConnectionError) -> bool:
        """Handle connection error and return should continue flag."""
        utils.log_connection_closed(conn_info.connection_id, error)
        return False
    
    def _should_break_on_error(self, conn_info: ConnectionInfo, error: Exception) -> bool:
        """Determine if monitoring should break on this error."""
        if self._is_connection_closed_error(conn_info, error):
            return True
        return False
    
    def _is_connection_closed_error(self, conn_info: ConnectionInfo, error: Exception) -> bool:
        """Check if error indicates connection is closed."""
        error_msg = str(error).lower()
        if 'close' in error_msg or 'disconnect' in error_msg:
            logger.debug(f"Connection appears closed for {conn_info.connection_id}: {error}")
            return True
        return False
    
    async def _execute_heartbeat_cycle(self, conn_info: ConnectionInfo) -> bool:
        """Execute single heartbeat cycle."""
        await self._send_ping_and_update_stats(conn_info)
        await asyncio.sleep(self.config.interval_seconds)
        await self._check_pong_response(conn_info)
        return self._validate_connection_health(conn_info)
    
    async def _send_ping_and_update_stats(self, conn_info: ConnectionInfo) -> None:
        """Send ping and update statistics."""
        await self._send_ping(conn_info)
        conn_info.last_ping = datetime.now(timezone.utc)
        self.statistics.increment_ping_sent()
    
    def _validate_connection_health(self, conn_info: ConnectionInfo) -> bool:
        """Validate connection health after heartbeat cycle."""
        if not self._is_connection_alive(conn_info):
            logger.warning(f"Connection {conn_info.connection_id} failed heartbeat check")
            return False
        return True
    
    def _is_connection_alive(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is alive using manager and heartbeat checks."""
        if not self.connection_manager.is_connection_alive(conn_info):
            return False
        return self._check_heartbeat_health(conn_info)
    
    def _check_heartbeat_health(self, conn_info: ConnectionInfo) -> bool:
        """Check heartbeat-specific health indicators."""
        if not self._is_heartbeat_timeout_ok(conn_info):
            return False
        return self._is_missed_heartbeats_ok(conn_info)
    
    def _is_heartbeat_timeout_ok(self, conn_info: ConnectionInfo) -> bool:
        """Check if heartbeat timeout is within limits."""
        now = datetime.now(timezone.utc)
        time_since_ping = (now - conn_info.last_ping).total_seconds()
        if time_since_ping > self.config.timeout_seconds:
            logger.debug(f"Connection {conn_info.connection_id} heartbeat timeout ({time_since_ping:.1f}s)")
            return False
        return True
    
    def _is_missed_heartbeats_ok(self, conn_info: ConnectionInfo) -> bool:
        """Check if missed heartbeats are within limits."""
        missed_count = self.missed_heartbeats.get(conn_info.connection_id, 0)
        if missed_count >= self.config.max_missed_heartbeats:
            logger.debug(f"Connection {conn_info.connection_id} exceeded missed heartbeat limit ({missed_count})")
            return False
        return True
    
    async def _send_ping(self, conn_info: ConnectionInfo):
        """Send ping message to connection."""
        ping_message = utils.create_ping_message()
        try:
            utils.validate_connection_for_ping(conn_info, self.connection_manager)
            await utils.perform_ping_send(conn_info, ping_message)
        except ConnectionError:
            raise
        except Exception as e:
            self._handle_ping_error(conn_info, e)
    
    def _handle_ping_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Handle errors during ping sending."""
        if utils.is_connection_closed_ping_error(error):
            utils.handle_closed_connection_ping_error(conn_info.connection_id, error)
        utils.handle_general_ping_error(conn_info.connection_id, error)
        raise
    
    async def _check_pong_response(self, conn_info: ConnectionInfo):
        """Check if we received a pong response within the timeout."""
        time_since_response = utils.calculate_response_time(conn_info)
        if utils.is_response_timeout(time_since_response, self.config.timeout_seconds):
            await self._handle_pong_timeout(conn_info)
    
    async def _handle_pong_timeout(self, conn_info: ConnectionInfo) -> None:
        """Handle pong response timeout."""
        missed_count = utils.increment_missed_counter(self.missed_heartbeats, conn_info.connection_id)
        utils.log_missed_heartbeat(conn_info.connection_id, missed_count, self.config.max_missed_heartbeats)
        if utils.should_handle_timeout(missed_count, self.config.max_missed_heartbeats):
            self.statistics.increment_timeout()
    
    def handle_pong_received(self, conn_info: ConnectionInfo) -> None:
        """Handle pong response from client."""
        self._update_pong_timestamp(conn_info)
        self._reset_missed_heartbeat_counter(conn_info)
        self.statistics.increment_pong_received()
        self._log_pong_received(conn_info)
    
    def _update_pong_timestamp(self, conn_info: ConnectionInfo) -> None:
        """Update pong timestamp for connection."""
        conn_info.last_pong = datetime.now(timezone.utc)
    
    def _reset_missed_heartbeat_counter(self, conn_info: ConnectionInfo) -> None:
        """Reset missed heartbeat counter for connection."""
        if conn_info.connection_id in self.missed_heartbeats:
            self.missed_heartbeats[conn_info.connection_id] = 0
    
    def _log_pong_received(self, conn_info: ConnectionInfo) -> None:
        """Log pong received message."""
        logger.debug(f"Received pong from connection {conn_info.connection_id}")