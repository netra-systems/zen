import { render, screen, fireEvent } from '@testing-library/react';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store';

jest.mock('@/hooks/useWebSocket');
jest.mock('@/store');

describe('MessageInput', () => {
  const sendMessage = jest.fn();
  const setProcessing = jest.fn();

  beforeEach(() => {
    (useWebSocket as jest.Mock).mockReturnValue({
      sendMessage,
    });
    (useChatStore as jest.Mock).mockReturnValue({
      setProcessing,
      isProcessing: false,
    });
  });

  it('should render the input field and send button', () => {
    render(<MessageInput />);
    expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('should update the input value on change', () => {
    render(<MessageInput />);
    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test message' } });
    expect(input.value).toBe('Test message');
  });

  it('should send a message when the send button is clicked', () => {
    render(<MessageInput />);
    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    expect(sendMessage).toHaveBeenCalledWith(JSON.stringify({ type: 'user_message', payload: { text: 'Test message' } }));
    expect(setProcessing).toHaveBeenCalledWith(true);
    expect(input.value).toBe('');
  });

  it('should send a message when Enter key is pressed', () => {
    render(<MessageInput />);
    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 13, charCode: 13 });

    expect(sendMessage).toHaveBeenCalledWith(JSON.stringify({ type: 'user_message', payload: { text: 'Test message' } }));
    expect(setProcessing).toHaveBeenCalledWith(true);
    expect(input.value).toBe('');
  });

  it('should disable input and button when processing', () => {
    (useChatStore as jest.Mock).mockReturnValue({
      setProcessing,
      isProcessing: true,
    });
    render(<MessageInput />);
    expect(screen.getByPlaceholderText('Agent is thinking...')).toBeDisabled();
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
  });
});