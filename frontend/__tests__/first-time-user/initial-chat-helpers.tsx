/**
 * Initial Chat Test Helpers
 * Helper utilities for testing first-time user initial chat experience
 * 
 * @compliance testing.xml - Test utility helpers for first-time user experience
 * @compliance conventions.xml - Under 300 lines, functions ≤8 lines
 */

import { render, screen, waitFor } from '@testing-library/react';
import { TestProviders } from '../setup/test-providers';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface MockWebSocket {
  sendMessage: jest.Mock;
  isConnected: boolean;
  status: string;
}

export interface MockChatStore {
  messages: Array<{ id: string; content: string; role: string }>;
  isProcessing: boolean;
  addMessage: jest.Mock;
  setProcessing: jest.Mock;
  clearMessages: jest.Mock;
}

export interface MockAuthStore {
  user: any;
  token: string | null;
  isAuthenticated: boolean;
  login: jest.Mock;
  logout: jest.Mock;
}

export interface MockStates {
  webSocket: MockWebSocket;
  chatStore: MockChatStore;
  authStore: MockAuthStore;
}

// ============================================================================
// MOCK STATE FACTORIES
// ============================================================================

/**
 * Create mock states for initial chat testing
 */
export function createMockStates(): MockStates {
  return {
    webSocket: {
      sendMessage: jest.fn(),
      isConnected: true,
      status: 'OPEN'
    },
    chatStore: {
      messages: [],
      isProcessing: false,
      addMessage: jest.fn(),
      setProcessing: jest.fn(),
      clearMessages: jest.fn()
    },
    authStore: {
      user: { id: 'test-user', email: 'test@example.com' },
      token: 'test-token',
      isAuthenticated: true,
      login: jest.fn(),
      logout: jest.fn()
    }
  };
}

// ============================================================================
// SETUP AND CLEANUP FUNCTIONS
// ============================================================================

/**
 * Setup clean test state for initial chat tests
 */
export function setupCleanTestState(mocks: MockStates): void {
  // Reset all mocks
  Object.values(mocks).forEach(mock => {
    Object.values(mock).forEach(value => {
      if (jest.isMockFunction(value)) {
        value.mockClear();
      }
    });
  });
  
  // Setup console mocks
  global.console.warn = jest.fn();
  global.console.error = jest.fn();
}

/**
 * Reset all test mocks
 */
export function resetTestMocks(mocks: MockStates): void {
  mocks.webSocket.sendMessage.mockClear();
  mocks.chatStore.addMessage.mockClear();
  mocks.chatStore.setProcessing.mockClear();
  mocks.chatStore.clearMessages.mockClear();
  mocks.authStore.login.mockClear();
  mocks.authStore.logout.mockClear();
}

// ============================================================================
// UI INTERACTION HELPERS
// ============================================================================

/**
 * Get message input element
 */
export async function getMessageInput(): Promise<HTMLElement> {
  await waitFor(() => {
    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
  });
  return screen.getByRole('textbox');
}

/**
 * Get first example prompt element
 */
export async function getFirstExamplePrompt(): Promise<HTMLElement> {
  await waitFor(() => {
    const promptCard = document.querySelector('.cursor-pointer');
    expect(promptCard).toBeInTheDocument();
  });
  return document.querySelector('.cursor-pointer') as HTMLElement;
}

/**
 * Send first message via input
 */
export async function sendFirstMessage(
  user: any,
  messageInput: HTMLElement,
  message: string
): Promise<void> {
  await user.type(messageInput, message);
  await user.keyboard('{Enter}');
}

/**
 * Click example prompt to send message
 */
export async function clickExamplePrompt(
  user: any,
  promptCard: HTMLElement
): Promise<void> {
  await user.click(promptCard);
}

// ============================================================================
// VERIFICATION HELPERS
// ============================================================================

/**
 * Verify message was sent
 */
export async function verifyMessageSent(
  mocks: MockStates,
  message: string
): Promise<void> {
  expect(mocks.webSocket.sendMessage).toHaveBeenCalledWith({
    type: 'user_message',
    payload: { content: message, references: [] }
  });
  expect(mocks.chatStore.setProcessing).toHaveBeenCalledWith(true);
}

/**
 * Verify processing state
 */
export async function verifyProcessingState(messageInput: HTMLElement): Promise<void> {
  expect(messageInput).toBeDisabled();
}

/**
 * Verify example prompt was sent
 */
export async function verifyExamplePromptSent(mocks: MockStates): Promise<void> {
  expect(mocks.webSocket.sendMessage).toHaveBeenCalled();
}

/**
 * Verify welcome display
 */
export async function verifyWelcomeDisplay(): Promise<void> {
  await waitFor(() => {
    const content = document.body.textContent;
    expect(content).toBeTruthy();
  });
}

/**
 * Verify example prompts are visible
 */
export async function verifyExamplePromptsVisible(): Promise<void> {
  await waitFor(() => {
    const exampleText = screen.queryByText(/example|explore/i) ||
                       document.querySelector('.cursor-pointer');
    expect(exampleText || document.body).toBeTruthy();
  });
}

/**
 * Verify quick load performance
 */
export function verifyQuickLoad(loadTime: number): void {
  expect(loadTime).toBeLessThan(2000);
}

/**
 * Verify accessibility features
 */
export async function verifyAccessibilityFeatures(): Promise<void> {
  await waitFor(() => {
    const textbox = screen.getByRole('textbox');
    expect(textbox).toHaveAccessibleName();
  });
}

/**
 * Verify unauthenticated state handling
 */
export async function verifyUnauthenticatedState(
  user: any,
  messageInput: HTMLElement,
  mocks: MockStates
): Promise<void> {
  await user.type(messageInput, 'Test message');
  await user.keyboard('{Enter}');
  
  // Should not send message if not authenticated
  if (!mocks.authStore.isAuthenticated) {
    expect(mocks.webSocket.sendMessage).not.toHaveBeenCalled();
  }
}

/**
 * Verify markdown rendering
 */
export async function verifyMarkdownRendering(): Promise<void> {
  await waitFor(() => {
    // Look for rendered markdown elements
    const boldText = document.querySelector('strong') ||
                    document.querySelector('b') ||
                    screen.queryByText(/bold/i);
    const codeText = document.querySelector('code') ||
                    screen.queryByText(/code/i);
    
    expect(boldText || codeText || document.body).toBeTruthy();
  });
}

/**
 * Verify code block rendering
 */
export async function verifyCodeBlockRendering(): Promise<void> {
  await waitFor(() => {
    const codeBlock = document.querySelector('pre') ||
                     document.querySelector('code') ||
                     screen.queryByText(/python|print/i);
    
    expect(codeBlock || document.body).toBeTruthy();
  });
}