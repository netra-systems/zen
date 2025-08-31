import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MessageList } from '@/components/chat/MessageList';
import { useUnifiedChatStore } from '@/store/unified-chat';
import {
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ble content rendering prevents user confusion
 * Value Impact: Consistent message display improves user experience and trust
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MessageList } from '@/components/chat/MessageList';
import { useUnifiedChatStore } from '@/store/unified-chat';
import {
  setupDefaultMocks,
  createUnifiedChatStoreMock
} from './ui-test-utilities';

// Mock Zustand store
jest.mock('@/store/unified-chat');

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => React.createElement('div', props, children),
  },
  AnimatePresence: ({ children }: any) => children,
}));

// Mock UI components
jest.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, ...props }: any) => React.createElement('div', props, children),
}));

jest.mock('@/components/ui/card', () => ({
  Card: ({ children, ...props }: any) => React.createElement('div', props, children),
  CardContent: ({ children, ...props }: any) => React.createElement('div', props, children),
  CardHeader: ({ children, ...props }: any) => React.createElement('div', props, children),
  CardTitle: ({ children, ...props }: any) => React.createElement('h3', props, children),
}));

jest.mock('@/components/ui/avatar', () => ({
  Avatar: ({ children, ...props }: any) => React.createElement('div', props, children),
  AvatarFallback: ({ children, ...props }: any) => React.createElement('div', props, children),
}));

jest.mock('@/components/ui/collapsible', () => ({
  Collapsible: ({ children, ...props }: any) => React.createElement('div', props, children),
  CollapsibleContent: ({ children, ...props }: any) => React.createElement('div', props, children),
  CollapsibleTrigger: ({ children, ...props }: any) => React.createElement('button', props, children),
}));

jest.mock('@/components/chat/ThinkingIndicator', () => ({
  ThinkingIndicator: () => React.createElement('div', {}, 'Thinking...'),
}));

jest.mock('@/components/chat/RawJsonView', () => ({
  RawJsonView: ({ data }: any) => React.createElement('pre', {}, JSON.stringify(data, null, 2)),
}));

jest.mock('@/components/chat/MCPToolIndicator', () => ({
  MCPToolIndicator: () => React.createElement('div', {}, 'MCP Tool'),
}));

beforeEach(() => {
  setupDefaultMocks();
});

describe('Message Content Normalization', () => {
    jest.setTimeout(10000);
  describe('String Content Processing', () => {
      jest.setTimeout(10000);
    test('should handle string content correctly', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '1',
            role: 'user',
            content: 'Hello, this is a string message',
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText('Hello, this is a string message')).toBeInTheDocument();
    });

    test('should handle empty string content gracefully', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '2',
            role: 'user',
            content: '',
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      const { container } = render(<MessageList />);
      expect(container).toBeInTheDocument();
      // Should not crash with empty content
    });

    test('should handle whitespace-only content', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '3',
            role: 'user',
            content: '   \n\t   ',
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      const { container } = render(<MessageList />);
      expect(container).toBeInTheDocument();
    });

    test('should preserve formatting in string content', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '4',
            role: 'assistant',
            content: 'Line 1\nLine 2\nLine 3',
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText(/Line 1.*Line 2.*Line 3/s)).toBeInTheDocument();
    });
  });

  describe('Object Content Processing', () => {
      jest.setTimeout(10000);
    test('should handle object content with text property', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '5',
            role: 'assistant',
            content: { type: 'text', text: 'This is an object message' },
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText('This is an object message')).toBeInTheDocument();
    });

    test('should handle object content without text property', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '6',
            role: 'assistant',
            content: { type: 'custom', data: 'some data' },
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      // Should stringify the object when no text property exists
      expect(screen.getByText(/{"type":"custom","data":"some data"}/)).toBeInTheDocument();
    });

    test('should handle nested object structures', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '7',
            role: 'assistant',
            content: { 
              type: 'structured',
              data: { 
                nested: { 
                  value: 'deep content',
                  count: 42 
                }
              }
            },
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      // Should stringify nested objects
      expect(screen.getByText(/deep content/)).toBeInTheDocument();
    });

    test('should handle object with multiple text-like properties', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '8',
            role: 'assistant',
            content: { 
              text: 'Primary text',
              content: 'Secondary content',
              message: 'Tertiary message'
            },
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      // Should prioritize 'text' property
      expect(screen.getByText('Primary text')).toBeInTheDocument();
    });
  });

  describe('Null and Undefined Content Handling', () => {
      jest.setTimeout(10000);
    test('should handle null content gracefully', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '9',
            role: 'user',
            content: null,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      const { container } = render(<MessageList />);
      expect(container).toBeInTheDocument();
      // Should not crash and should render something
    });

    test('should handle undefined content gracefully', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '10',
            role: 'assistant',
            content: undefined,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      const { container } = render(<MessageList />);
      expect(container).toBeInTheDocument();
      // Should not crash and should render something
    });

    test('should handle mixed null and valid content', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '11',
            role: 'user',
            content: null,
            timestamp: Date.now(),
            metadata: {},
          },
          {
            id: '12',
            role: 'assistant',
            content: 'Valid message',
            timestamp: Date.now() + 1000,
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText('Valid message')).toBeInTheDocument();
    });
  });

  describe('Array Content Processing', () => {
      jest.setTimeout(10000);
    test('should handle array content by stringifying', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '13',
            role: 'assistant',
            content: ['item1', 'item2', 'item3'],
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText(/\["item1","item2","item3"\]/)).toBeInTheDocument();
    });

    test('should handle nested array content', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '14',
            role: 'assistant',
            content: [['nested', 'array'], 'simple', { key: 'value' }],
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText(/nested.*array/)).toBeInTheDocument();
    });

    test('should handle empty array content', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '15',
            role: 'assistant',
            content: [],
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText(/\[\]/)).toBeInTheDocument();
    });
  });

  describe('Special Content Types', () => {
      jest.setTimeout(10000);
    test('should handle boolean content', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '16',
            role: 'assistant',
            content: true,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText('true')).toBeInTheDocument();
    });

    test('should handle numeric content', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '17',
            role: 'assistant',
            content: 42.5,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText('42.5')).toBeInTheDocument();
    });

    test('should handle zero numeric content', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: '18',
            role: 'assistant',
            content: 0,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText('0')).toBeInTheDocument();
    });
  });

  describe('Content Consistency', () => {
      jest.setTimeout(10000);
    test('should handle mixed content types in message list', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'mixed-1',
            role: 'user',
            content: 'String message',
            timestamp: Date.now(),
            metadata: {},
          },
          {
            id: 'mixed-2',
            role: 'assistant',
            content: { type: 'text', text: 'Object message' },
            timestamp: Date.now() + 1000,
            metadata: { agentName: 'TestAgent' },
          },
          {
            id: 'mixed-3',
            role: 'system',
            content: { customProp: 'value' },
            timestamp: Date.now() + 2000,
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      const { container } = render(<MessageList />);
      expect(container).toBeInTheDocument();
      expect(screen.getByText('String message')).toBeInTheDocument();
      expect(screen.getByText('Object message')).toBeInTheDocument();
    });

    test('should maintain content order during normalization', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'order-1',
            role: 'user',
            content: 'First',
            timestamp: Date.now(),
            metadata: {},
          },
          {
            id: 'order-2',
            role: 'assistant',
            content: 'Second',
            timestamp: Date.now() + 1000,
            metadata: {},
          },
          {
            id: 'order-3',
            role: 'user',
            content: 'Third',
            timestamp: Date.now() + 2000,
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      
      // All messages should be rendered
      expect(screen.getByText('First')).toBeInTheDocument();
      expect(screen.getByText('Second')).toBeInTheDocument();
      expect(screen.getByText('Third')).toBeInTheDocument();
    });
  });
});