/**
 * Message Input Validation Test - Iteration 5
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';

// Mock component that simulates message input with character limits
const MessageInputWithValidation: React.FC = () => {
  const [message, setMessage] = React.useState('');
  const MAX_LENGTH = 500;
  const isOverLimit = message.length > MAX_LENGTH;

  return (
    <div>
      <textarea
        data-testid="message-textarea"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        maxLength={MAX_LENGTH * 2} // Allow typing beyond limit for testing
        placeholder="Start typing your AI optimization request..."
      />
      <div data-testid="char-count" style={{ color: isOverLimit ? 'red' : 'gray' }}>
        {message.length}/{MAX_LENGTH}
      </div>
      <button 
        data-testid="send-button"
        disabled={isOverLimit || message.trim().length === 0}
      >
        Send
      </button>
      {isOverLimit && (
        <div data-testid="error-message" style={{ color: 'red' }}>
          Message exceeds maximum length
        </div>
      )}
    </div>
  );
};

describe('Message Input Validation', () => {
  it('should show character count', async () => {
    const user = userEvent.setup();
    render(<MessageInputWithValidation />);
    
    const textarea = screen.getByTestId('message-textarea');
    const charCount = screen.getByTestId('char-count');
    
    await user.type(textarea, 'Hello world!');
    
    expect(charCount).toHaveTextContent('12/500');
  });

  it('should disable send button when message exceeds limit', async () => {
    render(<MessageInputWithValidation />);
    
    const textarea = screen.getByTestId('message-textarea');
    const sendButton = screen.getByTestId('send-button');
    
    // Directly set value instead of typing to avoid timeout
    const longMessage = 'A'.repeat(501);
    React.act(() => {
      textarea.focus();
      // Simulate direct value setting as if user pasted content
      Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')!.set!.call(textarea, longMessage);
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    
    expect(sendButton).toBeDisabled();
    expect(screen.getByTestId('error-message')).toBeInTheDocument();
    
    // Fixed: Should be red when over limit (using computed RGB value)
    expect(screen.getByTestId('char-count')).toHaveStyle('color: rgb(255, 0, 0)');
  });
});