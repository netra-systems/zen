import React from 'react';
import { render } from '@testing-library/react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { TestProviders } from '../../test-utils/providers';

// Mock dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useChatWebSocket', () => ({
  useChatWebSocket: jest.fn()
}));
jest.mock('@/components/chat/ChatHeader', () => ({
  ChatHeader: () => <div data-testid="chat-header">Chat Header</div>
}));
jest.mock('@/components/chat/MessageList', () => ({
  MessageList: () => <div data-testid="message-list">Message List</div>
}));
jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput: () => <div data-testid="message-input">Message Input</div>
}));
jest.mock('@/components/chat/PersistentResponseCard', () => ({
  PersistentResponseCard: ({ isCollapsed, onToggleCollapse }: any) => (
    <div data-testid="response-card" data-collapsed={isCollapsed}>
      <button onClick={onToggleCollapse}>Toggle</button>
      Response Card
    </div>
  )
}));
jest.mock('@/components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => <div data-testid="example-prompts">Example Prompts</div>
}));

// Mock store with all properties
export const mockStore = {
  isProcessing: false,
  messages: [],
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  currentRunId: null,
  addMessage: jest.fn(),
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  updateLayerData: jest.fn(),
};

// Common test setup function
export const setupMocks = () => {
  // Mock fetch for config
  global.fetch = jest.fn().mockResolvedValue({
    json: jest.fn().mockResolvedValue({
      ws_url: 'ws://localhost:8000/ws'
    })
  });

  jest.clearAllMocks();
  jest.useFakeTimers();
  (useUnifiedChatStore as jest.Mock).mockReturnValue(mockStore);
  const { useChatWebSocket } = require('@/hooks/useChatWebSocket');
  useChatWebSocket.mockReturnValue({
    connected: true,
    error: null
  });
};

// Common cleanup function
export const cleanupMocks = () => {
  jest.useRealTimers();
};