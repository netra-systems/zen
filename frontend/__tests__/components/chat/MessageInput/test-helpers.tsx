/**
 * MessageInput Test Helpers
 * Common operations for testing MessageInput component
 * BVJ: Reduces code duplication and ensures consistent test patterns
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';

// Helper to render component
export const renderMessageInput = () => {
  return render(<MessageInput />);
};

// Helper to get textarea
export const getTextarea = () => {
  return screen.getByRole('textbox', { name: /message input/i }) as HTMLTextAreaElement;
};

// Helper to get send button
export const getSendButton = () => {
  return screen.getByRole('button', { name: /send/i });
};

// Helper to type message
export const typeMessage = async (text: string) => {
  const textarea = getTextarea();
  await userEvent.type(textarea, text);
  return textarea;
};

// Helper to send message via Enter
export const sendViaEnter = async (text: string) => {
  const textarea = getTextarea();
  // Use fireEvent for more direct input control
  fireEvent.change(textarea, { target: { value: text } });
  fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
  return textarea;
};

// Helper to send message via button
export const sendViaButton = async (text: string) => {
  await typeMessage(text);
  const button = getSendButton();
  await userEvent.click(button);
  return button;
};

// Helper to check message was sent
export const expectMessageSent = async (mockSend: jest.Mock, content: string) => {
  await waitFor(() => {
    expect(mockSend).toHaveBeenCalledWith({
      message: content,
      activeThreadId: 'thread-1',
      currentThreadId: 'thread-1', 
      isAuthenticated: true
    });
  }, { timeout: 1000 });
};