/**
 * Async Operation Handling Utilities
 * WebSocket and API operations with 8-line function limit enforcement
 */

import { waitFor, act } from '@testing-library/react';
import WS from 'jest-websocket-mock';

// Types for async operations
export interface AsyncOperationConfig {
  timeout?: number;
  retryCount?: number;
  retryDelay?: number;
  expectSuccess?: boolean;
}

export interface WebSocketOperationConfig extends AsyncOperationConfig {
  messageDelay?: number;
  reconnectOnFailure?: boolean;
  batchSize?: number;
}

export interface APIOperationConfig extends AsyncOperationConfig {
  endpoint?: string;
  method?: string;
  expectedStatus?: number;
}

// WebSocket async operation handlers
export const handleWebSocketConnection = async (server: WS, config: WebSocketOperationConfig = {}) => {
  const timeout = config.timeout || 2000;
  
  await waitFor(() => {
    expect(server).toHaveReceivedMessages([]);
  }, { timeout });
  
  return { connected: true, timestamp: Date.now() };
};

export const handleWebSocketMessage = async (server: WS, message: any, config: WebSocketOperationConfig = {}) => {
  const delay = config.messageDelay || 0;
  
  if (delay > 0) {
    await new Promise(resolve => setTimeout(resolve, delay));
  }
  
  await act(async () => {
    server.send(JSON.stringify(message));
  });
  
  return { sent: true, message, timestamp: Date.now() };
};

export const handleWebSocketBatch = async (server: WS, messages: any[], config: WebSocketOperationConfig = {}) => {
  const batchSize = config.batchSize || messages.length;
  const results = [];
  
  for (let i = 0; i < messages.length; i += batchSize) {
    const batch = messages.slice(i, i + batchSize);
    const batchResults = await sendMessageBatch(server, batch, config);
    results.push(...batchResults);
  }
  
  return results;
};

const sendMessageBatch = async (server: WS, batch: any[], config: WebSocketOperationConfig) => {
  const promises = batch.map(message => handleWebSocketMessage(server, message, config));
  return Promise.all(promises);
};

export const handleWebSocketReconnect = async (server: WS, config: WebSocketOperationConfig = {}) => {
  const retryDelay = config.retryDelay || 100;
  
  await act(async () => {
    server.close();
  });
  
  await new Promise(resolve => setTimeout(resolve, retryDelay));
  
  return handleWebSocketConnection(server, config);
};

export const handleWebSocketError = async (server: WS, error: Error) => {
  await act(async () => {
    server.error(error);
  });
  
  return { error: true, message: error.message, timestamp: Date.now() };
};

// API async operation handlers
export const handleAPIRequest = async (config: APIOperationConfig = {}) => {
  const endpoint = config.endpoint || '/api/test';
  const method = config.method || 'GET';
  const timeout = config.timeout || 5000;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(endpoint, { method, signal: controller.signal });
    clearTimeout(timeoutId);
    return { success: true, status: response.status, data: await response.json() };
  } catch (error) {
    clearTimeout(timeoutId);
    return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
};

export const handleAPIRetry = async (config: APIOperationConfig = {}) => {
  const retryCount = config.retryCount || 3;
  const retryDelay = config.retryDelay || 1000;
  
  for (let attempt = 0; attempt < retryCount; attempt++) {
    const result = await handleAPIRequest(config);
    
    if (result.success) {
      return { ...result, attempt: attempt + 1 };
    }
    
    if (attempt < retryCount - 1) {
      await new Promise(resolve => setTimeout(resolve, retryDelay * Math.pow(2, attempt)));
    }
  }
  
  return { success: false, error: 'Max retries exceeded', attempts: retryCount };
};

export const handleConcurrentAPIRequests = async (requests: APIOperationConfig[], config: AsyncOperationConfig = {}) => {
  const timeout = config.timeout || 10000;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const promises = requests.map(reqConfig => handleAPIRequest({ ...reqConfig, timeout }));
    const results = await Promise.allSettled(promises);
    clearTimeout(timeoutId);
    return results.map(result => result.status === 'fulfilled' ? result.value : { success: false, error: 'Promise rejected' });
  } catch (error) {
    clearTimeout(timeoutId);
    return requests.map(() => ({ success: false, error: 'Batch operation failed' }));
  }
};

// File upload async operation handlers
export const handleFileUpload = async (file: File, config: APIOperationConfig = {}) => {
  const endpoint = config.endpoint || '/api/upload';
  const timeout = config.timeout || 30000;
  
  const formData = new FormData();
  formData.append('file', file);
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      body: formData,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return { success: true, status: response.status, data: await response.json() };
  } catch (error) {
    clearTimeout(timeoutId);
    return { success: false, error: error instanceof Error ? error.message : 'Upload failed' };
  }
};

export const handleStreamingOperation = async (stream: ReadableStream, config: AsyncOperationConfig = {}) => {
  const timeout = config.timeout || 60000;
  const chunks: any[] = [];
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const reader = stream.getReader();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }
    
    clearTimeout(timeoutId);
    return { success: true, chunks, totalChunks: chunks.length };
  } catch (error) {
    clearTimeout(timeoutId);
    return { success: false, error: error instanceof Error ? error.message : 'Stream failed' };
  }
};

// Performance measurement utilities
export const measureAsyncOperation = async <T>(operation: () => Promise<T>, label: string = 'operation'): Promise<{ result: T; duration: number; label: string }> => {
  const start = performance.now();
  const result = await operation();
  const duration = performance.now() - start;
  
  return { result, duration, label };
};

export const measureConcurrentOperations = async <T>(operations: (() => Promise<T>)[], labels: string[] = []): Promise<{ results: T[]; durations: number[]; totalDuration: number }> => {
  const start = performance.now();
  
  const promises = operations.map((op, index) => measureAsyncOperation(op, labels[index] || `operation-${index}`));
  const measurements = await Promise.all(promises);
  
  const totalDuration = performance.now() - start;
  
  return {
    results: measurements.map(m => m.result),
    durations: measurements.map(m => m.duration),
    totalDuration
  };
};