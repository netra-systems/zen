"use client";

import React, { useCallback } from 'react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import { useAuthState } from '@/hooks/useAuthState';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { ThreadOperationManager } from '@/lib/thread-operation-manager';
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

  // Create thread click handler using the hook
  const handleThreadClick = useCallback(async (threadId: string) => {
    // Prevent switching if already on the same thread
    if (threadId === activeThreadId) {
      return;
    }
    
    // Use ThreadOperationManager to ensure atomic operation
    const result = await ThreadOperationManager.startOperation(
      'switch',
      threadId,
      async (signal) => {
        // Check if another operation is blocking
        if (ThreadOperationManager.isOperationInProgress('create')) {
          return { success: false, error: new Error('New chat creation in progress') };
        }
        
        // Check for abort
        if (signal.aborted) {
          return { success: false, error: new Error('Operation aborted') };
        }
        
        // Send WebSocket message for thread switch notification
        sendMessage({
          type: 'switch_thread',
          payload: { thread_id: threadId }
        });
        
        // Use the hook to perform the actual thread switch
        // The hook handles all state management, loading, and cleanup
        const success = await switchToThread(threadId, {
          clearMessages: true,
          showLoadingIndicator: true,
          updateUrl: true
        });
        
        return { success, threadId };
      },
      {
        timeoutMs: 5000,
        retryAttempts: 2
      }
    );
    
    if (!result.success) {
      console.error('Failed to switch thread:', result.error);
    }
  }, [activeThreadId, sendMessage, switchToThread]);
  
  const { threads, isLoadingThreads, loadError, loadThreads } = useThreadLoader(
    showAllThreads,
    filterType,
    activeThreadId,
    handleThreadClick
  );
  
  // Handle new chat creation with proper thread switching
  const handleNewChat = useCallback(async () => {
    // Use ThreadOperationManager to ensure atomic operation
    const result = await ThreadOperationManager.startOperation(
      'create',
      null,
      async (signal) => {
        // Prevent double-clicks and concurrent creation
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
          
          // Use the thread switching hook to properly navigate to the new thread
          // Force the switch to ensure it happens even if another operation is pending
          const switchSuccess = await switchToThread(newThread.id, {
            clearMessages: true,
            showLoadingIndicator: false, // We're already showing creation state
            updateUrl: true, // Critical: ensures URL is updated
            force: true // Force switch for new chat
          });
          
          if (switchSuccess) {
            // Reload the thread list to show the new thread
            await loadThreads();
            return { success: true, threadId: newThread.id };
          } else {
            return { success: false, error: new Error('Failed to switch to new thread') };
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const errorObj = error instanceof Error ? error : new Error(errorMessage);
          console.error('Failed to create thread:', errorObj);
          return { success: false, error: errorObj };
        } finally {
          setIsCreatingThread(false);
        }
      },
      {
        timeoutMs: 10000,
        retryAttempts: 1,
        force: true // Force new chat creation
      }
    );
    
    if (!result.success) {
      console.error('Failed to create new chat:', result.error);
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