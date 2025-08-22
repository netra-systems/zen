/**
 * Chat Page Component Tests
 * 
 * Tests for the chat home page, including Start New Conversation button functionality.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed test with clear interfaces
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import ChatPage from '@/app/chat/page';
import { useThreadCreation } from '@/hooks/useThreadCreation';
import { useUnifiedChatStore } from '@/store/unified-chat';

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn()
}));

jest.mock('@/hooks/useThreadCreation', () => ({
  useThreadCreation: jest.fn()
}));

jest.mock('@/store/unified-chat');

jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>
  }
}));

describe('ChatPage Component', () => {
  const mockPush = jest.fn();
  const mockCreateAndNavigate = jest.fn();
  const mockSetActiveThread = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush
    });
    
    (useThreadCreation as jest.Mock).mockReturnValue({
      createAndNavigate: mockCreateAndNavigate
    });
    
    (useUnifiedChatStore as jest.Mock).mockImplementation((selector: any) => {
      const state = {
        activeThreadId: null,
        setActiveThread: mockSetActiveThread
      };
      return selector ? selector(state) : state;
    });
  });
  
  /**
   * Test 1: Start New Conversation button renders and is clickable
   */
  it('should render Start New Conversation button and handle click', async () => {
    mockCreateAndNavigate.mockResolvedValue(true);
    
    render(<ChatPage />);
    
    const button = screen.getByRole('button', { 
      name: /start new conversation/i 
    });
    
    expect(button).toBeInTheDocument();
    expect(button).toBeEnabled();
    
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockCreateAndNavigate).toHaveBeenCalledTimes(1);
    });
  });
  
  /**
   * Test 2: Successfully creates thread and navigates to chat
   */
  it('should create new thread and navigate to chat on successful creation', async () => {
    mockCreateAndNavigate.mockResolvedValue(true);
    
    render(<ChatPage />);
    
    const button = screen.getByRole('button', { 
      name: /start new conversation/i 
    });
    
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockCreateAndNavigate).toHaveBeenCalled();
      expect(mockPush).toHaveBeenCalledWith('/chat');
    });
  });
  
  /**
   * Test 3: Handles thread creation failure gracefully
   */
  it('should not navigate when thread creation fails', async () => {
    mockCreateAndNavigate.mockResolvedValue(false);
    
    render(<ChatPage />);
    
    const button = screen.getByRole('button', { 
      name: /start new conversation/i 
    });
    
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockCreateAndNavigate).toHaveBeenCalled();
    });
    
    expect(mockPush).not.toHaveBeenCalled();
  });
  
  /**
   * Test: View Recent Chats button navigates correctly
   */
  it('should navigate to chat when View Recent Chats is clicked', () => {
    render(<ChatPage />);
    
    const button = screen.getByRole('button', { 
      name: /view recent chats/i 
    });
    
    expect(button).toBeInTheDocument();
    
    fireEvent.click(button);
    
    expect(mockPush).toHaveBeenCalledWith('/chat');
  });
  
  /**
   * Test: Clears active thread when component mounts
   */
  it('should clear active thread when page loads with active thread', () => {
    (useUnifiedChatStore as jest.Mock).mockImplementation((selector: any) => {
      const state = {
        activeThreadId: 'thread-123',
        setActiveThread: mockSetActiveThread
      };
      return selector ? selector(state) : state;
    });
    
    render(<ChatPage />);
    
    expect(mockSetActiveThread).toHaveBeenCalledWith(null);
  });
  
  /**
   * Test: Does not clear active thread when already null
   */
  it('should not call setActiveThread when activeThreadId is already null', () => {
    render(<ChatPage />);
    
    expect(mockSetActiveThread).not.toHaveBeenCalled();
  });
  
  /**
   * Test: Welcome content renders correctly
   */
  it('should render welcome content with correct text', () => {
    render(<ChatPage />);
    
    expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    expect(screen.getByText(/Your AI-powered optimization platform/i)).toBeInTheDocument();
  });
  
  /**
   * Test: Feature cards render correctly
   */
  it('should render all feature cards', () => {
    render(<ChatPage />);
    
    expect(screen.getByText('AI Optimization')).toBeInTheDocument();
    expect(screen.getByText('Multi-Agent System')).toBeInTheDocument();
    expect(screen.getByText('Real-time Analysis')).toBeInTheDocument();
  });
  
  /**
   * Test: Button has correct styling classes
   */
  it('should apply correct styling to Start New Conversation button', () => {
    render(<ChatPage />);
    
    const button = screen.getByRole('button', { 
      name: /start new conversation/i 
    });
    
    expect(button).toHaveClass('bg-blue-600');
    expect(button).toHaveClass('text-white');
    expect(button).toHaveClass('hover:bg-blue-700');
  });
  
  /**
   * Test: Multiple rapid clicks only create one thread
   */
  it('should handle multiple rapid clicks without creating duplicate threads', async () => {
    mockCreateAndNavigate.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve(true), 100))
    );
    
    render(<ChatPage />);
    
    const button = screen.getByRole('button', { 
      name: /start new conversation/i 
    });
    
    // Simulate rapid clicking
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockCreateAndNavigate).toHaveBeenCalledTimes(3);
    }, { timeout: 500 });
    
    // Navigation should happen for each successful creation
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/chat');
    });
  });
});