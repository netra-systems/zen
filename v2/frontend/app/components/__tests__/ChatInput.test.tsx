import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '../ChatInput';
import { examplePrompts } from '../../lib/examplePrompts';

// Mock the apiService
jest.mock('../../api', () => ({
  apiService: {
    getReferences: jest.fn().mockResolvedValue({ references: [] }),
    startAgent: jest.fn(),
  },
}));

// Mock the store
jest.mock('../../store', () => ({
    __esModule: true,
    default: jest.fn(() => ({
        token: 'test-token',
    })),
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