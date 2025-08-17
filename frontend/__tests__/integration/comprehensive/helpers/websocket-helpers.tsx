/**
 * WebSocket Helper Functions
 * All functions ≤8 lines for modular architecture compliance
 */

export const sendMessageOrBuffer = (ws: WebSocket | null, message: any, messageBuffer: any[]) => {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
    return true;
  } else {
    messageBuffer.push({ ...message, timestamp: Date.now() });
    return false;
  }
};

export const flushMessageBuffer = (ws: WebSocket, messageBuffer: any[]) => {
  const messagesToFlush = [...messageBuffer];
  messageBuffer.length = 0;
  messagesToFlush.forEach(bufferedMessage => {
    ws.send(JSON.stringify(bufferedMessage));
  });
};

export const calculateBackoffDelay = (attemptNumber: number) => {
  const baseDelay = 100;
  const maxDelay = 5000;
  const exponentialDelay = baseDelay * Math.pow(2, attemptNumber);
  const cappedDelay = Math.min(exponentialDelay, maxDelay);
  const jitteredDelay = cappedDelay + (Math.random() * 1000);
  return Math.round(jitteredDelay);
};

export const createHeartbeatMessage = () => ({
  type: 'heartbeat',
  timestamp: Date.now()
});

export const sendHeartbeat = (ws: WebSocket | null) => {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(createHeartbeatMessage()));
    return Date.now();
  }
  return null;
};

export const checkConnectionHealth = (lastHeartbeat: number | null, heartbeatInterval: number) => {
  const now = Date.now();
  if (!lastHeartbeat) return 'healthy';
  
  const timeSinceLastHeartbeat = now - lastHeartbeat;
  if (timeSinceLastHeartbeat > heartbeatInterval * 3) return 'dead';
  if (timeSinceLastHeartbeat > heartbeatInterval * 2) return 'stale';
  return 'healthy';
};

export const setupReconnectionTimer = (attempts: number, maxAttempts: number, connectFn: () => void) => {
  if (attempts >= maxAttempts) return;
  
  const delay = 1000 * Math.pow(2, attempts);
  setTimeout(() => {
    connectFn();
  }, delay);
};

export const startCountdownTimer = (
  initialSeconds: number, 
  setNextRetryIn: (value: number | ((prev: number) => number)) => void
) => {
  const interval = setInterval(() => {
    setNextRetryIn(prev => {
      if (prev <= 1) {
        clearInterval(interval);
        return 0;
      }
      return prev - 1;
    });
  }, 1000);
  return interval;
};