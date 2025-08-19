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
    setupCleanState();
    resetAllMocks();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('First Message Sending Experience', () => {
    it('allows new user to send first message via input field', async () => {
      const user = userEvent.setup();
      renderMessageInput();
      
      const messageInput = await getMessageInput();
      const testMessage = 'Hello, I need help optimizing my AI costs';
      
      await sendFirstMessage(user, messageInput, testMessage);
      await verifyMessageSent(testMessage);
    });

    it('shows proper loading feedback during first message processing', async () => {
      const user = userEvent.setup();
      mockChatStore.isProcessing = true;
      
      renderMessageInput();
      const messageInput = await getMessageInput();
      
      await verifyProcessingState(messageInput);
    });

    it('handles authentication properly for first message', async () => {
      mockAuthStore.isAuthenticated = false;
      const user = userEvent.setup();
      
      renderMessageInput();
      const messageInput = await getMessageInput();
      
      await verifyUnauthenticatedState(user, messageInput);
    });
  });

  describe('Example Prompts Interaction', () => {
    it('allows clicking example prompts to send first message', async () => {
      const user = userEvent.setup();
      renderExamplePrompts();
      
      const promptCard = await getFirstExamplePrompt();
      await clickExamplePrompt(user, promptCard);
      
      await verifyExamplePromptSent();
    });

    it('provides visual feedback when hovering over example prompts', async () => {
      const user = userEvent.setup();
      renderExamplePrompts();
      
      const promptCard = await getFirstExamplePrompt();
      await verifyPromptHoverEffects(user, promptCard);
    });

    it('collapses example prompts after sending first message', async () => {
      const user = userEvent.setup();
      renderExamplePrompts();
      
      const promptCard = await getFirstExamplePrompt();
      await clickExamplePrompt(user, promptCard);
      
      await verifyPromptsCollapsed();
    });
  });

  describe('Welcome Message and First-Time Experience', () => {
    it('displays welcome experience for new users', async () => {
      renderMainChat();
      await verifyWelcomeDisplay();
    });

    it('shows example prompts prominently for new users', async () => {
      renderMainChat();
      await verifyExamplePromptsVisible();
    });

    it('provides clear value proposition in first interaction', async () => {
      renderMainChat();
      await verifyValueProposition();
    });
  });

  describe('Message Formatting and Display', () => {
    it('handles markdown formatting in first message response', async () => {
      const markdownMessage = createMockMessage({
        content: '**Bold text** and `code snippet`',
        role: 'assistant'
      });
      
      mockChatStore.messages = [markdownMessage];
      renderMainChat();
      
      await verifyMarkdownRendering();
    });

    it('displays code blocks properly in chat interface', async () => {
      const codeMessage = createMockMessage({
        content: '```python\nprint("Hello World")\n```',
        role: 'assistant'
      });
      
      mockChatStore.messages = [codeMessage];
      renderMainChat();
      
      await verifyCodeBlockRendering();
    });
  });

  describe('Performance and Accessibility', () => {
    it('loads initial chat interface quickly for first impression', async () => {
      const startTime = performance.now();
      renderMainChat();
      const loadTime = performance.now() - startTime;
      
      verifyQuickLoad(loadTime);
      expectNoErrors();
    });

    it('provides accessible first-time user experience', async () => {
      renderMainChat();
      await verifyAccessibilityFeatures();
    });
  });

  // Helper Functions (≤8 lines each)
  function setupCleanState(): void {
    mockChatStore.isProcessing = false;
    mockChatStore.messages = [];
    mockAuthStore.isAuthenticated = true;
    mockAuthStore.user = mockAuthenticatedUser;
    localStorage.clear();
    sessionStorage.clear();
  }

  function resetAllMocks(): void {
    mockWebSocket.sendMessage.mockClear();
    mockChatStore.addMessage.mockClear();
    mockChatStore.setProcessing.mockClear();
    mockAuthStore.login.mockClear();
    mockAuthStore.logout.mockClear();
  }

  function renderMessageInput(): void {
    render(<MessageInput />);
  }

  function renderExamplePrompts(): void {
    render(<ExamplePrompts />);
  }

  function renderMainChat(): void {
    renderWithProviders(<MainChat />);
  }

  async function getMessageInput(): Promise<HTMLElement> {
    return await waitFor(() => 
      screen.getByRole('textbox', { name: /message input/i })
    );
  }

  async function sendFirstMessage(
    user: any, 
    input: HTMLElement, 
    message: string
  ): Promise<void> {
    await user.type(input, message);
    await user.keyboard('{Enter}');
  }

  async function verifyMessageSent(message: string): Promise<void> {
    await waitFor(() => {
      expect(mockChatStore.addMessage).toHaveBeenCalledWith(
        expect.objectContaining({ content: message, role: 'user' })
      );
    });
  }

  async function verifyProcessingState(input: HTMLElement): Promise<void> {
    expect(input).toBeDisabled();
    expect(screen.getByText(/processing/i)).toBeInTheDocument();
  }

  async function verifyUnauthenticatedState(
    user: any, 
    input: HTMLElement
  ): Promise<void> {
    await user.type(input, 'test message');
    await user.keyboard('{Enter}');
    expect(mockChatStore.addMessage).not.toHaveBeenCalled();
  }

  async function getFirstExamplePrompt(): Promise<HTMLElement> {
    return await waitFor(() => 
      screen.getByText(/I need to reduce costs but keep quality the same/i)
    );
  }

  async function clickExamplePrompt(
    user: any, 
    prompt: HTMLElement
  ): Promise<void> {
    await user.click(prompt);
  }

  async function verifyExamplePromptSent(): Promise<void> {
    await waitFor(() => {
      expect(mockWebSocket.sendMessage).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'user_message' })
      );
    });
  }

  async function verifyPromptHoverEffects(
    user: any, 
    prompt: HTMLElement
  ): Promise<void> {
    await user.hover(prompt);
    const sendIcon = screen.getByTestId('send-icon') || prompt.querySelector('svg');
    expect(sendIcon).toBeVisible();
  }

  async function verifyPromptsCollapsed(): Promise<void> {
    await waitFor(() => {
      const collapseButton = screen.getByText(/hide/i);
      expect(collapseButton).toBeInTheDocument();
    });
  }

  async function verifyWelcomeDisplay(): Promise<void> {
    const welcomeText = await screen.findByText(/welcome to netra ai/i);
    expect(welcomeText).toBeInTheDocument();
    expect(welcomeText).toBeVisible();
  }

  async function verifyExamplePromptsVisible(): Promise<void> {
    const promptsHeader = await screen.findByText(/quick start examples/i);
    expect(promptsHeader).toBeInTheDocument();
    expect(promptsHeader).toBeVisible();
  }

  async function verifyValueProposition(): Promise<void> {
    const valueText = screen.getByText(/ai-powered optimization/i);
    expect(valueText).toBeInTheDocument();
  }

  async function verifyMarkdownRendering(): Promise<void> {
    const boldText = await screen.findByText(/bold text/i);
    const codeText = await screen.findByText(/code snippet/i);
    expect(boldText).toBeInTheDocument();
    expect(codeText).toBeInTheDocument();
  }

  async function verifyCodeBlockRendering(): Promise<void> {
    const codeBlock = await screen.findByText(/print\("hello world"\)/i);
    expect(codeBlock).toBeInTheDocument();
  }

  function verifyQuickLoad(loadTime: number): void {
    expect(loadTime).toBeLessThan(1000); // Should load under 1 second
  }

  async function verifyAccessibilityFeatures(): Promise<void> {
    const mainContent = screen.getByRole('main') || document.body;
    const interactiveElements = mainContent.querySelectorAll('button, input, a');
    
    interactiveElements.forEach(element => {
      expect(element).toHaveAttribute('tabindex');
    });
  }
});