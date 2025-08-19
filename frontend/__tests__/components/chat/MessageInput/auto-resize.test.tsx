/**
 * MessageInput Auto-resize Tests
 * Tests for textarea auto-resize behavior
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import {
  mockSendMessage,
  setupMinimalMocks,
  resetMocks
} from './minimal-test-setup';
import {
  renderMessageInput,
  getTextarea,
  typeMessage,
  sendViaEnter
} from './test-helpers';

// Setup minimal mocks before imports
setupMinimalMocks();

describe('MessageInput - Auto-resize Textarea Behavior', () => {
  beforeEach(() => {
    resetMocks();
  });

  describe('Auto-resize textarea behavior', () => {
    const verifyTextareaStartsMinimal = () => {
      const textarea = getTextarea();
      expect(textarea.rows).toBeLessThanOrEqual(2);
    };

    it('should start with single row', () => {
      renderMessageInput();
      verifyTextareaStartsMinimal();
    });

    const setMultilineContent = (textarea: HTMLTextAreaElement, text: string) => {
      fireEvent.change(textarea, { target: { value: text } });
    };

    const verifyTextareaExpanded = async (textarea: HTMLTextAreaElement, content: string) => {
      await waitFor(() => {
        expect(textarea.value).toBe(content);
        expect(textarea.rows).toBeGreaterThan(1);
      });
    };

    it('should expand textarea as content grows', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      const multilineText = 'Line 1\nLine 2\nLine 3';
      setMultilineContent(textarea, multilineText);
      await verifyTextareaExpanded(textarea, multilineText);
    });

    const createManyLinesText = (count: number) => {
      return Array.from({ length: count }, (_, i) => `Line ${i}`).join('\n');
    };

    const verifyMaxRowsRespected = async (textarea: HTMLTextAreaElement) => {
      await waitFor(() => {
        expect(textarea.rows).toBeLessThanOrEqual(5);
      });
    };

    it('should respect maximum rows limit', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      const manyLines = createManyLinesText(10);
      setMultilineContent(textarea, manyLines);
      await verifyMaxRowsRespected(textarea);
    });

    it('should reset to single row after sending', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Set multiline content directly to ensure it works
      const multilineText = 'Line 1\nLine 2';
      fireEvent.change(textarea, { target: { value: multilineText } });
      
      await waitFor(() => {
        expect(textarea.rows).toBeGreaterThan(1);
        expect(textarea.value).toBe(multilineText);
      });
      
      // Send message by pressing Enter
      fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
      
      await waitFor(() => {
        expect(textarea.rows).toBe(1);
        expect(textarea.value).toBe('');
      });
    });

    it('should handle paste of multiline content', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      const multilineText = 'Line 1\nLine 2\nLine 3\nLine 4\nLine 5';
      
      // Simulate paste
      await userEvent.click(textarea);
      await userEvent.paste(multilineText);
      
      await waitFor(() => {
        expect(textarea.value).toBe(multilineText);
        expect(textarea.rows).toBeGreaterThan(1);
        expect(textarea.rows).toBeLessThanOrEqual(5); // MAX_ROWS
      });
    });

    it('should maintain scroll position during resize', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Type content
      await userEvent.type(textarea, 'First line');
      const initialScrollTop = textarea.scrollTop;
      
      // Add more content
      await userEvent.type(textarea, '{shift>}{enter}{/shift}');
      await userEvent.type(textarea, 'Second line');
      
      // Scroll position should be maintained
      expect(textarea.scrollTop).toBeGreaterThanOrEqual(initialScrollTop);
    });
  });
});