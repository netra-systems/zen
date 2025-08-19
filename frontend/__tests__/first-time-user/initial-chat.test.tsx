/**
 * Initial Chat Experience Tests - Business Critical for First-Time Users
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: Free → Early (Critical first impression and conversion funnel)
 * - Business Goal: Optimize first message success rate to prevent 20-30% user drop-off
 * - Value Impact: Each successful first chat = potential $1K+ ARR conversion
 * - Revenue Impact: 10% improvement in first chat success = $150K+ annually
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: First message sending, example prompts, welcome experience
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Test utilities and helpers
import { renderWithProviders, createMockMessage, expectNoErrors } from '../test-utils';
import {
  createMockStates,
  setupCleanTestState,
  resetTestMocks,
  getMessageInput,
  getFirstExamplePrompt,
  sendFirstMessage,
  clickExamplePrompt,
  verifyMessageSent,
  verifyProcessingState,
  verifyExamplePromptSent,
  verifyWelcomeDisplay,
  verifyExamplePromptsVisible,
  verifyQuickLoad,
  verifyAccessibilityFeatures,
  verifyUnauthenticatedState,
  verifyMarkdownRendering,
  verifyCodeBlockRendering
} from './initial-chat-helpers';

// Real components under test
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { MessageInput } from '@/components/chat/MessageInput';
import MainChat from '@/components/chat/MainChat';

// Initialize mock states
const mocks = createMockStates();

// Mock hooks with proper return types
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => mocks.webSocket)
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => mocks.chatStore)
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => mocks.authStore)
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(() => ({
    currentThreadId: 'thread-new-user',
    threads: []
  }))
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: jest.fn(() => ({
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: true,
    loadingMessage: 'Initializing...'
  }))
}));

describe('Initial Chat Experience Tests', () => {
  beforeEach(() => {
    setupCleanTestState(mocks);
    resetTestMocks(mocks);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('First Message Sending Experience', () => {
    it('allows new user to send first message via input field', async () => {
      const user = userEvent.setup();
      render(<MessageInput />);
      
      const messageInput = await getMessageInput();
      const testMessage = 'Hello, I need help optimizing my AI costs';
      
      await sendFirstMessage(user, messageInput, testMessage);
      await verifyMessageSent(mocks, testMessage);
    });

    it('shows proper loading feedback during first message processing', async () => {
      mocks.chatStore.isProcessing = true;
      render(<MessageInput />);
      
      const messageInput = await getMessageInput();
      await verifyProcessingState(messageInput);
    });

    it('handles authentication properly for first message', async () => {
      mocks.authStore.isAuthenticated = false;
      const user = userEvent.setup();
      render(<MessageInput />);
      
      const messageInput = await getMessageInput();
      await verifyUnauthenticatedState(user, messageInput, mocks);
    });
  });

  describe('Example Prompts Interaction', () => {
    it('allows clicking example prompts to send first message', async () => {
      const user = userEvent.setup();
      render(<ExamplePrompts />);
      
      const promptCard = await getFirstExamplePrompt();
      await clickExamplePrompt(user, promptCard);
      await verifyExamplePromptSent(mocks);
    });

    it('provides visual feedback when hovering over example prompts', async () => {
      const user = userEvent.setup();
      render(<ExamplePrompts />);
      
      const promptCard = await getFirstExamplePrompt();
      await user.hover(promptCard);
      
      const sendIcon = promptCard.querySelector('svg');
      expect(sendIcon).toBeVisible();
    });

    it('collapses example prompts after sending first message', async () => {
      const user = userEvent.setup();
      render(<ExamplePrompts />);
      
      const promptCard = await getFirstExamplePrompt();
      await clickExamplePrompt(user, promptCard);
      
      await waitFor(() => {
        const collapseButton = screen.getByText(/hide/i);
        expect(collapseButton).toBeInTheDocument();
      });
    });
  });

  describe('Welcome Message and First-Time Experience', () => {
    it('displays welcome experience for new users', async () => {
      renderWithProviders(<MainChat />);
      await verifyWelcomeDisplay();
    });

    it('shows example prompts prominently for new users', async () => {
      renderWithProviders(<MainChat />);
      await verifyExamplePromptsVisible();
    });

    it('provides clear value proposition in first interaction', async () => {
      renderWithProviders(<MainChat />);
      const valueText = screen.getByText(/ai-powered optimization/i);
      expect(valueText).toBeInTheDocument();
    });
  });

  describe('Message Formatting and Display', () => {
    it('handles markdown formatting in first message response', async () => {
      const markdownMessage = createMockMessage({
        content: '**Bold text** and `code snippet`',
        role: 'assistant'
      });
      
      mocks.chatStore.messages = [markdownMessage];
      renderWithProviders(<MainChat />);
      await verifyMarkdownRendering();
    });

    it('displays code blocks properly in chat interface', async () => {
      const codeMessage = createMockMessage({
        content: '```python\nprint("Hello World")\n```',
        role: 'assistant'
      });
      
      mocks.chatStore.messages = [codeMessage];
      renderWithProviders(<MainChat />);
      await verifyCodeBlockRendering();
    });
  });

  describe('Performance and Accessibility', () => {
    it('loads initial chat interface quickly for first impression', async () => {
      const startTime = performance.now();
      renderWithProviders(<MainChat />);
      const loadTime = performance.now() - startTime;
      
      verifyQuickLoad(loadTime);
      expectNoErrors();
    });

    it('provides accessible first-time user experience', async () => {
      renderWithProviders(<MainChat />);
      await verifyAccessibilityFeatures();
    });
  });
});