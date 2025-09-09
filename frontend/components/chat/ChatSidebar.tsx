"use client";

import React, { useCallback } from 'react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import { useAuthState } from '@/hooks/useAuthState';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { ThreadOperationManager } from '@/lib/thread-operation-manager';
import { threadStateMachineManager } from '@/lib/thread-state-machine';
import { logger } from '@/lib/logger';
import { AuthGate } from '@/components/auth/AuthGate';
import { 
  useChatSidebarState, 
  useThreadLoader, 
  useThreadFiltering 
} from './ChatSidebarHooks';
import {
  NewChatButton,
  AdminControls,
  SearchBar
} from './ChatSidebarUIComponents';
import { ThreadList } from './ChatSidebarThreadList';
import { PaginationControls, Footer } from './ChatSidebarFooter';
import { FilterType } from './ChatSidebarTypes';

export const ChatSidebar: React.FC = () => {
  const { isProcessing, activeThreadId } = useUnifiedChatStore();
  const { sendMessage } = useWebSocket();
  const { isDeveloperOrHigher } = useAuthStore();
  const { isAuthenticated, userTier } = useAuthState();
  const isAdmin = isDeveloperOrHigher();
  
  const {
    searchQuery, setSearchQuery,
    isCreatingThread, setIsCreatingThread,
    showAllThreads, setShowAllThreads,
    filterType, setFilterType,
    currentPage, setCurrentPage
  } = useChatSidebarState();
  
  const threadsPerPage = 50;





  // Use the proper thread switching hook
  const { switchToThread, state: threadSwitchState } = useThreadSwitching();

  // Create thread click handler using the hook properly without double-wrapping
  const handleThreadClick = useCallback(async (threadId: string) => {
    // Prevent switching if already on the same thread
    if (threadId === activeThreadId) {
      return;
    }

    // Prevent switching if processing is in progress
    if (isProcessing) {
      console.warn('Cannot switch threads while processing is in progress');
      return;
    }

    // Check if we're already loading this specific thread
    if (threadSwitchState.isLoading && threadSwitchState.loadingThreadId === threadId) {
      console.warn(`Already loading thread ${threadId}`);
      return;
    }

    // Check if an operation is already in progress using the ThreadOperationManager directly
    // This prevents starting a duplicate operation before the hook even tries
    if (ThreadOperationManager.isOperationInProgress('switch', threadId)) {
      console.warn(`Thread switch to ${threadId} already in progress - skipping`);
      return;
    }
    
    try {
      // Determine if we should force the operation
      // Force is needed when switching from one loading thread to another
      const shouldForce = threadSwitchState.isLoading && 
                         threadSwitchState.loadingThreadId !== null &&
                         threadSwitchState.loadingThreadId !== threadId;
      
      // Use the switchToThread hook which already handles ThreadOperationManager internally
      // DO NOT wrap this in another ThreadOperationManager.startOperation call!
      const success = await switchToThread(threadId, {
        clearMessages: true,
        showLoadingIndicator: true,
        updateUrl: true,
        force: shouldForce, // This will be passed to ThreadOperationManager inside the hook
        skipDuplicateCheck: true // Skip duplicate check since we already checked above
      });
      
      if (success) {
        // Send WebSocket notification after successful switch
        sendMessage({
          type: 'switch_thread',
          payload: { thread_id: threadId }
        });
      } else if (threadSwitchState.error) {
        // Only log real errors, not mutex blocks
        const errorMessage = threadSwitchState.error.message || '';
        if (!errorMessage.includes('Operation already in progress') && 
            !errorMessage.includes('debounced') &&
            !errorMessage.includes('aborted')) {
          console.error('Failed to switch thread:', threadSwitchState.error);
        }
      }
    } catch (error) {
      // Handle unexpected errors only
      if (error instanceof Error) {
        const errorMessage = error.message;
        if (!errorMessage.includes('Operation already in progress') && 
            !errorMessage.includes('debounced') &&
            !errorMessage.includes('aborted')) {
          console.error('Unexpected error switching thread:', error);
        }
      }
    }
  }, [activeThreadId, isProcessing, threadSwitchState, sendMessage, switchToThread]);
  
  const { threads, isLoadingThreads, loadError, loadThreads } = useThreadLoader(
    showAllThreads,
    filterType,
    activeThreadId,
    handleThreadClick
  );
  
  // Handle new chat creation with state machine and proper thread switching
  const handleNewChat = useCallback(async () => {
    const stateMachine = threadStateMachineManager.getStateMachine('newChat');
    
    // Check if we can transition to creating state
    if (!stateMachine.canTransition('START_CREATE')) {
      logger.warn('Cannot start new chat creation - state machine blocked');
      return;
    }
    
    // Start state machine transition
    const operationId = `create_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    stateMachine.transition('START_CREATE', {
      operationId,
      startTime: Date.now(),
      targetThreadId: null
    });
    
    // Use ThreadOperationManager with enhanced debouncing and mutex
    const result = await ThreadOperationManager.startOperation(
      'create',
      null,
      async (signal) => {
        // State machine guards against concurrent operations
        if (isCreatingThread || isProcessing || threadSwitchState.isLoading) {
          return { success: false, error: new Error('Operation already in progress') };
        }
        
        setIsCreatingThread(true);
        try {
          // Check for abort
          if (signal.aborted) {
            throw new Error('Operation aborted');
          }
          
          // Create the new thread
          const { ThreadService } = await import('@/services/threadService');
          const newThread = await ThreadService.createThread();
          
          // Check for abort again
          if (signal.aborted) {
            throw new Error('Operation aborted');
          }
          
          // Update state machine with target thread
          stateMachine.transition('START_SWITCH', {
            targetThreadId: newThread.id
          });
          
          // Use the thread switching hook with explicit URL management
          const switchSuccess = await switchToThread(newThread.id, {
            clearMessages: true,
            showLoadingIndicator: false, // We're already showing creation state
            updateUrl: true, // Critical: ensures URL is updated atomically
            skipUrlUpdate: false, // Ensure URL sync happens
            force: true // Force switch for new chat
          });
          
          if (switchSuccess) {
            // Reload the thread list to show the new thread
            await loadThreads();
            stateMachine.transition('COMPLETE_SUCCESS');
            return { success: true, threadId: newThread.id };
          } else {
            stateMachine.transition('COMPLETE_ERROR', { error: new Error('Failed to switch to new thread') });
            return { success: false, error: new Error('Failed to switch to new thread') };
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const errorObj = error instanceof Error ? error : new Error(errorMessage);
          console.error('Failed to create thread:', errorObj);
          stateMachine.transition('COMPLETE_ERROR', { error: errorObj });
          return { success: false, error: errorObj };
        } finally {
          setIsCreatingThread(false);
        }
      },
      {
        timeoutMs: 10000,
        retryAttempts: 1,
        force: false // Let the enhanced mutex handle concurrency instead of forcing
      }
    );
    
    if (!result.success) {
      console.error('Failed to create new chat:', result.error);
      stateMachine.transition('COMPLETE_ERROR', { error: result.error });
    }
  }, [isCreatingThread, isProcessing, threadSwitchState.isLoading, switchToThread, loadThreads]);
  
  const { sortedThreads, paginatedThreads, totalPages } = useThreadFiltering(
    threads,
    searchQuery,
    threadsPerPage,
    currentPage
  );
  
  const handleFilterChange = (type: FilterType) => {
    setFilterType(type);
    setCurrentPage(1);
  };
  
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  return (
    <div className="w-80 h-full bg-white/95 backdrop-blur-md border-r border-gray-200 flex flex-col" data-testid="chat-sidebar" role="complementary">
      {/* Header with New Chat Button - Auth Protected */}
      <AuthGate 
        showLoginPrompt={false}
        fallback={
          <div className="p-4 border-b border-gray-200">
            <div className="w-full py-2 px-4 text-center text-gray-500 border border-gray-300 rounded-lg bg-gray-50">
              Sign in to start chatting
            </div>
          </div>
        }
      >
        <div className="p-4 border-b border-gray-200">
          <NewChatButton
            isCreatingThread={isCreatingThread}
            isProcessing={isProcessing}
            onNewChat={handleNewChat}
          />
        </div>
      </AuthGate>

      {/* Admin Controls - Developer+ Only */}
      <AuthGate requireTier="Mid" showLoginPrompt={false}>
        <AdminControls
          isAdmin={isAdmin}
          showAllThreads={showAllThreads}
          filterType={filterType}
          onToggleAllThreads={() => setShowAllThreads(!showAllThreads)}
          onFilterChange={handleFilterChange}
        />
      </AuthGate>

      {/* Search Bar - Auth Protected */}
      <AuthGate 
        showLoginPrompt={false}
        fallback={
          <div className="p-4">
            <div className="w-full py-2 px-3 text-gray-400 border border-gray-200 rounded-lg bg-gray-50">
              🔍 Search (Sign in required)
            </div>
          </div>
        }
      >
        <SearchBar
          searchQuery={searchQuery}
          showAllThreads={showAllThreads}
          onSearchChange={setSearchQuery}
        />
      </AuthGate>

      {/* Thread List - Auth Protected */}
      <AuthGate 
        showLoginPrompt={false}
        fallback={
          <div className="flex-1 p-4 text-center text-gray-500">
            <div className="mb-4">💬</div>
            <p className="text-sm">Your chat history will appear here</p>
            <p className="text-xs text-gray-400 mt-2">Sign in to view conversations</p>
          </div>
        }
      >
        <ThreadList
          threads={paginatedThreads}
          isLoadingThreads={isLoadingThreads}
          loadError={loadError}
          activeThreadId={activeThreadId}
          isProcessing={isProcessing}
          showAllThreads={showAllThreads}
          onThreadClick={handleThreadClick}
          onRetryLoad={loadThreads}
        />
      </AuthGate>

      {/* Pagination Controls - Auth Protected */}
      <AuthGate showLoginPrompt={false}>
        <PaginationControls
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      </AuthGate>

      {/* Footer with Thread Count and Quick Actions - Auth Protected */}
      <AuthGate showLoginPrompt={false}>
        <Footer
          threads={threads}
          paginatedThreads={paginatedThreads}
          threadsPerPage={threadsPerPage}
          isAdmin={isAdmin}
        />
      </AuthGate>
    </div>
  );
};