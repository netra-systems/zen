import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
- Segment: All (Free → Enterprise)  
 * - Business Goal: Ensure core chat messaging functions reliably
 * - Value Impact: Chat is the primary product interface - 100% business critical
 * - Revenue Impact: Core functionality = 100% of revenue potential
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 * - Real WebSocket connections (NO mocks for core functionality)
 * - Real components with actual state management
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Real components and utilities
import { MessageInput } from '../../../components/chat/MessageInput';
import { MainChat } from '../../../components/chat/MainChat';
import { TestProviders } from '../../setup/test-providers';

// Real WebSocket test utilities
import { 
  WebSocketTestManager,
  waitForRealMessage,
  expectRealWebSocketConnection,
  expectRealMessageReceived,
  expectRealMessageContent,
  simulateRealNetworkError
} from '../../helpers/websocket-test-manager';

// Chat functionality test helpers
import {
  setupChatTestEnvironment,
  establishChatConnection,
  cleanupChatResources,
  sendUserMessage,
  expectMessageDelivered,
  expectMessagePersisted,
  expectDeliveryConfirmation,
  expectMessageDisplayed,
  MESSAGE_SEND_TIMEOUT,
  MESSAGE_RECEIVE_TIMEOUT
} from './test-helpers';

// Test data factories  
import {
  createBasicUserMessage,
  createMessageWithId,
  createLongUserMessage,
  createMessageSequence,
  createSpecialCharMessage,
  createMultilineMessage,
  createEmptyMessage,
  createWhitespaceMessage
} from './test-data-factories';

describe('Message Send/Receive Core Functionality', () => {
    jest.setTimeout(10000);
  let wsManager: WebSocketTestManager;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(async () => {
    user = userEvent.setup();
    wsManager = new WebSocketTestManager();
    await setupChatTestEnvironment(wsManager);
  });

  afterEach(async () => {
    await cleanupChatResources(wsManager);
  });

  describe('Basic Message Sending', () => {
      jest.setTimeout(10000);
    test('sends user message through real WebSocket', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );

      const messageText = createBasicUserMessage();
      const textArea = screen.getByRole('textbox');
      
      await user.type(textArea, messageText);
      await user.keyboard('{Enter}');

      expectRealWebSocketConnection(wsManager);
      await waitForRealMessage(wsManager, 'user_message', MESSAGE_SEND_TIMEOUT);
      expectRealMessageReceived(wsManager, 'user_message');
    });

    test('handles message with delivery confirmation', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );

      const messageWithId = createMessageWithId();
      const textArea = screen.getByRole('textbox');
      
      await user.type(textArea, messageWithId.content);
      await user.keyboard('{Enter}');

      const confirmationMsg = await waitForRealMessage(
        wsManager, 
        'delivery_confirmation', 
        MESSAGE_SEND_TIMEOUT
      );
      expectDeliveryConfirmation(messageWithId.id, confirmationMsg);
    });

    test('sends long messages without truncation', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );

      const longMessage = createLongUserMessage(500);
      const textArea = screen.getByRole('textbox');
      
      await user.type(textArea, longMessage);
      await user.keyboard('{Enter}');

      const sentMsg = await waitForRealMessage(wsManager, 'user_message', MESSAGE_SEND_TIMEOUT);
      expectRealMessageContent(sentMsg, longMessage);
    });

    test('maintains message order during rapid sending', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );

      const messageSequence = createMessageSequence(3);
      const textArea = screen.getByRole('textbox');

      for (const message of messageSequence) {
        await user.clear(textArea);
        await user.type(textArea, message);
        await user.keyboard('{Enter}');
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      await waitFor(() => {
        const sentMessages = wsManager.getSentMessages();
        expect(sentMessages).toHaveLength(3);
      });
    });

    test('handles special characters and emojis', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );

      const specialMessage = createSpecialCharMessage();
      const textArea = screen.getByRole('textbox');
      
      await user.type(textArea, specialMessage);
      await user.keyboard('{Enter}');

      const sentMsg = await waitForRealMessage(wsManager, 'user_message', MESSAGE_SEND_TIMEOUT);
      expectRealMessageContent(sentMsg, specialMessage);
    });

    test('sends multiline messages with shift+enter', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );

      const multilineMessage = createMultilineMessage();
      const textArea = screen.getByRole('textbox');
      
      await user.type(textArea, multilineMessage.line1);
      await user.keyboard('{Shift>}{Enter}{/Shift}');
      await user.type(textArea, multilineMessage.line2);
      await user.keyboard('{Enter}');

      const sentMsg = await waitForRealMessage(wsManager, 'user_message', MESSAGE_SEND_TIMEOUT);
      expect(sentMsg).toContain(multilineMessage.line1);
      expect(sentMsg).toContain(multilineMessage.line2);
    });
  });

  describe('Message Receiving and Display', () => {
      jest.setTimeout(10000);
    test('receives and displays agent responses', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const agentResponse = 'This is an agent response to your query.';
      wsManager.simulateIncomingMessage({
        type: 'agent_response',
        content: agentResponse,
        timestamp: new Date().toISOString()
      });

      await waitFor(() => {
        expectMessageDisplayed(agentResponse);
      }, { timeout: MESSAGE_RECEIVE_TIMEOUT });
    });

    test('handles streaming message updates', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const streamChunks = ['Hello', ' there,', ' how can I help?'];
      
      for (const chunk of streamChunks) {
        wsManager.simulateIncomingMessage({
          type: 'agent_stream',
          content: chunk,
          messageId: 'stream-test-123'
        });
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      await waitFor(() => {
        const fullMessage = streamChunks.join('');
        expectMessageDisplayed(fullMessage);
      });
    });

    test('persists messages across component remounts', async () => {
      await establishChatConnection(wsManager);
      
      const { unmount } = render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const testMessage = 'Persistence test message';
      await sendUserMessage(wsManager, testMessage);
      
      unmount();
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await waitFor(() => {
        expectMessagePersisted(testMessage);
      });
    });
  });

  describe('Message Validation and Error Handling', () => {
      jest.setTimeout(10000);
    test('prevents sending empty messages', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );

      const emptyMessage = createEmptyMessage();
      const textArea = screen.getByRole('textbox');
      
      await user.type(textArea, emptyMessage);
      await user.keyboard('{Enter}');

      // Should not send any message
      expect(wsManager.getSentMessages()).toHaveLength(0);
    });

    test('prevents sending whitespace-only messages', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );

      const whitespaceMessage = createWhitespaceMessage();
      const textArea = screen.getByRole('textbox');
      
      await user.type(textArea, whitespaceMessage);
      await user.keyboard('{Enter}');

      expect(wsManager.getSentMessages()).toHaveLength(0);
    });

    test('handles network errors during send', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );

      simulateRealNetworkError(wsManager);
      
      const messageText = createBasicUserMessage();
      const textArea = screen.getByRole('textbox');
      
      await user.type(textArea, messageText);
      await user.keyboard('{Enter}');

      // Should show error state but not crash
      await waitFor(() => {
        expect(screen.queryByText(/error/i)).toBeInTheDocument();
      });
    });

    test('retries failed messages automatically', async () => {
      await establishChatConnection(wsManager);
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );

      const messageText = createBasicUserMessage();
      const textArea = screen.getByRole('textbox');
      
      // Simulate temporary network failure
      simulateRealNetworkError(wsManager);
      
      await user.type(textArea, messageText);
      await user.keyboard('{Enter}');

      // Restore connection
      await wsManager.reconnect();
      
      // Message should eventually be delivered
      await waitFor(() => {
        expectMessageDelivered(messageText);
      }, { timeout: MESSAGE_SEND_TIMEOUT * 2 });
    });
  });
});