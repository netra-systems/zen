/**
 * Message Input Length Validation Tests
 * Tests for enforcing message length limits and user feedback
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock components for testing
const MockMessageInput: React.FC<{
  onSendMessage?: (message: string) => void;
  maxLength?: number;
  disabled?: boolean;
}> = ({ onSendMessage, maxLength = 2000, disabled = false }) => {
  const [message, setMessage] = React.useState('');
  const [error, setError] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Check for empty message first
    if (message.trim().length === 0) {
      setError('Message cannot be empty');
      return;
    }
    
    // Then check for length
    if (message.length > maxLength) {
      setError(`Message too long. Maximum ${maxLength} characters allowed.`);
      return;
    }
    
    // Clear error and send message
    setError('');
    onSendMessage?.(message);
    setMessage('');
  };

  // Show error when message exceeds limit and clear appropriate errors
  React.useEffect(() => {
    if (message.length > maxLength) {
      setError(`Message too long. Maximum ${maxLength} characters allowed.`);
    } else if (error && error.includes('Maximum') && message.length <= maxLength) {
      // Clear the length error when back within limits
      setError('');
    } else if (error === 'Message cannot be empty' && message.trim().length > 0) {
      // Clear empty message error when user starts typing
      setError('');
    }
  }, [message, maxLength, error]);

  return (
    <form onSubmit={handleSubmit} data-testid="message-form">
      <div>
        <textarea
          data-testid="message-input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Start typing your AI optimization request..."
          disabled={disabled}
          maxLength={maxLength + 100} // Allow typing beyond limit to show error
        />
        <div data-testid="character-count">
          {message.length}/{maxLength}
        </div>
        {error && (
          <div data-testid="error-message" role="alert">
            {error}
          </div>
        )}
      </div>
      <button 
        type="submit" 
        data-testid="send-button"
        disabled={disabled || message.length > maxLength}
      >
        Send
      </button>
    </form>
  );
};

describe('MessageInput - Length Validation', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  it('should enforce maximum message length limit', async () => {
    const mockSendMessage = jest.fn();
    const user = userEvent.setup();
    
    render(
      <MockMessageInput 
        onSendMessage={mockSendMessage} 
        maxLength={50}
      />
    );

    const messageInput = screen.getByTestId('message-input');
    const sendButton = screen.getByTestId('send-button');

    // Type a message that exceeds the limit
    const longMessage = 'This is a very long message that exceeds the fifty character limit for testing';
    
    await user.type(messageInput, longMessage);

    // Should show character count exceeding limit
    expect(screen.getByTestId('character-count')).toHaveTextContent('78/50');

    // Should show error message when trying to send
    await user.click(sendButton);

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toHaveTextContent(
        'Message too long. Maximum 50 characters allowed.'
      );
    });

    // Should not call the send message function
    expect(mockSendMessage).not.toHaveBeenCalled();

    // Send button should be disabled when message is too long
    expect(sendButton).toBeDisabled();
  });

  it('should allow sending messages within length limit', async () => {
    const mockSendMessage = jest.fn();
    const user = userEvent.setup();
    
    render(
      <MockMessageInput 
        onSendMessage={mockSendMessage} 
        maxLength={100}
      />
    );

    const messageInput = screen.getByTestId('message-input');
    const sendButton = screen.getByTestId('send-button');

    // Type a valid message
    const validMessage = 'This is a valid message within the limit';
    
    await user.type(messageInput, validMessage);

    // Should show character count within limit
    expect(screen.getByTestId('character-count')).toHaveTextContent('40/100');

    // Should not show error message
    expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();

    // Send button should be enabled
    expect(sendButton).toBeEnabled();

    // Should successfully send the message
    await user.click(sendButton);

    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith(validMessage);
    });

    // Should clear the input after sending
    expect(messageInput).toHaveValue('');
  });

  it('should prevent sending empty messages', async () => {
    const mockSendMessage = jest.fn();
    const user = userEvent.setup();
    
    render(<MockMessageInput onSendMessage={mockSendMessage} />);

    const sendButton = screen.getByTestId('send-button');

    // Try to send empty message by clicking the send button
    await user.click(sendButton);

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toHaveTextContent(
        'Message cannot be empty'
      );
    });

    expect(mockSendMessage).not.toHaveBeenCalled();
  });

  it('should clear error when user starts typing within limit', async () => {
    const user = userEvent.setup();
    
    render(<MockMessageInput maxLength={20} />);

    const messageInput = screen.getByTestId('message-input');
    const sendButton = screen.getByTestId('send-button');

    // Type a message that exceeds the limit
    await user.type(messageInput, 'This message is too long for the limit');

    // Try to send to trigger error
    await user.click(sendButton);

    // Should show error
    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });

    // Clear input and type a valid message
    await user.clear(messageInput);
    await user.type(messageInput, 'Valid message');

    // Error should be cleared
    await waitFor(() => {
      expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});