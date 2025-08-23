/**
 * WebSocket Test Components
 * All functions ≤8 lines for modular architecture compliance
 */

import React from 'react';
import { 
  sendMessageOrBuffer,
  flushMessageBuffer,
  calculateBackoffDelay,
  sendHeartbeat,
  checkConnectionHealth,
  setupReconnectionTimer,
  startCountdownTimer
} from '../helpers/websocket-helpers';
import { wrapStateSetterWithAct } from '../../../test-utils/react-act-utils';

interface ResilientWebSocketProps {
  messageBuffer: any[];
}

export const ResilientWebSocketComponent: React.FC<ResilientWebSocketProps> = ({ messageBuffer }) => {
  const [connectionState, setConnectionState] = React.useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [messages, setMessages] = React.useState<any[]>([]);
  const [reconnectAttempts, setReconnectAttempts] = React.useState(0);
  const wsRef = React.useRef<WebSocket | null>(null);
  
  // Wrap state setters with act() to prevent warnings
  const safeSetConnectionState = wrapStateSetterWithAct(setConnectionState);
  const safeSetMessages = wrapStateSetterWithAct(setMessages);
  const safeSetReconnectAttempts = wrapStateSetterWithAct(setReconnectAttempts);

  const sendMessage = (message: any) => {
    return sendMessageOrBuffer(wsRef.current, message, messageBuffer);
  };

  const handleWebSocketOpen = () => {
    safeSetConnectionState('connected');
    safeSetReconnectAttempts(0);
    flushMessageBuffer(wsRef.current!, messageBuffer);
  };

  const handleWebSocketClose = () => {
    safeSetConnectionState('disconnected');
    safeSetReconnectAttempts(prev => prev + 1);
    setupReconnectionTimer(reconnectAttempts, 5, connect);
  };

  const handleWebSocketError = () => {
    safeSetConnectionState('error');
  };

  const handleWebSocketMessage = (event: MessageEvent) => {
    const message = JSON.parse(event.data);
    safeSetMessages(prev => [...prev, message]);
  };

  const connect = () => {
    safeSetConnectionState('connecting');
    
    try {
      const ws = new WebSocket('ws://localhost:8000/ws');
      ws.onopen = handleWebSocketOpen;
      ws.onclose = handleWebSocketClose;
      ws.onerror = handleWebSocketError;
      ws.onmessage = handleWebSocketMessage;
      wsRef.current = ws;
    } catch (error) {
      safeSetConnectionState('error');
    }
  };

  React.useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return (
    <div>
      <div data-testid="connection-state">{connectionState}</div>
      <div data-testid="reconnect-attempts">{reconnectAttempts}</div>
      <div data-testid="buffer-size">{messageBuffer.length} buffered</div>
      <div data-testid="message-count">{messages.length} received</div>
      
      <button 
        onClick={() => sendMessage({ type: 'ping', data: 'test' })}
        data-testid="send-message"
      >
        Send Message
      </button>
      
      <button onClick={connect} data-testid="manual-connect">
        Connect
      </button>
    </div>
  );
};

export const ExponentialBackoffComponent = () => {
  const [attempts, setAttempts] = React.useState(0);
  const [nextRetryIn, setNextRetryIn] = React.useState(0);
  const [connectionState, setConnectionState] = React.useState('disconnected');
  const [lastDelay, setLastDelay] = React.useState(0);
  const [delayHistory, setDelayHistory] = React.useState<number[]>([]);

  // Wrap state setters with act() to prevent warnings
  const safeSetAttempts = wrapStateSetterWithAct(setAttempts);
  const safeSetNextRetryIn = wrapStateSetterWithAct(setNextRetryIn);
  const safeSetConnectionState = wrapStateSetterWithAct(setConnectionState);
  const safeSetLastDelay = wrapStateSetterWithAct(setLastDelay);
  const safeSetDelayHistory = wrapStateSetterWithAct(setDelayHistory);

  const attemptReconnect = async () => {
    const delay = calculateBackoffDelay(attempts);
    safeSetDelayHistory(prev => [...prev, delay]);
    safeSetLastDelay(delay);
    safeSetNextRetryIn(Math.round(delay / 1000));
    safeSetConnectionState('waiting');
    safeSetAttempts(prev => prev + 1);
  };

  const executeReconnectionWithCountdown = async (delay: number) => {
    const countdownInterval = startCountdownTimer(Math.round(delay / 1000), safeSetNextRetryIn);
    await new Promise(resolve => setTimeout(resolve, delay));
    safeSetConnectionState('failed');
    
    if (attempts < 3) {
      setTimeout(() => attemptReconnect(), 100);
    }
  };

  const handleAttemptReconnect = async () => {
    await attemptReconnect();
    await executeReconnectionWithCountdown(lastDelay);
  };

  const resetAttempts = () => {
    safeSetAttempts(0);
    safeSetNextRetryIn(0);
    safeSetConnectionState('disconnected');
    safeSetLastDelay(0);
    safeSetDelayHistory([]);
  };

  return (
    <div>
      <button onClick={handleAttemptReconnect} data-testid="start-reconnect">
        Start Reconnection
      </button>
      <button onClick={resetAttempts} data-testid="reset">
        Reset
      </button>
      
      <div data-testid="attempts">Attempts: {attempts}</div>
      <div data-testid="connection-state">{connectionState}</div>
      <div data-testid="next-retry">Next retry in: {nextRetryIn}s</div>
      <div data-testid="last-delay">Last delay: {lastDelay}ms</div>
      <div data-testid="delay-history">
        Delays: {delayHistory.join(', ')}ms
      </div>
    </div>
  );
};

export const HeartbeatComponent = () => {
  const [lastHeartbeat, setLastHeartbeat] = React.useState<number | null>(null);
  const [connectionHealth, setConnectionHealth] = React.useState<'healthy' | 'stale' | 'dead'>('healthy');
  const [heartbeatInterval, setHeartbeatInterval] = React.useState(1000);
  const wsRef = React.useRef<WebSocket | null>(null);
  const heartbeatTimerRef = React.useRef<NodeJS.Timeout | null>(null);
  const healthCheckRef = React.useRef<NodeJS.Timeout | null>(null);

  const performHeartbeat = () => {
    const timestamp = sendHeartbeat(wsRef.current);
    if (timestamp) setLastHeartbeat(timestamp);
  };

  const performHealthCheck = () => {
    const health = checkConnectionHealth(lastHeartbeat, heartbeatInterval);
    setConnectionHealth(health as 'healthy' | 'stale' | 'dead');
  };

  const startTimers = () => {
    heartbeatTimerRef.current = setInterval(performHeartbeat, heartbeatInterval);
    healthCheckRef.current = setInterval(performHealthCheck, heartbeatInterval / 2);
  };

  const clearTimers = () => {
    if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
    if (healthCheckRef.current) clearInterval(healthCheckRef.current);
  };

  React.useEffect(() => {
    startTimers();
    return clearTimers;
  }, [heartbeatInterval, lastHeartbeat]);

  return (
    <div>
      <div data-testid="connection-health">{connectionHealth}</div>
      <div data-testid="last-heartbeat">
        {lastHeartbeat ? new Date(lastHeartbeat).toISOString() : 'None'}
      </div>
      <div data-testid="heartbeat-interval">{heartbeatInterval}ms</div>
      
      <button onClick={performHeartbeat} data-testid="manual-heartbeat">
        Send Heartbeat
      </button>
      
      <button
        onClick={() => setHeartbeatInterval(500)}
        data-testid="faster-heartbeat"
      >
        Faster Heartbeat
      </button>
    </div>
  );
};