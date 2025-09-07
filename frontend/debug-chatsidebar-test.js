// Debug test to check ChatSidebar import
const React = require('react');

// Test the import the same way the failing test does
try {
  console.log('Attempting to import ChatSidebar...');
  
  // Mock the dependencies first
  jest.mock('@/store/unified-chat');
  jest.mock('@/hooks/useWebSocket');
  jest.mock('@/store/authStore');
  jest.mock('@/hooks/useAuthState');
  jest.mock('@/components/auth/AuthGate', () => ({
    AuthGate: ({ children }) => children
  }));
  jest.mock('@/hooks/useThreadSwitching');
  jest.mock('@/lib/thread-operation-manager');
  jest.mock('@/lib/thread-state-machine');
  jest.mock('@/lib/logger');
  jest.mock('@/services/threadService');
  jest.mock('./components/chat/ChatSidebarHooks');
  jest.mock('./components/chat/ChatSidebarUIComponents');
  jest.mock('./components/chat/ChatSidebarThreadList');
  jest.mock('./components/chat/ChatSidebarFooter');
  
  const { ChatSidebar } = require('@/components/chat/ChatSidebar');
  console.log('ChatSidebar imported successfully:', typeof ChatSidebar);
  console.log('ChatSidebar value:', ChatSidebar);
  
} catch (error) {
  console.error('Import error:', error.message);
  console.error('Stack:', error.stack);
}