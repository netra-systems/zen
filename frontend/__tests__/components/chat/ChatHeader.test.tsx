
import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { setupChatMocks, resetChatMocks, renderWithChatSetup, overrideChatMocks, mockUnifiedChatStore, mockMCPTools } from './shared-test-setup';

// Mock only necessary dependencies - use real components
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useMCPTools');

// Import the mocked hooks
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useMCPTools } from '@/hooks/useMCPTools';

// Setup mocks before tests
beforeAll(() => {
  setupChatMocks();
});

beforeEach(() => {
  resetChatMocks();
  // Reset the mock implementations
  jest.mocked(useUnifiedChatStore).mockReturnValue(mockUnifiedChatStore);
  (useMCPTools as jest.Mock).mockReturnValue(mockMCPTools);
});

describe('ChatHeader', () => {
  it('should render the sub-agent name and status', () => {
    jest.mocked(useUnifiedChatStore).mockReturnValue({
      ...mockUnifiedChatStore,
      subAgentName: 'Test Agent',
      subAgentStatus: { lifecycle: 'running' },
      isProcessing: false,
    });
    renderWithChatSetup(<ChatHeader />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    // Status is displayed with specific casing and formatting
    expect(screen.getByText('running')).toBeInTheDocument();
  });

  it('should render default status when no status provided', () => {
    jest.mocked(useUnifiedChatStore).mockReturnValue({
      ...mockUnifiedChatStore,
      subAgentName: 'Test Agent',
      subAgentStatus: { lifecycle: null },
      isProcessing: false,
    });
    renderWithChatSetup(<ChatHeader />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    // Status is displayed as 'Ready' when lifecycle is null
    expect(screen.getByText('Ready')).toBeInTheDocument();
  });

  it('should render default agent name when no name provided', () => {
    jest.mocked(useUnifiedChatStore).mockReturnValue({
      ...mockUnifiedChatStore,
      subAgentName: null,
      subAgentStatus: null,
      isProcessing: false,
    });
    renderWithChatSetup(<ChatHeader />);
    expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
  });

  it('should render processing state', () => {
    jest.mocked(useUnifiedChatStore).mockReturnValue({
      ...mockUnifiedChatStore,
      subAgentName: 'Test Agent',
      subAgentStatus: { lifecycle: 'active' },
      isProcessing: true,
    });
    renderWithChatSetup(<ChatHeader />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    // Status is displayed with specific casing and formatting
    expect(screen.getByText('active')).toBeInTheDocument();
  });
});
