/**
 * Type definitions for ChatSidebar components
 * Centralizes all TypeScript interfaces and types for better maintainability
 */

export type FilterType = 'all' | 'corpus' | 'synthetic' | 'config' | 'users';

export interface FilterOption {
  key: FilterType;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}

export interface ChatSidebarState {
  searchQuery: string;
  isCreatingThread: boolean;
  showAllThreads: boolean;
  filterType: FilterType;
  currentPage: number;
  isLoadingThreads: boolean;
  loadError: string | null;
}

export interface PaginationConfig {
  threadsPerPage: number;
  currentPage: number;
  totalPages: number;
}

export interface Thread {
  id: string;
  title: string;
  created_at: number;
  updated_at?: number;
  message_count?: number;
  user_id?: string;
  metadata?: Record<string, unknown>;
}

export interface ThreadListProps {
  threads: Thread[];
  isLoadingThreads: boolean;
  loadError: string | null;
  activeThreadId: string | null;
  isProcessing: boolean;
  onThreadClick: (threadId: string) => Promise<void>;
  onRetryLoad: () => Promise<void>;
}

export interface AdminControlsProps {
  isAdmin: boolean;
  showAllThreads: boolean;
  filterType: FilterType;
  onToggleAllThreads: () => void;
  onFilterChange: (type: FilterType) => void;
}

export interface SearchBarProps {
  searchQuery: string;
  showAllThreads: boolean;
  onSearchChange: (query: string) => void;
}

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export interface FooterProps {
  threads: Thread[];
  paginatedThreads: Thread[];
  threadsPerPage: number;
  isAdmin: boolean;
}

export interface NewChatButtonProps {
  isCreatingThread: boolean;
  isProcessing: boolean;
  onNewChat: () => Promise<void>;
}