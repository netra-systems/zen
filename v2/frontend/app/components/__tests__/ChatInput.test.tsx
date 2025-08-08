
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '@/app/components/ChatInput';
import { examplePrompts } from '@/lib/examplePrompts';

// Mock the apiService
jest.mock('@/app/services/api', () => ({
  apiService: {
    getReferences: jest.fn().mockResolvedValue({ references: [] }),
    startAgent: jest.fn(),
  },
}));

// Mock the AuthContext
jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'test-user', email: 'test@example.com' },
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

// Mock the WebSocket hook
jest.mock('@/app/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: jest.fn(),
  }),
}));

describe('ChatInput', () => {
  it('should load an example prompt on initial render', () => {
    render(<ChatInput />);
    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;
    expect(examplePrompts).toContain(input.value);
  });

  it('should have a disabled submit button when the input is empty', () => {
    render(<ChatInput />);
    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '' } });
    const submitButton = screen.getByText('Submit');
    expect(submitButton).toBeDisabled();
  });
});
