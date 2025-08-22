/**
 * WebSocket Helper Functions for Integration Tests
 * Provides common WebSocket testing utilities and message helpers
 */

import WS from 'jest-websocket-mock';
import { act } from '@testing-library/react';

/**
 * Creates a WebSocket event handler wrapper that properly wraps state updates in act()
 * This prevents React act() warnings in tests when WebSocket event handlers update component state
 * 
 * @example
 * // Instead of:
 * ws.onopen = () => setConnected(true);
 * 
 * // Use:
 * ws.onopen = createActWrapper(() => setConnected(true));
 * 
 * // For handlers with parameters:
 * ws.onmessage = createActWrapper((event) => {
 *   const data = JSON.parse(event.data);
 *   setMessage(data.content);
 * });
 */
export function createActWrapper<T extends (...args: any[]) => void>(callback: T): T {
  return ((...args: any[]) => {
    act(() => {
      callback(...args);
    });
  }) as T;
}

export async function waitForConnection(server: WS): Promise<void> {
  await expect(server).toReceiveMessage(expect.any(Object));
}

export function sendMessage(server: WS, content: string, threadId: string = 'test-thread'): void {
  server.send(JSON.stringify({
    type: 'message',
    data: {
      id: Date.now().toString(),
      content,
      role: 'user',
      threadId,
      timestamp: new Date().toISOString()
    }
  }));
}

export function sendStreamChunk(server: WS, chunk: string, messageId: string = `msg-${Date.now()}`, threadId: string = 'test-thread'): void {
  server.send(JSON.stringify({
    type: 'stream_chunk',
    data: {
      messageId,
      chunk,
      threadId,
      timestamp: new Date().toISOString()
    }
  }));
}

export function sendAgentStart(server: WS, agentType: string, threadId: string = 'test-thread'): void {
  server.send(JSON.stringify({
    type: 'agent_start',
    data: {
      agentType,
      threadId,
      agentId: `agent-${Date.now()}`,
      timestamp: new Date().toISOString()
    }
  }));
}

export function sendAgentMessage(server: WS, content: string, agentType: string, threadId: string = 'test-thread'): void {
  server.send(JSON.stringify({
    type: 'agent_message',
    data: {
      id: Date.now().toString(),
      content,
      role: 'assistant',
      agentType,
      threadId,
      timestamp: new Date().toISOString()
    }
  }));
}

export function sendAgentComplete(server: WS, agentType: string, threadId: string = 'test-thread'): void {
  server.send(JSON.stringify({
    type: 'agent_complete',
    data: {
      agentType,
      threadId,
      status: 'completed',
      timestamp: new Date().toISOString()
    }
  }));
}

export function sendError(server: WS, error: string, threadId: string = 'test-thread'): void {
  server.send(JSON.stringify({
    type: 'error',
    data: {
      error,
      threadId,
      timestamp: new Date().toISOString()
    }
  }));
}

export function sendSystemMessage(server: WS, message: string, threadId: string = 'test-thread'): void {
  server.send(JSON.stringify({
    type: 'system_message',
    data: {
      message,
      threadId,
      timestamp: new Date().toISOString()
    }
  }));
}

export async function waitForMessage(server: WS, expectedType?: string): Promise<any> {
  const message = await server.nextMessage;
  if (expectedType) {
    const parsed = typeof message === 'string' ? JSON.parse(message) : message;
    expect(parsed.type).toBe(expectedType);
    return parsed;
  }
  return message;
}

export function createWebSocketMessage(type: string, data: any): string {
  return JSON.stringify({
    type,
    data: {
      ...data,
      timestamp: new Date().toISOString()
    }
  });
}

export async function expectWebSocketMessage(server: WS, expectedMessage: any): Promise<void> {
  await expect(server).toReceiveMessage(expectedMessage);
}

export function simulateConnection(server: WS): void {
  // Simulate initial connection message
  server.send(JSON.stringify({
    type: 'connection_established',
    data: {
      status: 'connected',
      timestamp: new Date().toISOString()
    }
  }));
}

export function simulateDisconnection(server: WS): void {
  server.close();
}

export async function waitForDisconnection(server: WS): Promise<void> {
  // Wait for close event
  await new Promise(resolve => {
    server.on('close', resolve);
  });
}