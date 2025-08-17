"use client";

import React from 'react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { 
  useChatSidebarState, 
  useThreadLoader, 
  useThreadFiltering 
} from './ChatSidebarHooks';
import { 
  createNewChatHandler, 
  createThreadClickHandler 
} from './ChatSidebarHandlers';
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
  const isAdmin = isDeveloperOrHigher();
  
  const {
    searchQuery, setSearchQuery,
    isCreatingThread, setIsCreatingThread,
    showAllThreads, setShowAllThreads,
    filterType, setFilterType,
    currentPage, setCurrentPage
  } = useChatSidebarState();
  
  const threadsPerPage = 50;





  // Create event handlers
  const handleThreadClick = createThreadClickHandler(
    activeThreadId, 
    isProcessing, 
    { sendMessage }
  );
  
  const { threads, isLoadingThreads, loadError, loadThreads } = useThreadLoader(
    showAllThreads,
    filterType,
    activeThreadId,
    handleThreadClick
  );
  
  const handleNewChat = createNewChatHandler(
    setIsCreatingThread,
    loadThreads
  );
  
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
    <div className="w-80 h-full bg-white/95 backdrop-blur-md border-r border-gray-200 flex flex-col">
      {/* Header with New Chat Button */}
      <div className="p-4 border-b border-gray-200">
        <NewChatButton
          isCreatingThread={isCreatingThread}
          isProcessing={isProcessing}
          onNewChat={handleNewChat}
        />
      </div>

      {/* Admin Controls */}
      <AdminControls
        isAdmin={isAdmin}
        showAllThreads={showAllThreads}
        filterType={filterType}
        onToggleAllThreads={() => setShowAllThreads(!showAllThreads)}
        onFilterChange={handleFilterChange}
      />

      {/* Search Bar */}
      <SearchBar
        searchQuery={searchQuery}
        showAllThreads={showAllThreads}
        onSearchChange={setSearchQuery}
      />

      {/* Thread List */}
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

      {/* Pagination Controls */}
      <PaginationControls
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={handlePageChange}
      />

      {/* Footer with Thread Count and Quick Actions */}
      <Footer
        threads={threads}
        paginatedThreads={paginatedThreads}
        threadsPerPage={threadsPerPage}
        isAdmin={isAdmin}
      />
    </div>
  );
};