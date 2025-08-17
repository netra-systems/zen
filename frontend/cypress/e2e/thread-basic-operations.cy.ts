import { Message, WebSocketMessage } from '@/types/chat';
import {
  setupThreadTestEnvironment,
  openThreadSidebar,
  createNewThread,
  mockThreadMessages,
  sendMessage,
  simulateAgentResponse,
  mockNewThreadCreation,
  waitForThreadOperation,
  verifyThreadVisible,
  verifyMessageVisible,
  verifyMessageNotVisible,
  mockThread1Messages,
  mockThread2Messages
} from './thread-test-helpers';

/**
 * Thread Basic Operations Tests
 * Tests for thread display, switching, and creation
 * Business Value: Growth segment - validates core conversation workflows
 */

describe('Thread Basic Operations', () => {
  beforeEach(() => {
    setupThreadTestEnvironment();
  });

  it('should display thread list and allow switching between threads', () => {
    openThreadSidebar();
    verifyThreadsDisplayed();
    testThreadSwitching();
  });

  it('should create a new thread and maintain conversation context', () => {
    createNewThread();
    setupNewThreadMock();
    testNewThreadCreation();
    testConversationContext();
  });

  // Helper functions for thread display test
  function verifyThreadsDisplayed(): void {
    verifyThreadVisible('LLM Optimization Discussion');
    verifyThreadVisible('Cost Analysis Project');
    verifyThreadVisible('Performance Testing');
  }

  function testThreadSwitching(): void {
    setupThread1Messages();
    selectFirstThread();
    verifyFirstThreadMessages();
    
    setupThread2Messages();
    selectSecondThread();
    verifySecondThreadMessages();
    verifyFirstThreadMessagesHidden();
  }

  function setupThread1Messages(): void {
    mockThreadMessages('thread-1', mockThread1Messages);
  }

  function selectFirstThread(): void {
    cy.contains('LLM Optimization Discussion').click();
    waitForThreadOperation('getThread1Messages');
  }

  function verifyFirstThreadMessages(): void {
    verifyMessageVisible('How can I optimize my LLM inference?');
    verifyMessageVisible('I can help you optimize your LLM inference');
  }

  function setupThread2Messages(): void {
    mockThreadMessages('thread-2', mockThread2Messages);
  }

  function selectSecondThread(): void {
    cy.contains('Cost Analysis Project').click();
    waitForThreadOperation('getThread2Messages');
  }

  function verifySecondThreadMessages(): void {
    verifyMessageVisible('Analyze the cost of my current deployment');
    verifyMessageVisible('Analyzing your deployment costs');
  }

  function verifyFirstThreadMessagesHidden(): void {
    verifyMessageNotVisible('How can I optimize my LLM inference?');
  }

  // Helper functions for new thread creation test
  function setupNewThreadMock(): void {
    const newThread = {
      id: 'thread-new',
      title: 'New Conversation',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      user_id: 1,
      message_count: 0
    };
    mockNewThreadCreation(newThread);
  }

  function testNewThreadCreation(): void {
    const firstMessage = 'Start a new optimization analysis';
    sendMessage(firstMessage);
    waitForThreadOperation('createThread');
    verifyMessageVisible(firstMessage);
    simulateFirstAgentResponse();
  }

  function simulateFirstAgentResponse(): void {
    const agentResponse = {
      id: 'msg-new-1',
      thread_id: 'thread-new',
      created_at: new Date().toISOString(),
      content: 'Starting new optimization analysis for your system...',
      type: 'agent' as const,
      sub_agent_name: 'TriageSubAgent'
    };
    simulateAgentResponse(agentResponse);
    verifyMessageVisible('Starting new optimization analysis');
  }

  function testConversationContext(): void {
    sendFollowUpMessage();
    simulateContextualResponse();
  }

  function sendFollowUpMessage(): void {
    const followUp = 'Focus on GPU utilization';
    sendMessage(followUp);
    verifyMessageVisible(followUp);
  }

  function simulateContextualResponse(): void {
    const contextResponse = {
      id: 'msg-new-2',
      thread_id: 'thread-new',
      created_at: new Date().toISOString(),
      content: 'Focusing the optimization analysis on GPU utilization as requested...',
      type: 'agent' as const,
      sub_agent_name: 'OptimizationsCoreSubAgent'
    };
    simulateAgentResponse(contextResponse);
    verifyContextualResponseDisplayed();
  }

  function verifyContextualResponseDisplayed(): void {
    verifyMessageVisible('Focusing the optimization analysis on GPU utilization');
  }
});