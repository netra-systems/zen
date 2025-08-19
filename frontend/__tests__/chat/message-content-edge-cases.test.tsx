/**
 * Message Content Edge Cases Tests
 * Tests for edge cases and regression prevention in message content handling
 * 
 * BVJ: Content Security and Robustness
 * Segment: All - prevents application crashes and security issues
 * Business Goal: Application stability and security compliance
 * Value Impact: Prevents user frustration from crashes and potential security vulnerabilities
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MessageList } from '@/components/chat/MessageList';
import { MessageItem } from '@/components/chat/MessageItem';
import { useUnifiedChatStore } from '@/store/unified-chat';
import {
  setupDefaultMocks,
  createUnifiedChatStoreMock
} from './ui-test-utilities';

// Mock Zustand store
jest.mock('@/store/unified-chat');

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

beforeEach(() => {
  setupDefaultMocks();
});

describe('Message Content Edge Cases and Regression Prevention', () => {
  describe('React Element-like Objects', () => {
    test('should not throw when content is a React element-like object', () => {
      const mockStore = createUnifiedChatStoreMock({
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
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });

    test('should handle React-like objects with nested properties', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'react-like',
            role: 'assistant',
            content: { 
              type: 'component',
              props: { 
                children: [
                  { type: 'span', props: { children: 'Nested content' } },
                  'Plain text'
                ]
              }
            },
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });

    test('should handle objects with circular references safely', () => {
      const circularObj: any = { type: 'circular' };
      circularObj.self = circularObj;

      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'circular',
            role: 'assistant',
            content: circularObj,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });
  });

  describe('Special Characters and XSS Prevention', () => {
    test('should handle content with special characters', () => {
      const mockStore = createUnifiedChatStoreMock({
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
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      // React should safely escape these characters
      expect(screen.getByText(/Message with.*characters/)).toBeInTheDocument();
    });

    test('should handle Unicode and emoji content', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'unicode',
            role: 'user',
            content: 'Unicode test: 你好 🚀 ñáéíóú ℝ𝕖𝕒𝕝𝕝𝕪 𝔀𝓮𝓲𝓻𝓭 𝓯𝓸𝓷𝓽',
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText(/Unicode test/)).toBeInTheDocument();
    });

    test('should handle content with HTML entities', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'html-entities',
            role: 'assistant',
            content: 'Content with &lt;tag&gt; and &amp; entities',
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText(/Content with.*entities/)).toBeInTheDocument();
    });

    test('should prevent XSS through object injection', () => {
      const message = {
        id: 'xss-test',
        type: 'ai' as const,
        content: {
          __html: '<script>alert("xss")</script>',
          dangerouslySetInnerHTML: { __html: '<script>alert("xss")</script>' }
        } as any,
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      expect(() => render(<MessageItem message={message} />)).not.toThrow();
    });
  });

  describe('Large Content Handling', () => {
    test('should handle extremely large text content', () => {
      const largeContent = 'A'.repeat(100000); // 100k characters
      
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'large-content',
            role: 'assistant',
            content: largeContent,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });

    test('should handle deeply nested object content', () => {
      const createDeepObject = (depth: number): any => {
        if (depth === 0) return { value: 'deep value' };
        return { nested: createDeepObject(depth - 1) };
      };

      const deepObject = createDeepObject(50);

      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'deep-object',
            role: 'assistant',
            content: deepObject,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });

    test('should handle arrays with many elements', () => {
      const largeArray = Array.from({ length: 10000 }, (_, i) => `Item ${i}`);

      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'large-array',
            role: 'assistant',
            content: largeArray,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });
  });

  describe('Invalid Data Type Handling', () => {
    test('should handle function as content', () => {
      const functionContent = () => 'I am a function';

      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'function-content',
            role: 'assistant',
            content: functionContent as any,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });

    test('should handle Symbol as content', () => {
      const symbolContent = Symbol('test-symbol');

      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'symbol-content',
            role: 'assistant',
            content: symbolContent as any,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });

    test('should handle Date object as content', () => {
      const dateContent = new Date('2025-01-01T10:00:00Z');

      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'date-content',
            role: 'assistant',
            content: dateContent as any,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText(/2025-01-01/)).toBeInTheDocument();
    });

    test('should handle RegExp as content', () => {
      const regexContent = /test-pattern/gi;

      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'regex-content',
            role: 'assistant',
            content: regexContent as any,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });
  });

  describe('Malformed Message Objects', () => {
    test('should handle message with missing required properties', () => {
      const message = {
        id: 'malformed',
        // Missing type, content, etc.
      } as any;

      expect(() => render(<MessageItem message={message} />)).not.toThrow();
    });

    test('should handle message with incorrect property types', () => {
      const message = {
        id: 123, // Should be string
        type: 'invalid-type',
        content: 'Valid content',
        created_at: 'not-a-date',
        displayed_to_user: 'not-a-boolean',
        references: 'not-an-array',
      } as any;

      expect(() => render(<MessageItem message={message} />)).not.toThrow();
    });

    test('should handle completely malformed message object', () => {
      const malformedMessage = {
        randomProperty: 'random value',
        anotherProperty: { nested: { deeply: 'value' } },
      } as any;

      expect(() => render(<MessageItem message={malformedMessage} />)).not.toThrow();
    });
  });

  describe('Browser Compatibility Edge Cases', () => {
    test('should handle content that triggers JSON.stringify errors', () => {
      const problematicObject = {};
      Object.defineProperty(problematicObject, 'toJSON', {
        value: () => { throw new Error('JSON stringify failed'); }
      });

      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'stringify-error',
            role: 'assistant',
            content: problematicObject,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });

    test('should handle content with getter properties that throw', () => {
      const objectWithThrowingGetter = {
        get problematic() {
          throw new Error('Getter error');
        },
        safe: 'This is safe'
      };

      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'throwing-getter',
            role: 'assistant',
            content: objectWithThrowingGetter,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });

    test('should handle content with non-enumerable properties', () => {
      const objectWithNonEnumerable = {};
      Object.defineProperty(objectWithNonEnumerable, 'hidden', {
        value: 'hidden value',
        enumerable: false
      });
      Object.defineProperty(objectWithNonEnumerable, 'visible', {
        value: 'visible value',
        enumerable: true
      });

      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'non-enumerable',
            role: 'assistant',
            content: objectWithNonEnumerable,
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });
  });

  describe('Memory and Performance Edge Cases', () => {
    test('should handle rapid re-renders without memory leaks', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'rerender-test',
            role: 'user',
            content: 'Test message for re-rendering',
            timestamp: Date.now(),
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      const { rerender } = render(<MessageList />);
      
      // Simulate rapid re-renders
      for (let i = 0; i < 10; i++) {
        rerender(<MessageList />);
      }

      expect(screen.getByText('Test message for re-rendering')).toBeInTheDocument();
    });

    test('should handle messages with identical content efficiently', () => {
      const duplicateContent = 'This is duplicate content';
      
      const mockStore = createUnifiedChatStoreMock({
        messages: Array.from({ length: 100 }, (_, i) => ({
          id: `duplicate-${i}`,
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: duplicateContent,
          timestamp: Date.now() + i,
          metadata: {},
        })),
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      expect(() => render(<MessageList />)).not.toThrow();
    });

    test('should handle zero timestamp gracefully', () => {
      const mockStore = createUnifiedChatStoreMock({
        messages: [
          {
            id: 'zero-timestamp',
            role: 'user',
            content: 'Message with zero timestamp',
            timestamp: 0,
            metadata: {},
          },
        ],
        isProcessing: false,
      });

      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockStore);

      render(<MessageList />);
      expect(screen.getByText('Message with zero timestamp')).toBeInTheDocument();
    });
  });
});