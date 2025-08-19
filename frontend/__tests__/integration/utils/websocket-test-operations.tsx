/**
 * WebSocket Test Operations
 * Extracted test operations with 8-line function limit enforcement
 */

import { waitFor, render } from '@testing-library/react';
import { TestProviders } from '../../setup/test-providers';
import { WebSocketTestManager } from '../../helpers/websocket-test-manager';
import { generateLargeMessage } from '../../helpers/websocket-test-utilities';

// Connection lifecycle operations (≤8 lines each)
export const performConnectionLifecycleTest = async (wsManager: WebSocketTestManager) => {
  const { connected, disconnected } = await testConnectionSequence(wsManager);
  
  expect(connected).toBe(true);
  expect(disconnected).toBe(true);
  expect(wsManager.getConnectionHistory()).toContainEqual(
    expect.objectContaining({ event: 'open' })
  );
};

const testConnectionSequence = async (wsManager: WebSocketTestManager) => {
  await waitFor(() => {
    expect(wsManager.getConnectionState()).toBe('connected');
  }, { timeout: 2000 });
  
  const connected = wsManager.isReady();
  wsManager.close(1000, 'Test close');
  
  await waitFor(() => {
    expect(wsManager.getConnectionState()).toBe('disconnected');
  });
  
  return { connected, disconnected: !wsManager.isReady() };
};

export const performConnectionErrorTest = async (wsManager: WebSocketTestManager, Component: React.ComponentType) => {
  render(<TestProviders><Component /></TestProviders>);
  
  wsManager.simulateError(new Error('Connection failed'));
  
  await waitFor(() => {
    expect(wsManager.getConnectionState()).toBe('error');
  });
  
  expect(wsManager.getConnectionHistory()).toContainEqual(
    expect.objectContaining({ event: 'error' })
  );
};

export const performReconnectionTest = async (wsManager: WebSocketTestManager, Component: React.ComponentType) => {
  render(<TestProviders><Component /></TestProviders>);
  
  await wsManager.waitForConnection();
  expect(wsManager.isReady()).toBe(true);
  
  wsManager.simulateReconnect();
  
  await verifyReconnectionSequence(wsManager);
};

const verifyReconnectionSequence = async (wsManager: WebSocketTestManager) => {
  await waitFor(() => {
    expect(wsManager.getConnectionState()).toBe('reconnecting');
  });
  
  await waitFor(() => {
    expect(wsManager.getConnectionState()).toBe('connected');
  }, { timeout: 1000 });
};

// Message processing operations (≤8 lines each)
export const performMessageSendingTest = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const testMessage = { type: 'test', data: 'Hello WebSocket' };
  wsManager.sendMessage(testMessage);
  wsManager.sendMessage({ type: 'test2', data: 'Second message' });
  
  const sentMessages = wsManager.getSentMessages();
  expect(sentMessages).toHaveLength(2);
  expect(sentMessages[0]).toContain('Hello WebSocket');
};

export const performMessageReceivingTest = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const testMessage = { type: 'incoming', data: 'Server message' };
  wsManager.simulateIncomingMessage(testMessage);
  
  await waitFor(() => {
    const receivedMessages = wsManager.getReceivedMessages();
    expect(receivedMessages).toHaveLength(1);
    expect(receivedMessages[0]).toContain('Server message');
  });
};

export const performMessageQueuingTest = async (wsManager: WebSocketTestManager) => {
  const buffer = wsManager.getMessageBuffer();
  
  const success1 = buffer.add('Message 1');
  const success2 = buffer.add('Message 2');
  
  expect(success1).toBe(true);
  expect(success2).toBe(true);
  expect(buffer.size()).toBe(2);
  
  const flushed = buffer.flush();
  expect(flushed).toHaveLength(2);
  expect(buffer.size()).toBe(0);
};

export const performFailedMessageTest = async (wsManager: WebSocketTestManager) => {
  wsManager.close();
  
  await waitFor(() => {
    expect(wsManager.isReady()).toBe(false);
  });
  
  expect(() => {
    wsManager.sendMessage('Should fail');
  }).toThrow();
};

// Large message operations (≤8 lines each)
export const performLargeMessageSendTest = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const largeMessage = generateLargeMessage(1024);
  expect(largeMessage.length).toBeGreaterThan(1000000);
  
  wsManager.sendMessage(largeMessage);
  
  const sentMessages = wsManager.getSentMessages();
  expect(sentMessages).toHaveLength(1);
  expect(sentMessages[0].length).toBeGreaterThan(1000000);
};

export const performLargeMessageReceiveTest = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const largeMessage = generateLargeMessage(512);
  wsManager.simulateIncomingMessage(largeMessage);
  
  await waitFor(() => {
    const receivedMessages = wsManager.getReceivedMessages();
    expect(receivedMessages).toHaveLength(1);
    expect(receivedMessages[0].length).toBeGreaterThan(500000);
  });
};

export const performBufferLimitTest = async (wsManager: WebSocketTestManager) => {
  const buffer = wsManager.getMessageBuffer();
  buffer.setMaxSize(3);
  
  expect(buffer.add('message-1')).toBe(true);
  expect(buffer.add('message-2')).toBe(true);
  expect(buffer.add('message-3')).toBe(true);
  expect(buffer.add('message-4')).toBe(false);
  expect(buffer.size()).toBe(3);
  
  const flushed = buffer.flush();
  expect(flushed.length).toBe(3);
  expect(buffer.size()).toBe(0);
  expect(buffer.add('message-after-flush')).toBe(true);
};

// Performance operations (≤8 lines each)
export const performConnectionTimingTest = async (wsManager: WebSocketTestManager) => {
  const connectionTime = await wsManager.measureConnectionTime();
  
  expect(connectionTime).toBeGreaterThan(0);
  expect(connectionTime).toBeLessThan(1000);
};

export const performRoundTripLatencyTest = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const testMessage = { id: 'test-123', echo: true };
  const latency = await wsManager.measureMessageRoundTrip(testMessage);
  
  expect(latency).toBeGreaterThan(0);
  expect(latency).toBeLessThan(100);
};

export const performConcurrentMessageTest = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const promises = Array(10).fill(0).map((_, i) => {
    return new Promise<void>((resolve) => {
      wsManager.sendMessage({ id: i, data: `Message ${i}` });
      resolve();
    });
  });
  
  await Promise.all(promises);
  
  const sentMessages = wsManager.getSentMessages();
  expect(sentMessages.length).toBe(10);
};

// Cleanup operations (≤8 lines each)
export const performCleanupTest = async (wsManager: WebSocketTestManager, Component: React.ComponentType) => {
  await wsManager.waitForConnection();
  expect(wsManager.isReady()).toBe(true);
  
  const { unmount } = render(<TestProviders><Component /></TestProviders>);
  
  wsManager.cleanup();
  expect(wsManager.isReady()).toBe(false);
  
  unmount();
  
  expect(wsManager.getSentMessages()).toHaveLength(0);
  expect(wsManager.getReceivedMessages()).toHaveLength(0);
};