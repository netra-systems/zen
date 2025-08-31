
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { jest } from '@jest/globals';

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => React.createElement('div', props, children)
  },
  AnimatePresence: ({ children }) => children
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  ChevronDown: () => React.createElement('div', { 'data-testid': 'chevron-down' }),
  Send: () => React.createElement('div', { 'data-testid': 'send-icon' }),
  Sparkles: () => React.createElement('div', { 'data-testid': 'sparkles-icon' }),
  Zap: () => React.createElement('div', { 'data-testid': 'zap-icon' }),
  TrendingUp: () => React.createElement('div', { 'data-testid': 'trending-up-icon' }),
  Shield: () => React.createElement('div', { 'data-testid': 'shield-icon' }),
  Database: () => React.createElement('div', { 'data-testid': 'database-icon' }),
  Brain: () => React.createElement('div', { 'data-testid': 'brain-icon' })
}));

// Mock UI components
jest.mock('@/components/ui/card', () => ({
  Card: ({ children, ...props }) => React.createElement('div', { ...props, className: 'card' }, children),
  CardContent: ({ children, ...props }) => React.createElement('div', { ...props, className: 'card-content' }, children)
}));

jest.mock('@/components/ui/collapsible', () => ({
  Collapsible: ({ children, ...props }) => React.createElement('div', props, children),
  CollapsibleContent: ({ children, ...props }) => React.createElement('div', props, children),
  CollapsibleTrigger: ({ children, ...props }) => React.createElement('button', props, children)
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }) => React.createElement('button', props, children)
}));

// Mock external dependencies
jest.mock('@/lib/examplePrompts', () => ({
  examplePrompts: [
    "Help me reduce my AI costs by 30% while maintaining quality. I'm spending $5000/month on GPT-4 calls.",
    "My chatbot response time is too slow at 3 seconds. Can you optimize it to under 1 second without increasing costs?",
    "I'm launching a new feature next month that will 3x my API usage. How should I prepare my infrastructure?"
  ]
}));

jest.mock('@/lib/utils', () => ({
  generateUniqueId: jest.fn(() => 'test-id-123')
}));

jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn()
  }
}));

// Mock dependencies at the top level
const mockSendMessage = jest.fn();
const mockWebSocket = {
  sendMessage: mockSendMessage,
  connected: true,
  error: null,
  status: 'OPEN' as const,
  isConnected: true,
  connectionState: 'connected' as const,
};

const mockUnifiedChatStore = {
  isProcessing: false,
  messages: [],
  addMessage: jest.fn(),
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  activeThreadId: 'thread-1',
  setActiveThread: jest.fn(),
};

const mockAuthStore = {
  isAuthenticated: true,
  user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
  token: 'test-token-123',
  login: jest.fn(),
  logout: jest.fn(),
  loading: false,
};

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => mockWebSocket)
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => mockUnifiedChatStore)
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => mockAuthStore)
}));

import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

const resetMocks = () => {
  jest.clearAllMocks();
  mockUnifiedChatStore.isProcessing = false;
  mockAuthStore.isAuthenticated = true;
};

beforeEach(() => {
  resetMocks();
});

describe('ExamplePrompts', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  it('sends a message when an example prompt is clicked', () => {
    mockAuthStore.isAuthenticated = true;

    render(<ExamplePrompts />);

    const firstPrompt = screen.getByText(/Help me reduce my AI costs by 30% while maintaining quality/i);
    fireEvent.click(firstPrompt);

    expect(mockUnifiedChatStore.addMessage).toHaveBeenCalledWith(expect.objectContaining({
      role: 'user',
      content: 'I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.'
    }));
    expect(mockWebSocket.sendMessage).toHaveBeenCalledWith({
      type: 'user_message',
      payload: { 
        content: 'I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.',
        references: []
      }
    });
    expect(mockUnifiedChatStore.setProcessing).toHaveBeenCalledWith(true);
  });

  it('does not send message when user is not authenticated', () => {
    mockAuthStore.isAuthenticated = false;
    
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    
    render(<ExamplePrompts />);
    
    const firstPrompt = screen.getByText(/Help me reduce my AI costs by 30% while maintaining quality/i);
    fireEvent.click(firstPrompt);
    
    expect(consoleErrorSpy).toHaveBeenCalledWith('[ERROR]', 'User must be authenticated to send messages');
    expect(mockUnifiedChatStore.addMessage).not.toHaveBeenCalled();
    expect(mockWebSocket.sendMessage).not.toHaveBeenCalled();
    expect(mockUnifiedChatStore.setProcessing).not.toHaveBeenCalled();
    
    consoleErrorSpy.mockRestore();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});
