/**
 * Type definitions for Corpus Discovery Panel
 * Strongly typed interfaces following type_safety.xml specifications
 */

export interface DiscoveryCategory {
  name: string;
  description: string;
  options: ConfigOption[];
}

export interface ConfigOption {
  id: string;
  label: string;
  value: string;
  description?: string;
  recommended?: boolean;
}

export interface CorpusDiscoveryPanelProps {
  onDiscoverySelect: (category: string, option: ConfigOption) => void;
  sessionId: string;
  className?: string;
}

export interface WebSocketMessage {
  message_type: string;
  intent?: string;
  query?: string;
  session_id: string;
  partial_input?: string;
  category?: string;
}

export interface DiscoveryResponse {
  message_type: string;
  items?: Array<{
    name: string;
    id: string;
    description: string;
    recommended?: boolean;
  }>;
  suggestions?: string[];
}

export interface CategoryHandlers {
  loadCategories: () => Promise<void>;
  handleSearch: (query: string) => void;
  handleCategorySelect: (categoryName: string) => void;
  handleOptionSelect: (category: DiscoveryCategory, option: ConfigOption) => void;
}

export interface DiscoveryState {
  searchQuery: string;
  selectedCategory: string | null;
  categories: DiscoveryCategory[];
  loading: boolean;
  suggestions: string[];
}