import React from 'react';
import { render, screen } from '@testing-library/react';
import { MessageList } from '@/components/chat/MessageList';
import { MessageItem } from '@/components/chat/MessageItem';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock Zustand store
jest.mock('@/store/unified-chat');

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock UI components
jest.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, ...props }: any) => <div {...props}>{children}</div>,
}));

jest.mock('@/components/ui/card', () => ({
  Card: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  CardContent: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  CardHeader: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  CardTitle: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
}));

jest.mock('@/components/ui/avatar', () => ({
  Avatar: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  AvatarFallback: ({ children, ...props }: any) => <div {...props}>{children}</div>,
}));

jest.mock('@/components/ui/collapsible', () => ({
  Collapsible: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  CollapsibleContent: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  CollapsibleTrigger: ({ children, ...props }: any) => <button {...props}>{children}</button>,
}));

jest.mock('@/components/chat/ThinkingIndicator', () => ({
  ThinkingIndicator: () => <div>Thinking...</div>,
}));

jest.mock('@/components/chat/RawJsonView', () => ({
  RawJsonView: ({ data }: any) => <pre>{JSON.stringify(data, null, 2)}</pre>,
}));

jest.mock('@/components/chat/MCPToolIndicator', () => ({
  MCPToolIndicator: () => <div>MCP Tool</div>,
}));

describe('Message Content Handling', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('MessageList Content Normalization', () => {
      jest.setTimeout(10000);
    it('should handle string content correctly', () => {
      const mockStore = {
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
      };

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText('Hello, this is a string message')).toBeInTheDocument();
    });

    it('should handle object content with text property', () => {
      const mockStore = {
        messages: [
          {
            id: '2',
            role: 'assistant',
            content: { type: 'text', text: 'This is an object message' },
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      };

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText('This is an object message')).toBeInTheDocument();
    });

    it('should handle object content without text property', () => {
      const mockStore = {
        messages: [
          {
            id: '3',
            role: 'assistant',
            content: { type: 'custom', data: 'some data' },
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      };

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      // Should stringify the object when no text property exists
      expect(screen.getByText(/{"type":"custom","data":"some data"}/)).toBeInTheDocument();
    });

    it('should handle null/undefined content gracefully', () => {
      const mockStore = {
        messages: [
          {
            id: '4',
            role: 'user',
            content: null,
            timestamp: Date.now(),
            metadata: {},
          },
          {
            id: '5',
            role: 'assistant',
            content: undefined,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      };

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      const { container } = render(<MessageList />);
      expect(container).toBeInTheDocument();
      // Should not crash and should render something
    });

    it('should handle array content by stringifying', () => {
      const mockStore = {
        messages: [
          {
            id: '6',
            role: 'assistant',
            content: ['item1', 'item2', 'item3'],
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      };

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText(/\["item1","item2","item3"\]/)).toBeInTheDocument();
    });
  });

  describe('MessageItem Content Rendering', () => {
      jest.setTimeout(10000);
    it('should render string content directly', () => {
      const message = {
        id: 'test-1',
        type: 'user' as const,
        content: 'This is a test message',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('This is a test message')).toBeInTheDocument();
    });

    it('should handle object content in MessageItem', () => {
      const message = {
        id: 'test-2',
        type: 'ai' as const,
        content: { type: 'text', text: 'AI response text' } as any,
        sub_agent_name: 'TestAgent',
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('AI response text')).toBeInTheDocument();
    });

    it('should handle complex nested object content', () => {
      const message = {
        id: 'test-3',
        type: 'ai' as const,
        content: { 
          type: 'complex',
          nested: { deep: { value: 'test' } }
        } as any,
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      // Should stringify complex objects
      expect(screen.getByText(/{"type":"complex","nested":{"deep":{"value":"test"}}}/)).toBeInTheDocument();
    });

    it('should prioritize error content over regular content', () => {
      const message = {
        id: 'test-4',
        type: 'ai' as const,
        content: 'Regular content',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: 'An error occurred',
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('An error occurred')).toBeInTheDocument();
      expect(screen.queryByText('Regular content')).not.toBeInTheDocument();
    });

    it('should handle messages with references', () => {
      const message = {
        id: 'test-5',
        type: 'user' as const,
        content: 'Message with references',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: ['ref1.txt', 'ref2.pdf'],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('Message with references')).toBeInTheDocument();
      expect(screen.getByText('ref1.txt')).toBeInTheDocument();
      expect(screen.getByText('ref2.pdf')).toBeInTheDocument();
    });
  });

  describe('Edge Cases and Regression Prevention', () => {
      jest.setTimeout(10000);
    it('should not throw when content is a React element-like object', () => {
      const mockStore = {
        messages: [
          {
            id: '7',
            role: 'assistant',
            content: { 
              type: 'div',
              props: { children: 'This looks like a React element' }
            },
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      };

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });

    it('should handle mixed content types in message list', () => {
      const mockStore = {
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
            timestamp: Date.now(),
            metadata: { agentName: 'TestAgent' },
          },
          {
            id: 'mixed-3',
            role: 'system',
            content: { customProp: 'value' },
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      };

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      const { container } = render(<MessageList />);
      expect(container).toBeInTheDocument();
      expect(screen.getByText('String message')).toBeInTheDocument();
      expect(screen.getByText('Object message')).toBeInTheDocument();
    });

    it('should handle empty string content', () => {
      const message = {
        id: 'test-empty',
        type: 'ai' as const,
        content: '',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('Netra Agent')).toBeInTheDocument(); // Should still render the header
    });

    it('should handle content with special characters', () => {
      const mockStore = {
        messages: [
          {
            id: 'special-chars',
            role: 'user',
            content: 'Message with <script>alert("xss")</script> and & < > " \' characters',
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      };

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      // React should safely escape these characters
      expect(screen.getByText(/Message with.*characters/)).toBeInTheDocument();
    });
  });
});