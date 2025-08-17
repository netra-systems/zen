
import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { setupChatMocks, resetChatMocks, renderWithChatSetup, overrideChatMocks, mockUnifiedChatStore, mockMCPTools } from './shared-test-setup';

// Mock all dependencies at the top level
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useMCPTools');
jest.mock('@/components/chat/ConnectionStatusIndicator', () => ({
  ConnectionStatusIndicator: () => <div data-testid="connection-status">Connected</div>
}));
jest.mock('@/components/chat/MCPServerStatus', () => ({
  MCPServerStatus: () => <div data-testid="mcp-server-status">MCP Status</div>
}));

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
  (useUnifiedChatStore as jest.Mock).mockReturnValue(mockUnifiedChatStore);
  (useMCPTools as jest.Mock).mockReturnValue(mockMCPTools);
});

describe('ChatHeader', () => {
  it('should render the sub-agent name and status', () => {
    (useUnifiedChatStore as jest.Mock).mockReturnValue({
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
    (useUnifiedChatStore as jest.Mock).mockReturnValue({
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
    (useUnifiedChatStore as jest.Mock).mockReturnValue({
      ...mockUnifiedChatStore,
      subAgentName: null,
      subAgentStatus: null,
      isProcessing: false,
    });
    renderWithChatSetup(<ChatHeader />);
    expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
  });

  it('should render processing state', () => {
    (useUnifiedChatStore as jest.Mock).mockReturnValue({
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
