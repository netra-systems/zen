import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useTextareaResize } from '@/components/chat/hooks/useTextareaResize';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { useMessageSending } from '@/components/chat/hooks/useMessageSending';
import { useMessageHistory } from '@/components/chat/hooks/useMessageHistory';
import {
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
chat/hooks/useMessageHistory', () => ({
  useMessageHistory: jest.fn()
}));

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useTextareaResize } from '@/components/chat/hooks/useTextareaResize';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { useMessageSending } from '@/components/chat/hooks/useMessageSending';
import { useMessageHistory } from '@/components/chat/hooks/useMessageHistory';
import {
  renderMessageInput,
  getTextarea,
  typeMessage,
  sendViaEnter
} from './test-helpers';

// Get the mocked functions
const mockUseTextareaResize = useTextareaResize as jest.Mock;
const mockUseWebSocket = useWebSocket as jest.Mock;
const mockUseUnifiedChatStore = useUnifiedChatStore as jest.Mock;
const mockUseThreadStore = useThreadStore as jest.Mock;
const mockUseAuthStore = useAuthStore as jest.Mock;
const mockUseMessageSending = useMessageSending as jest.Mock;
const mockUseMessageHistory = useMessageHistory as jest.Mock;

describe('MessageInput - Auto-resize Textarea Behavior', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup the textarea resize mock with dynamic behavior
    mockUseTextareaResize.mockImplementation((textareaRef: any, message: string) => {
      const lineCount = message ? message.split('\n').length : 1;
      const rows = Math.min(Math.max(lineCount, 1), 5);
      return { rows };
    });
    
    // Setup other mocks
    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
    });
    
    mockUseUnifiedChatStore.mockReturnValue({
      activeThreadId: 'thread-1',
      isProcessing: false,
      setProcessing: jest.fn(),
      addMessage: jest.fn(),
      addOptimisticMessage: jest.fn(),
      updateOptimisticMessage: jest.fn(),
    });
    
    mockUseThreadStore.mockReturnValue({
      currentThreadId: 'thread-1',
      setCurrentThread: jest.fn(),
      addThread: jest.fn(),
    });
    
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
    });
    
    mockUseMessageSending.mockReturnValue({
      isSending: false,
      error: null,
      isTimeout: false,
      retryCount: 0,
      isCircuitOpen: false,
      handleSend: jest.fn().mockResolvedValue(undefined),
      retry: jest.fn(),
      reset: jest.fn()
    });
    
    mockUseMessageHistory.mockReturnValue({
      messageHistory: [],
      addToHistory: jest.fn(),
      navigateHistory: jest.fn(() => '')
    });
  });

  describe('Auto-resize textarea behavior', () => {
      jest.setTimeout(10000);
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

    const verifyTextareaReset = async (textarea: HTMLTextAreaElement) => {
      await waitFor(() => {
        expect(textarea.rows).toBe(1);
        expect(textarea.value).toBe('');
      });
    };

    it('should reset to single row after sending', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      const multilineText = 'Line 1\nLine 2';
      setMultilineContent(textarea, multilineText);
      await verifyTextareaExpanded(textarea, multilineText);
      fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
      await verifyTextareaReset(textarea);
    });

    const pasteMultilineContent = async (textarea: HTMLTextAreaElement, text: string) => {
      await userEvent.click(textarea);
      await userEvent.paste(text);
    };

    const verifyPastedContent = async (textarea: HTMLTextAreaElement, text: string) => {
      await waitFor(() => {
        expect(textarea.value).toBe(text);
        expect(textarea.rows).toBeGreaterThan(1);
        expect(textarea.rows).toBeLessThanOrEqual(5);
      });
    };

    it('should handle paste of multiline content', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      const multilineText = 'Line 1\nLine 2\nLine 3\nLine 4\nLine 5';
      await pasteMultilineContent(textarea, multilineText);
      await verifyPastedContent(textarea, multilineText);
    });

    const typeInitialContent = async (textarea: HTMLTextAreaElement) => {
      await userEvent.type(textarea, 'First line');
      return textarea.scrollTop;
    };

    const addMoreContent = async (textarea: HTMLTextAreaElement) => {
      await userEvent.type(textarea, '{shift>}{enter}{/shift}');
      await userEvent.type(textarea, 'Second line');
    };

    it('should maintain scroll position during resize', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      const initialScrollTop = await typeInitialContent(textarea);
      await addMoreContent(textarea);
      expect(textarea.scrollTop).toBeGreaterThanOrEqual(initialScrollTop);
    });
  });
});