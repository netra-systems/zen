
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';

const mockSendMessage = jest.fn();
const mockSetProcessing = jest.fn();

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ sendMessage: mockSendMessage }),
}));

jest.mock('@/store/chat', () => ({
  useChatStore: () => ({ setProcessing: mockSetProcessing }),
}));

describe('ExamplePrompts', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('sends a message when an example prompt is clicked', () => {
    render(<ExamplePrompts />);

    const firstPrompt = screen.getByText(/I need to reduce costs but keep quality the same/i);
    fireEvent.click(firstPrompt);

    expect(mockSendMessage).toHaveBeenCalledWith(
      JSON.stringify({ type: 'user_message', payload: { text: 'I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.' } })
    );
    expect(mockSetProcessing).toHaveBeenCalledWith(true);
  });
});
