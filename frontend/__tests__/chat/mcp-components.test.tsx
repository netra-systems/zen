import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MCPToolIndicator } from '@/components/chat/MCPToolIndicator';
import { MCPServerStatus } from '@/components/chat/MCPServerStatus';
import { MCPResultCard } from '@/components/chat/MCPResultCard';
import type { 
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
MCPServerStatus } from '@/components/chat/MCPServerStatus';
import { MCPResultCard } from '@/components/chat/MCPResultCard';
import type { 
  MCPToolExecution, 
  MCPServerInfo, 
  MCPToolResult 
} from '@/types/mcp-types';
import {
  setupMCPMocks,
  cleanupMCPMocks,
  createMockServer,
  createMockExecution as createMockExecutionFromMock,
  createMockToolResult
} from '../mocks/mcp-service-mock';

// ============================================
// Test Setup and Teardown
// ============================================

beforeEach(() => {
  setupMCPMocks();
});

afterEach(() => {
  cleanupMCPMocks();
  jest.clearAllMocks();
    // Clean up timers to prevent hanging
    jest.clearAllTimers();
    jest.useFakeTimers();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
});

// ============================================
// Test Data Setup (8 lines max)
// ============================================

const createMockExecution = (overrides?: Partial<MCPToolExecution>): MCPToolExecution => ({
  id: 'exec-1',
  tool_name: 'mock-tool',
  server_name: 'mock-server',
  status: 'COMPLETED',
  arguments: { param1: 'value1' },
  started_at: new Date().toISOString(),
  duration_ms: 1500,
  ...overrides
});

// Using mock factories from the mock service module
const createMockResult = createMockToolResult;

// ============================================
// MCPToolIndicator Tests (8 lines max each)
// ============================================

describe('MCPToolIndicator', () => {
    jest.setTimeout(10000);
  it('renders tool executions correctly', () => {
    const executions = [createMockExecution()];
    render(
      <MCPToolIndicator 
        tool_executions={executions}
        server_status="CONNECTED"
        show_details={true}
      />
    );
    expect(screen.getByText('mock-tool')).toBeInTheDocument();
    expect(screen.getByText('@mock-server')).toBeInTheDocument();
  });

  it('shows empty state when no executions', () => {
    render(
      <MCPToolIndicator 
        tool_executions={[]}
        server_status="CONNECTED"
      />
    );
    expect(screen.queryByText('MCP Tools')).not.toBeInTheDocument();
  });

  it('displays execution status correctly', () => {
    const runningExecution = createMockExecution({ status: 'RUNNING' });
    const failedExecution = createMockExecution({ 
      id: 'exec-2', 
      status: 'FAILED' 
    });
    render(
      <MCPToolIndicator 
        tool_executions={[runningExecution, failedExecution]}
        server_status="CONNECTED"
        show_details={true}
      />
    );
    expect(screen.getByText('MCP Tools (2)')).toBeInTheDocument();
  });

  it('expands execution details on click', async () => {
    const executions = [createMockExecution()];
    render(
      <MCPToolIndicator 
        tool_executions={executions}
        server_status="CONNECTED"
      />
    );
    const expandButton = screen.getByRole('button');
    fireEvent.click(expandButton);
    await waitFor(() => {
      expect(screen.getByText(/Arguments:/)).toBeInTheDocument();
    });
  });
});

// ============================================
// MCPServerStatus Tests (8 lines max each)
// ============================================

describe('MCPServerStatus', () => {
    jest.setTimeout(10000);
  it('renders server list correctly', () => {
    const servers = [createMockServer({ name: 'mock-server' })];
    render(<MCPServerStatus servers={servers} connections={[]} />);
    expect(screen.getByText('mock-server')).toBeInTheDocument();
    expect(screen.getByText('1/1 Connected')).toBeInTheDocument();
  });

  it('shows empty state when no servers', () => {
    render(<MCPServerStatus servers={[]} connections={[]} />);
    expect(screen.getByText('No MCP servers')).toBeInTheDocument();
  });

  it('displays server status correctly', () => {
    const connectedServer = createMockServer({ name: 'connected-server', status: 'CONNECTED' });
    const disconnectedServer = createMockServer({ 
      id: 'server-2',
      name: 'disconnected-server',
      status: 'DISCONNECTED' 
    });
    render(
      <MCPServerStatus 
        servers={[connectedServer, disconnectedServer]} 
        connections={[]} 
      />
    );
    expect(screen.getByText('1/2 Connected')).toBeInTheDocument();
  });

  it('renders in compact mode', () => {
    const servers = [createMockServer({ name: 'mock-server' })];
    render(
      <MCPServerStatus 
        servers={servers} 
        connections={[]} 
        compact={true} 
      />
    );
    expect(screen.getByText('mock-server')).toBeInTheDocument();
  });
});

// ============================================
// MCPResultCard Tests (8 lines max each)
// ============================================

describe('MCPResultCard', () => {
    jest.setTimeout(10000);
  const mockExecution = createMockExecution();

  it('renders successful result correctly', () => {
    const result = createMockResult();
    render(
      <MCPResultCard 
        result={result}
        execution={mockExecution}
        collapsible={false}
      />
    );
    expect(screen.getByText('mock-tool')).toBeInTheDocument();
    expect(screen.getByText('@mock-server')).toBeInTheDocument();
    expect(screen.getByText('150ms')).toBeInTheDocument();
  });

  it('renders error result correctly', () => {
    const errorResult = createMockResult({
      is_error: true,
      error_message: 'Test error occurred'
    });
    render(
      <MCPResultCard 
        result={errorResult}
        execution={mockExecution}
        collapsible={false}
      />
    );
    expect(screen.getByText('Execution Error')).toBeInTheDocument();
    expect(screen.getByText('Test error occurred')).toBeInTheDocument();
  });

  it('toggles collapsible content', async () => {
    const result = createMockResult();
    render(
      <MCPResultCard 
        result={result}
        execution={mockExecution}
        collapsible={true}
      />
    );
    const toggleButton = screen.getByRole('button');
    fireEvent.click(toggleButton);
    await waitFor(() => {
      expect(screen.getByText('Copy')).toBeInTheDocument();
    });
  });

  it('handles copy to clipboard', async () => {
    const mockClipboard = jest.fn();
    Object.assign(navigator, {
      clipboard: { writeText: mockClipboard }
    });
    
    const result = createMockResult();
    render(
      <MCPResultCard 
        result={result}
        execution={mockExecution}
        collapsible={false}
      />
    );
    
    const copyButton = screen.getByText('Copy');
    fireEvent.click(copyButton);
    expect(mockClipboard).toHaveBeenCalled();
  });
});

// ============================================
// Integration Tests (8 lines max each)
// ============================================

describe('MCP Components Integration', () => {
    jest.setTimeout(10000);
  it('works together in message context', () => {
    const executions = [createMockExecution()];
    const servers = [createMockServer({ name: 'mock-server' })];
    
    render(
      <div>
        <MCPServerStatus servers={servers} connections={[]} compact={true} />
        <MCPToolIndicator 
          tool_executions={executions}
          server_status="CONNECTED"
        />
      </div>
    );
    
    expect(screen.getByText('mock-server')).toBeInTheDocument();
    expect(screen.getByText('mock-tool')).toBeInTheDocument();
  });
});