"use client";

import React, { useState, useEffect } from 'react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { PersistentResponseCard } from '@/components/chat/PersistentResponseCard';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { OverflowPanel } from '@/components/chat/OverflowPanel';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';

const MainChat: React.FC = () => {
  const { 
    isProcessing, 
    messages,
    fastLayerData,
    mediumLayerData,
    slowLayerData,
    currentRunId,
    activeThreadId,
    isThreadLoading
  } = useUnifiedChatStore();
  
  const { status: wsStatus } = useWebSocket();
  const [isCardCollapsed, setIsCardCollapsed] = useState(false);
  const [isOverflowOpen, setIsOverflowOpen] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  
  // WebSocket events are automatically processed through the unified store

  const hasMessages = messages.length > 0;
  const isWebSocketConnected = wsStatus === 'OPEN';
  const isLoading = !isInitialized || !isWebSocketConnected || isThreadLoading;
  const isEmptyState = !activeThreadId && !hasMessages && !isLoading;
  const hasThreadButNoMessages = activeThreadId && !hasMessages && !isLoading && !isProcessing;
  
  // Thread loading is now handled via WebSocket events in the store
  // The handleWebSocketEvent function in useUnifiedChatStore will process
  // 'thread_loaded' events and automatically update the messages
  const showResponseCard = currentRunId !== null || isProcessing;

  // Initialize component when WebSocket is connected
  useEffect(() => {
    if (isWebSocketConnected && !isInitialized) {
      setIsInitialized(true);
    }
  }, [isWebSocketConnected, isInitialized]);

  // Thread loading is now managed through the unified store via WebSocket events
  // The store handles 'thread_loading' and 'thread_loaded' events automatically

  // Auto-collapse card after completion
  useEffect(() => {
    if (slowLayerData?.finalReport && !isProcessing) {
      const timer = setTimeout(() => {
        setIsCardCollapsed(true);
      }, 2000); // 2 seconds after completion
      
      return () => clearTimeout(timer);
    }
  }, [slowLayerData?.finalReport, isProcessing]);

  // Reset collapse state when new processing starts
  useEffect(() => {
    if (isProcessing) {
      setIsCardCollapsed(false);
    }
  }, [isProcessing]);

  // Keyboard shortcut for overflow panel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        setIsOverflowOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Show loading state while initializing
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <div className="text-sm text-gray-600">
            {!isWebSocketConnected ? 'Connecting to chat service...' : 
             isThreadLoading ? 'Loading thread messages...' : 'Loading chat...'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-gradient-to-br from-gray-50 via-white to-gray-50">
      {/* Sidebar removed - handled by AppWithLayout */}
      
      <div className="flex flex-col flex-1 max-w-full">
        {/* Chat Header */}
        <ChatHeader />
        
        {/* Main Content Area */}
        <div className="flex-grow overflow-hidden relative">
          <div className="h-full overflow-y-auto">
            {/* Empty State - shown when no thread is selected */}
            <AnimatePresence mode="wait">
              {isEmptyState && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className="flex flex-col items-center justify-center h-full text-center px-6"
                >
                  <div className="max-w-md">
                    <div className="mb-6">
                      <div className="w-16 h-16 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-4">
                        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                      </div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">Welcome to Netra AI</h3>
                      <p className="text-gray-600 mb-4">
                        Create a new conversation or select an existing one from the sidebar to get started with AI-powered optimization.
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            
            {/* Example Prompts - shown when thread selected but no messages */}
            <AnimatePresence mode="wait">
              {hasThreadButNoMessages && (
                <motion.div
                  initial={{ opacity: 1 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <ExamplePrompts />
                </motion.div>
              )}
            </AnimatePresence>
            
            {/* Message History */}
            {!isEmptyState && <MessageList />}
            
            {/* Persistent Response Card - Shows current processing */}
            <AnimatePresence>
              {showResponseCard && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className="px-6 py-4 max-w-5xl mx-auto"
                >
                  <PersistentResponseCard
                    fastLayerData={fastLayerData}
                    mediumLayerData={mediumLayerData}
                    slowLayerData={slowLayerData}
                    isProcessing={isProcessing}
                    isCollapsed={isCardCollapsed}
                    onToggleCollapse={() => setIsCardCollapsed(!isCardCollapsed)}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
        
        {/* Chat Input */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="border-t bg-white/95 backdrop-blur-sm shadow-lg"
        >
          <div className="px-6 py-4 max-w-5xl mx-auto w-full">
            <MessageInput />
          </div>
        </motion.div>
      </div>
      
      {/* Overflow Debug Panel */}
      <OverflowPanel isOpen={isOverflowOpen} onClose={() => setIsOverflowOpen(false)} />
    </div>
  );
};

export default MainChat;