/**
 * WebSocket Test Helpers
 * Common WebSocket utilities for integration tests
 */

import { act } from '@testing-library/react';
import WS from 'jest-websocket-mock';

export const waitForConnection = async (server: WS): Promise<void> => {
  await server.connected;
};

export const sendMessage = (server: WS, message: string): void => {
  act(() => {
    server.send(message);
  });
};

export const sendStreamChunk = (server: WS, chunk: string): void => {
  const message = JSON.stringify({ type: 'stream_chunk', chunk });
  sendMessage(server, message);
};

export const sendAgentStart = (server: WS): void => {
  sendMessage(server, JSON.stringify({ type: 'agent_started' }));
};

export const sendAgentMessage = (server: WS, content: string): void => {
  const message = JSON.stringify({ type: 'agent_message', content });
  sendMessage(server, message);
};

export const sendAgentComplete = (server: WS): void => {
  sendMessage(server, JSON.stringify({ type: 'agent_completed' }));
};

export const closeConnection = (server: WS): void => {
  act(() => {
    server.close();
  });
};