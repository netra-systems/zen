/**
 * Test Component Helpers
 * Reusable test components for integration tests
 */

import React from 'react';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';

export const LoginComponent = ({ onLogin }: { onLogin: () => void }) => {
  const { isAuthenticated, user } = useAuthStore();
  
  return (
    <div>
      <button onClick={onLogin}>Login</button>
      <div data-testid="auth-status">
        {isAuthenticated ? `Logged in as ${user?.email}` : 'Not logged in'}
      </div>
    </div>
  );
};

export const LogoutComponent = () => {
  const { logout, isAuthenticated } = useAuthStore();
  
  return (
    <div>
      <button onClick={logout}>Logout</button>
      <div data-testid="auth-status">
        {isAuthenticated ? 'Logged in' : 'Logged out'}
      </div>
    </div>
  );
};

export const ChatComponent = () => {
  const { messages, addMessage } = useChatStore();
  const [input, setInput] = React.useState('');

  const sendMessage = () => {
    if (!input.trim()) return;
    addMessage({
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: new Date().toISOString()
    });
    setInput('');
  };

  return (
    <div>
      <div data-testid="message-list">
        {messages.map(msg => (
          <div key={msg.id} data-testid={`message-${msg.id}`}>
            {msg.content}
          </div>
        ))}
      </div>
      <input
        data-testid="message-input"
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
};

export const ThreadComponent = () => {
  const { threads, currentThread, addThread, setCurrentThread } = useThreadStore();

  const handleCreateThread = () => {
    const newThread = {
      id: Date.now().toString(),
      title: 'New Thread',
      created_at: Date.now()
    };
    addThread(newThread);
  };

  return (
    <div>
      <button onClick={handleCreateThread}>Create Thread</button>
      <div data-testid="thread-count">{threads.length} threads</div>
      <div data-testid="active-thread">
        {currentThread ? currentThread.title : 'No active thread'}
      </div>
      {threads.map(thread => (
        <button
          key={thread.id}
          data-testid={`thread-${thread.id}`}
          onClick={() => setCurrentThread(thread.id)}
        >
          {thread.title || 'Untitled'}
        </button>
      ))}
    </div>
  );
};