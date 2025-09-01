import { Message, WebSocketMessage } from '@/types/unified';

/**
 * Thread Test Helpers
 * Common utilities, mocks, and helper functions for thread testing
 * Business Value: Growth segment - validates conversation management workflows
 */

// Thread mock data interfaces
export interface MockThread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  user_id: number;
  message_count: number;
}

export interface MockMessage {
  id: string;
  thread_id?: string;
  content: string;
  type: 'user' | 'agent';
  sub_agent_name?: string;
  created_at: string;
  displayed_to_user?: boolean;
}

// Mock thread data
export const mockThreads: MockThread[] = [
  {
    id: 'thread-1',
    title: 'LLM Optimization Discussion',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 3600000).toISOString(),
    user_id: 1,
    message_count: 5
  },
  {
    id: 'thread-2',
    title: 'Cost Analysis Project',
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date(Date.now() - 7200000).toISOString(),
    user_id: 1,
    message_count: 3
  },
  {
    id: 'thread-3',
    title: 'Performance Testing',
    created_at: new Date(Date.now() - 259200000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString(),
    user_id: 1,
    message_count: 8
  }
];

// Mock messages for different threads
export const mockThread1Messages: MockMessage[] = [
  {
    id: 'msg-1',
    thread_id: 'thread-1',
    content: 'How can I optimize my LLM inference?',
    type: 'user',
    created_at: new Date(Date.now() - 3700000).toISOString()
  },
  {
    id: 'msg-2',
    thread_id: 'thread-1',
    content: 'I can help you optimize your LLM inference. Let me analyze your current setup.',
    type: 'agent',
    sub_agent_name: 'OptimizationsCoreSubAgent',
    created_at: new Date(Date.now() - 3650000).toISOString()
  }
];

export const mockThread2Messages: MockMessage[] = [
  {
    id: 'msg-3',
    thread_id: 'thread-2',
    content: 'Analyze the cost of my current deployment',
    type: 'user',
    created_at: new Date(Date.now() - 7300000).toISOString()
  },
  {
    id: 'msg-4',
    thread_id: 'thread-2',
    content: 'Analyzing your deployment costs...',
    type: 'agent',
    sub_agent_name: 'DataSubAgent',
    created_at: new Date(Date.now() - 7250000).toISOString()
  }
];

import { setupAuthenticatedState } from '../support/auth-helpers';

// Authentication setup helper - uses unified auth helper
export function setupAuth(): void {
  setupAuthenticatedState();
}

// Thread API mocks setup
export function setupThreadMocks(): void {
  cy.intercept('GET', '/api/threads', {
    statusCode: 200,
    body: mockThreads
  }).as('getThreads');
}

// Open thread sidebar helper - sidebar is already visible in layout
export function openThreadSidebar(): void {
  // The sidebar is always visible in the current implementation
  cy.get('[data-testid="chat-sidebar"]', { timeout: 10000 }).should('be.visible');
}

// Create new thread helper
export function createNewThread(): void {
  cy.get('[data-testid="new-chat-button"]').click({ timeout: 10000 });
}

// Mock thread messages for specific thread
export function mockThreadMessages(threadId: string, messages: MockMessage[]): void {
  cy.intercept('GET', `/api/threads/${threadId}/messages`, {
    statusCode: 200,
    body: messages
  }).as(`getThread${threadId.split('-')[1]}Messages`);
}

// Send message helper
export function sendMessage(message: string): void {
  cy.get('[data-testid="message-input"] textarea', { timeout: 10000 }).type(message);
  cy.get('[data-testid="send-button"]').click();
}

// Simulate agent response via WebSocket
export function simulateAgentResponse(response: Omit<Message, 'id'> & { id: string }): void {
  cy.window().then((win) => {
    const agentMessage: WebSocketMessage = {
      type: 'message',
      payload: {
        ...response,
        displayed_to_user: true
      } as Message
    };
    // @ts-ignore
    (win as any).ws.onmessage({ data: JSON.stringify(agentMessage) });
  });
}

// Mock new thread creation
export function mockNewThreadCreation(threadData: MockThread): void {
  cy.intercept('POST', '/api/threads', {
    statusCode: 201,
    body: threadData
  }).as('createThread');
}

// Mock thread search
export function mockThreadSearch(searchTerm: string, results: MockThread[]): void {
  cy.intercept('GET', `/api/threads?search=${searchTerm}`, {
    statusCode: 200,
    body: results
  }).as('searchThreads');
}

// Mock thread deletion
export function mockThreadDeletion(threadId: string): void {
  cy.intercept('DELETE', `/api/threads/${threadId}`, {
    statusCode: 204
  }).as('deleteThread');
}

// Mock thread rename
export function mockThreadRename(threadId: string, updatedThread: MockThread): void {
  cy.intercept('PATCH', `/api/threads/${threadId}`, {
    statusCode: 200,
    body: updatedThread
  }).as('renameThread');
}

// Mock thread export
export function mockThreadExport(threadId: string, exportData: any): void {
  cy.intercept('GET', `/api/threads/${threadId}/export`, {
    statusCode: 200,
    headers: {
      'content-type': 'application/json',
      'content-disposition': 'attachment; filename="thread-export.json"'
    },
    body: exportData
  }).as('exportThread');
}

// Mock paginated messages
export function mockPaginatedMessages(
  threadId: string, 
  limit: number, 
  offset: number, 
  messages: MockMessage[]
): void {
  cy.intercept('GET', `/api/threads/${threadId}/messages?limit=${limit}&offset=${offset}`, {
    statusCode: 200,
    body: messages
  }).as(`getMessages${offset > 0 ? 'Older' : 'Initial'}`);
}

// Generate mock messages for pagination testing
export function generateMockMessages(
  threadId: string, 
  count: number, 
  startIndex: number = 0
): MockMessage[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `msg-${startIndex + i}`,
    thread_id: threadId,
    content: `${startIndex > 0 ? 'Older ' : ''}Message ${startIndex + i}`,
    type: (startIndex + i) % 2 === 0 ? 'user' : 'agent',
    created_at: new Date(Date.now() - ((startIndex + i) * 60000)).toISOString()
  }));
}

// Verify thread visibility helper
export function verifyThreadVisible(threadTitle: string): void {
  cy.contains(threadTitle).should('be.visible');
}

// Verify thread not visible helper
export function verifyThreadNotVisible(threadTitle: string): void {
  cy.contains(threadTitle).should('not.exist');
}

// Verify message visible helper
export function verifyMessageVisible(messageContent: string): void {
  cy.contains(messageContent).should('be.visible');
}

// Verify message not visible helper
export function verifyMessageNotVisible(messageContent: string): void {
  cy.contains(messageContent).should('not.exist');
}

// Common test setup for all thread tests
export function setupThreadTestEnvironment(): void {
  setupAuth();
  setupThreadMocks();
  cy.visit('/chat');
}

// Wait for thread operation to complete
export function waitForThreadOperation(aliasName: string): void {
  cy.wait(`@${aliasName}`);
}