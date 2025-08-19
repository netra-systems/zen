/**
 * Mock Components for Performance Testing
 * 
 * Lightweight mock components to avoid dependency issues in performance tests
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Full TypeScript typing
 */

import React from 'react';

export const MockMainChat = () => <div data-testid="main-chat">Mock Main Chat</div>;

export const MockChatSidebar = () => <div data-testid="chat-sidebar">Mock Chat Sidebar</div>;

export const MockMessageInput = () => <textarea data-testid="message-input" />;

export const MockThreadList = ({ threads }: { threads?: any[] }) => (
  <div data-testid="thread-list">
    <div data-testid="scroll-container">
      {threads?.map((thread, i) => (
        <div key={i} data-testid="thread-item" className="thread-item">
          {thread.title || thread.id}
        </div>
      ))}
    </div>
  </div>
);

export const MockWebSocketProvider = ({ children }: { children: React.ReactNode }) => (
  <div data-testid="websocket-provider">{children}</div>
);