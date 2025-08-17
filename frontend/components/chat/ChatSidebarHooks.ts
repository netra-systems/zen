/**
 * Custom hooks for ChatSidebar component
 * Manages thread state, loading, and filtering logic with ≤8 line functions
 */

import { useState, useEffect } from 'react';
import { Thread, ThreadService } from '@/services/threadService';
import { ChatSidebarState, FilterType } from './ChatSidebarTypes';

export const useChatSidebarState = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreatingThread, setIsCreatingThread] = useState(false);
  const [showAllThreads, setShowAllThreads] = useState(false);
  const [filterType, setFilterType] = useState<FilterType>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  return {
    searchQuery, setSearchQuery,
    isCreatingThread, setIsCreatingThread,
    showAllThreads, setShowAllThreads,
    filterType, setFilterType,
    currentPage, setCurrentPage,
    isLoadingThreads, setIsLoadingThreads,
    loadError, setLoadError
  };
};

export const useThreadLoader = (
  showAllThreads: boolean,
  filterType: FilterType,
  activeThreadId: string | null,
  onThreadClick: (threadId: string) => Promise<void>
) => {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const clearError = () => {
    setLoadError(null);
  };

  const setLoading = (loading: boolean) => {
    setIsLoadingThreads(loading);
  };

  const handleLoadError = (error: unknown) => {
    const errorMessage = error instanceof Error ? error.message : 'Failed to load threads';
    console.error('Failed to load threads:', errorMessage);
    setLoadError(errorMessage);
    setThreads([]);
  };

  const handleLoadSuccess = async (fetchedThreads: Thread[]) => {
    setThreads(fetchedThreads);
    if (!activeThreadId && fetchedThreads.length > 0) {
      await onThreadClick(fetchedThreads[0].id);
    }
  };

  const loadThreads = async () => {
    setLoading(true);
    clearError();
    try {
      const fetchedThreads = await ThreadService.listThreads();
      await handleLoadSuccess(fetchedThreads);
    } catch (error) {
      handleLoadError(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadThreads();
  }, [showAllThreads, filterType]);

  return {
    threads,
    isLoadingThreads,
    loadError,
    loadThreads
  };
};

export const useThreadFiltering = (
  threads: Thread[],
  searchQuery: string,
  threadsPerPage: number,
  currentPage: number
) => {
  const filterBySearch = (thread: Thread) => {
    if (!searchQuery) return true;
    const title = thread.metadata?.title || thread.title || `Chat ${thread.created_at}`;
    const lastMessage = thread.metadata?.last_message as string | undefined;
    return title.toLowerCase().includes(searchQuery.toLowerCase()) ||
           lastMessage?.toLowerCase().includes(searchQuery.toLowerCase());
  };

  const sortByUpdate = (a: Thread, b: Thread) => {
    const aTime = a.updated_at || a.created_at;
    const bTime = b.updated_at || b.created_at;
    return bTime - aTime;
  };

  const filteredThreads = threads.filter(filterBySearch);
  const sortedThreads = filteredThreads.sort(sortByUpdate);
  
  const totalPages = Math.ceil(sortedThreads.length / threadsPerPage);
  const paginatedThreads = sortedThreads.slice(
    (currentPage - 1) * threadsPerPage,
    currentPage * threadsPerPage
  );

  return {
    sortedThreads,
    paginatedThreads,
    totalPages
  };
};