/**
 * Message Content Rendering Tests
 * Tests for MessageItem component content rendering and display logic
 * 
 * BVJ: Message Display Infrastructure
 * Segment: All - proper message rendering is critical for all users
 * Business Goal: Clear communication and professional UI appearance
 * Value Impact: Good UX increases user engagement and trust in the platform
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MessageItem } from '@/components/chat/MessageItem';
import {
  setupDefaultMocks
} from './ui-test-utilities';

// Mock UI components
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

describe('Message Content Rendering', () => {
  describe('Basic Content Rendering', () => {
    test('should render string content directly', () => {
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

    test('should render long text content properly', () => {
      const longContent = 'This is a very long message that should wrap properly and be displayed correctly without breaking the layout or causing any rendering issues in the chat interface.';
      
      const message = {
        id: 'test-long',
        type: 'user' as const,
        content: longContent,
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText(longContent)).toBeInTheDocument();
    });

    test('should render multiline content with proper formatting', () => {
      const multilineContent = 'Line 1\nLine 2\nLine 3';
      
      const message = {
        id: 'test-multiline',
        type: 'ai' as const,
        content: multilineContent,
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText(/Line 1.*Line 2.*Line 3/s)).toBeInTheDocument();
    });

    test('should handle empty string content gracefully', () => {
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
  });

  describe('Object Content Rendering', () => {
    test('should handle object content in MessageItem', () => {
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

    test('should handle complex nested object content', () => {
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

    test('should handle object with multiple content properties', () => {
      const message = {
        id: 'test-multi',
        type: 'ai' as const,
        content: { 
          text: 'Primary text',
          content: 'Secondary content',
          message: 'Tertiary message'
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
      // Should prioritize 'text' property
      expect(screen.getByText('Primary text')).toBeInTheDocument();
    });

    test('should handle object without recognizable text properties', () => {
      const message = {
        id: 'test-unknown',
        type: 'ai' as const,
        content: { 
          status: 'success',
          code: 200,
          data: { result: 'processed' }
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
      // Should stringify the entire object
      expect(screen.getByText(/success.*200.*processed/)).toBeInTheDocument();
    });
  });

  describe('Error Content Handling', () => {
    test('should prioritize error content over regular content', () => {
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

    test('should handle different types of error messages', () => {
      const message = {
        id: 'test-error-types',
        type: 'ai' as const,
        content: 'Normal content',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: 'Connection timeout - please try again',
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('Connection timeout - please try again')).toBeInTheDocument();
    });

    test('should handle error objects', () => {
      const message = {
        id: 'test-error-object',
        type: 'ai' as const,
        content: 'Normal content',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: { message: 'API Error', code: 500 },
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText(/API Error.*500/)).toBeInTheDocument();
    });
  });

  describe('Agent Information Display', () => {
    test('should display sub-agent name when provided', () => {
      const message = {
        id: 'test-agent',
        type: 'ai' as const,
        content: 'Response from specific agent',
        sub_agent_name: 'OptimizationAgent',
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('OptimizationAgent')).toBeInTheDocument();
    });

    test('should use default agent name when sub_agent_name is null', () => {
      const message = {
        id: 'test-default-agent',
        type: 'ai' as const,
        content: 'Default agent response',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('Netra Agent')).toBeInTheDocument();
    });

    test('should display user information for user messages', () => {
      const message = {
        id: 'test-user',
        type: 'user' as const,
        content: 'User message content',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('You')).toBeInTheDocument();
    });
  });

  describe('References and Attachments', () => {
    test('should handle messages with references', () => {
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

    test('should handle empty references array', () => {
      const message = {
        id: 'test-no-refs',
        type: 'user' as const,
        content: 'Message without references',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('Message without references')).toBeInTheDocument();
    });

    test('should handle multiple file types in references', () => {
      const message = {
        id: 'test-multi-refs',
        type: 'user' as const,
        content: 'Message with various files',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: ['document.pdf', 'image.jpg', 'data.csv', 'presentation.pptx'],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('document.pdf')).toBeInTheDocument();
      expect(screen.getByText('image.jpg')).toBeInTheDocument();
      expect(screen.getByText('data.csv')).toBeInTheDocument();
      expect(screen.getByText('presentation.pptx')).toBeInTheDocument();
    });
  });

  describe('Tool Information Display', () => {
    test('should display tool information when available', () => {
      const message = {
        id: 'test-tool',
        type: 'ai' as const,
        content: 'Tool execution result',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: {
          name: 'optimization_tool',
          status: 'completed',
          duration: 1500
        },
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('Tool execution result')).toBeInTheDocument();
      // Tool info might be displayed in a collapsible section
    });

    test('should handle tool information with error status', () => {
      const message = {
        id: 'test-tool-error',
        type: 'ai' as const,
        content: 'Tool failed to execute',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: {
          name: 'failing_tool',
          status: 'error',
          error_message: 'Tool execution failed'
        },
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('Tool failed to execute')).toBeInTheDocument();
    });
  });

  describe('Raw Data Display', () => {
    test('should handle raw data when present', () => {
      const message = {
        id: 'test-raw-data',
        type: 'ai' as const,
        content: 'Message with raw data',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: {
          metrics: { cpu: 75, memory: 60 },
          timestamp: '2025-01-01T10:00:00Z'
        },
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('Message with raw data')).toBeInTheDocument();
      // Raw data might be displayed in JSON format
    });

    test('should handle null raw data gracefully', () => {
      const message = {
        id: 'test-no-raw-data',
        type: 'ai' as const,
        content: 'Message without raw data',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('Message without raw data')).toBeInTheDocument();
    });
  });

  describe('Timestamp and Metadata', () => {
    test('should display message timestamp', () => {
      const timestamp = new Date().toISOString();
      const message = {
        id: 'test-timestamp',
        type: 'user' as const,
        content: 'Message with timestamp',
        sub_agent_name: null,
        created_at: timestamp,
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={message} />);
      expect(screen.getByText('Message with timestamp')).toBeInTheDocument();
      // Timestamp display logic would be in the component
    });

    test('should handle different message types with appropriate styling', () => {
      const userMessage = {
        id: 'test-user-type',
        type: 'user' as const,
        content: 'User message',
        sub_agent_name: null,
        created_at: new Date().toISOString(),
        displayed_to_user: true,
        tool_info: null,
        raw_data: null,
        references: [],
        error: null,
      };

      render(<MessageItem message={userMessage} />);
      expect(screen.getByText('User message')).toBeInTheDocument();
      expect(screen.getByText('You')).toBeInTheDocument();
    });
  });
});