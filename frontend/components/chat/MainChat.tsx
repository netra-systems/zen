"use client";

import React, { useState, useEffect, useRef } from 'react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { PersistentResponseCard } from '@/components/chat/PersistentResponseCard';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { OverflowPanel } from '@/components/chat/OverflowPanel';
import { EventDiagnosticsPanel } from '@/components/chat/EventDiagnosticsPanel';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useLoadingState } from '@/hooks/useLoadingState';
import { useEventProcessor } from '@/hooks/useEventProcessor';
import { useThreadNavigation } from '@/hooks/useThreadNavigation';
import { logger } from '@/utils/debug-logger';

// Helper Functions (8 lines max each)
const executeTestRun = async (
  setIsRunningTests: (running: boolean) => void,
  setTestResults: (results: any) => void
): Promise<void> => {
  setIsRunningTests(true);
  try {
    // Only import test module in development
    if (process.env.NODE_ENV === 'development') {
      try {
        const testModule = await import('@/lib/event-queue.test');
        const results = await testModule.runEventQueueTests();
        setTestResults(results);
        logger.debug('Event Queue Test Results:', results);
      } catch (importError) {
        logger.error('Failed to load test module:', importError);
        setTestResults({ error: 'Test module not available' });
      }
    } else {
      setTestResults({ error: 'Tests only available in development mode' });
    }
  } catch (error) {
    handleTestExecutionError(error, setTestResults);
  } finally {
    setIsRunningTests(false);
  }
};

const handleTestExecutionError = (
  error: unknown,
  setTestResults: (results: any) => void
): void => {
  logger.error('Test execution failed:', error);
  setTestResults({ error: (error as Error).message });
};

const handleOverflowToggle = (
  e: KeyboardEvent,
  setIsOverflowOpen: (open: boolean | ((prev: boolean) => boolean)) => void
): void => {
  if (e.ctrlKey && e.shiftKey && e.key === 'D') {
    e.preventDefault();
    setIsOverflowOpen(prev => !prev);
  }
};

const handleDiagnosticsToggle = (
  e: KeyboardEvent,
  setShowEventDiagnostics: (show: boolean | ((prev: boolean) => boolean)) => void
): void => {
  if (e.ctrlKey && e.shiftKey && e.key === 'E') {
    e.preventDefault();
    setShowEventDiagnostics(prev => !prev);
  }
};

const createKeyboardHandler = (
  setIsOverflowOpen: (open: boolean | ((prev: boolean) => boolean)) => void,
  setShowEventDiagnostics: (show: boolean | ((prev: boolean) => boolean)) => void
) => {
  return (e: KeyboardEvent) => {
    handleOverflowToggle(e, setIsOverflowOpen);
    handleDiagnosticsToggle(e, setShowEventDiagnostics);
  };
};
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
    isThreadLoading,
    handleWebSocketEvent
  } = useUnifiedChatStore();
  
  // Thread navigation with URL sync
  const { currentThreadId, isNavigating } = useThreadNavigation();
  
  const { messages: wsMessages } = useWebSocket();
  const [isCardCollapsed, setIsCardCollapsed] = useState(false);
  const [isOverflowOpen, setIsOverflowOpen] = useState(false);
  const [showEventDiagnostics, setShowEventDiagnostics] = useState(false);
  const [testResults, setTestResults] = useState<any>(null);
  const [isRunningTests, setIsRunningTests] = useState(false);
  
  // Use new loading state hook for clean state management
  const {
    shouldShowLoading,
    shouldShowEmptyState,
    shouldShowExamplePrompts,
    loadingMessage
  } = useLoadingState();
  
  // Process WebSocket messages with race condition prevention
  const eventProcessor = useEventProcessor(
    wsMessages,
    handleWebSocketEvent,
    {
      maxQueueSize: 500,
      duplicateWindowMs: 3000,
      processingTimeoutMs: 5000,
      enableDeduplication: true
    }
  );

  // Test runner function
  const runTests = async () => {
    await executeTestRun(setIsRunningTests, setTestResults);
  };

  const hasMessages = messages.length > 0;
  
  // Thread loading is now handled via WebSocket events in the store
  // The handleWebSocketEvent function in useUnifiedChatStore will process
  // 'thread_loaded' events and automatically update the messages
  const showResponseCard = currentRunId !== null || isProcessing;
  const isThreadSwitching = (isThreadLoading || isNavigating) && !isProcessing;

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

  // Keyboard shortcuts for panels and diagnostics
  useEffect(() => {
    const handleKeyDown = createKeyboardHandler(setIsOverflowOpen, setShowEventDiagnostics);
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Show loading state while initializing
  if (shouldShowLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <div className="text-sm text-gray-600">
            {loadingMessage}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-gradient-to-br from-gray-50 via-white to-gray-50" data-testid="main-chat">
      {/* Sidebar removed - handled by AppWithLayout */}
      
      <div className="flex flex-col flex-1 max-w-full">
        {/* Chat Header */}
        <ChatHeader />
        
        {/* Main Content Area */}
        <div className="flex-grow overflow-hidden relative">
          <div className="h-full overflow-y-auto" data-testid="main-content">
            {/* Empty State with Example Prompts - shown when no thread is selected OR thread selected but no messages */}
            <AnimatePresence mode="wait">
              {(shouldShowEmptyState || shouldShowExamplePrompts) && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className="flex flex-col h-full px-6 py-6"
                >
                  {/* Welcome Header - only show for empty state (no thread) */}
                  {shouldShowEmptyState && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.1 }}
                      className="text-center mb-8"
                    >
                      <div className="w-20 h-20 mx-auto bg-gradient-to-br from-blue-100 to-purple-100 rounded-full flex items-center justify-center mb-6">
                        <svg className="w-10 h-10 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <h1 className="text-3xl font-bold text-gray-900 mb-3">Welcome to Netra AI</h1>
                      <p className="text-xl text-gray-600 mb-6">
                        Your AI-powered optimization platform for reducing costs and improving performance
                      </p>
                      <div className="bg-blue-50 rounded-lg p-6 mb-6 max-w-2xl mx-auto">
                        <h3 className="text-lg font-semibold text-blue-900 mb-3">Get Started in 3 Easy Steps:</h3>
                        <div className="space-y-3 text-left">
                          <div className="flex items-center text-blue-800">
                            <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3">1</span>
                            <span>Choose an example prompt below or type your own optimization request</span>
                          </div>
                          <div className="flex items-center text-blue-800">
                            <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3">2</span>
                            <span>Describe your current setup, performance requirements, and budget constraints</span>
                          </div>
                          <div className="flex items-center text-blue-800">
                            <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3">3</span>
                            <span>Get AI-powered recommendations to optimize your infrastructure</span>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                  
                  {/* Example Prompts Section */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: shouldShowEmptyState ? 0.2 : 0 }}
                    className="flex-grow"
                  >
                    <ExamplePrompts />
                  </motion.div>
                  
                  {/* Quick tip */}
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: shouldShowEmptyState ? 0.4 : 0.2 }}
                    className="text-center mt-6"
                  >
                    <p className="text-gray-500 text-sm">
                      💡 Try typing something like: "I need to reduce my AI costs by 30% while maintaining quality"
                    </p>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
            
            {/* Thread Loading Indicator */}
            {isThreadSwitching && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="flex items-center justify-center h-32"
              >
                <div className="flex flex-col items-center gap-3 p-6 bg-white/80 backdrop-blur-sm rounded-lg shadow-sm">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                  <div className="text-sm text-gray-600">Loading conversation...</div>
                  {(activeThreadId || currentThreadId) && (
                    <div className="text-xs text-gray-400">
                      Thread: {(activeThreadId || currentThreadId)!.slice(0, 8)}...
                    </div>
                  )}
                </div>
              </motion.div>
            )}
            
            {/* Message History */}
            {!shouldShowEmptyState && !isThreadSwitching && <MessageList />}
            
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
      
      {/* Event Processing Diagnostics Panel */}
      <EventDiagnosticsPanel
        showEventDiagnostics={showEventDiagnostics}
        setShowEventDiagnostics={setShowEventDiagnostics}
        eventProcessor={eventProcessor}
        wsMessages={wsMessages}
        testResults={testResults}
        setTestResults={setTestResults}
        isRunningTests={isRunningTests}
        setIsRunningTests={setIsRunningTests}
      />
    </div>
  );
};

export default MainChat;