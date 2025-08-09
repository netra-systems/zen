import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';

const mockSendMessage = jest.fn();

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ sendMessage: mockSendMessage }),
}));

jest.mock('@/store/chat');

describe('MessageInput', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render the input field and send button', () => {
    (useChatStore as jest.Mock).mockReturnValue({ isProcessing: false });
    render(<MessageInput />);
    expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('should update the input value on change', () => {
    (useChatStore as jest.Mock).mockReturnValue({ isProcessing: false });
    render(<MessageInput />);
    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test message' } });
    expect(input.value).toBe('Test message');
  });

  it('should send a message when the send button is clicked', () => {
    const setProcessing = jest.fn();
    (useChatStore as jest.Mock).mockReturnValue({ isProcessing: false, setProcessing });
    render(<MessageInput />);
    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    expect(mockSendMessage).toHaveBeenCalledWith(JSON.stringify({ type: 'user_message', payload: { text: 'Test message' } }));
    expect(setProcessing).toHaveBeenCalledWith(true);
    expect(input.value).toBe('');
  });

  it('should send a message when Enter key is pressed', () => {
    const setProcessing = jest.fn();
    (useChatStore as jest.Mock).mockReturnValue({ isProcessing: false, setProcessing });
    render(<MessageInput />);
    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 });

    expect(mockSendMessage).toHaveBeenCalledWith(JSON.stringify({ type: 'user_message', payload: { text: 'Test message' } }));
    expect(setProcessing).toHaveBeenCalledWith(true);
    expect(input.value).toBe('');
  });

  it('should disable input and button when processing', () => {
    (useChatStore as jest.Mock).mockReturnValue({ isProcessing: true });
    render(<MessageInput />);
    expect(screen.getByPlaceholderText('Agent is thinking...')).toBeDisabled();
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
  });
});