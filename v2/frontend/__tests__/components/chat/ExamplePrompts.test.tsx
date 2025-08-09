
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';

// Mock the useWebSocket hook
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: jest.fn(),
  }),
}));

// Mock the useChatStore hook
jest.mock('@/store/chat', () => ({
  useChatStore: () => ({
    setProcessing: jest.fn(),
  }),
}));

describe('ExamplePrompts', () => {
  it('sends a message when an example prompt is clicked', () => {
    const { sendMessage } = useWebSocket();
    const { setProcessing } = useChatStore();
    render(<ExamplePrompts />);

    const firstPrompt = screen.getByText(/I need to reduce costs but keep quality the same/i);
    fireEvent.click(firstPrompt);

    expect(sendMessage).toHaveBeenCalledWith(
      JSON.stringify({ type: 'user_message', payload: { text: 'I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.' } })
    );
    expect(setProcessing).toHaveBeenCalledWith(true);
  });
});
