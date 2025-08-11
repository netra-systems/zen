import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatWindow } from '@/components/chat/ChatWindow';

describe('ChatWindow', () => {
  it('renders input and send button', () => {
    const onSendMessage = jest.fn();
    render(<ChatWindow onSendMessage={onSendMessage} />);
    
    expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();
    expect(screen.getByText('Send')).toBeInTheDocument();
  });

  it('calls onSendMessage when send button is clicked', () => {
    const onSendMessage = jest.fn();
    render(<ChatWindow onSendMessage={onSendMessage} />);
    
    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByText('Send');
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);
    
    expect(onSendMessage).toHaveBeenCalledWith('Test message');
  });

  it('calls onSendMessage when Enter key is pressed', () => {
    const onSendMessage = jest.fn();
    render(<ChatWindow onSendMessage={onSendMessage} />);
    
    const input = screen.getByPlaceholderText('Type your message...');
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 13, charCode: 13 });
    
    expect(onSendMessage).toHaveBeenCalledWith('Test message');
  });

  it('clears input after sending message', () => {
    const onSendMessage = jest.fn();
    render(<ChatWindow onSendMessage={onSendMessage} />);
    
    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;
    const sendButton = screen.getByText('Send');
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);
    
    expect(input.value).toBe('');
  });

  it('does not send empty messages', () => {
    const onSendMessage = jest.fn();
    render(<ChatWindow onSendMessage={onSendMessage} />);
    
    const sendButton = screen.getByText('Send');
    
    fireEvent.click(sendButton);
    
    expect(onSendMessage).not.toHaveBeenCalled();
  });

  it('does not send messages with only whitespace', () => {
    const onSendMessage = jest.fn();
    render(<ChatWindow onSendMessage={onSendMessage} />);
    
    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByText('Send');
    
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(sendButton);
    
    expect(onSendMessage).not.toHaveBeenCalled();
  });
});