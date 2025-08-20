/**
 * Corpus Discovery Panel Component
 * 
 * Interactive UI for discovering corpus options and configurations.
 * Follows glassmorphic design with 450-line limit and 25-line function limit.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useWebSocket } from '../../../hooks/useWebSocket';
import { cn } from '../../../lib/utils';
import { 
  CorpusDiscoveryPanelProps, 
  DiscoveryCategory, 
  ConfigOption, 
  WebSocketMessage,
  DiscoveryResponse 
} from './types';
import { processDiscoveryResponse, extractSuggestions } from './categoryHandlers';
import { CategorySection, SearchBar, SuggestionsPanel, LoadingSpinner } from './DiscoveryComponents';

const CorpusDiscoveryPanel: React.FC<CorpusDiscoveryPanelProps> = ({
  onDiscoverySelect,
  sessionId,
  className
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [categories, setCategories] = useState<DiscoveryCategory[]>([]);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  
  const { sendMessage, lastMessage } = useWebSocket();

  useEffect(() => {
    loadDiscoveryCategories();
  }, []);

  useEffect(() => {
    handleWebSocketMessage();
  }, [lastMessage]);

  const loadDiscoveryCategories = useCallback(async () => {
    setLoading(true);
    const message: WebSocketMessage = {
      message_type: 'corpus_discovery_request',
      intent: 'discover',
      query: 'list available corpus options',
      session_id: sessionId
    };
    sendMessage(message);
  }, [sendMessage, sessionId]);

  const handleWebSocketMessage = useCallback(() => {
    if (!lastMessage) return;
    if (lastMessage.message_type === 'corpus_discovery_response') {
      handleDiscoveryResponse(lastMessage);
    }
  }, [lastMessage]);

  const handleDiscoveryResponse = (response: DiscoveryResponse) => {
    const newCategories = processDiscoveryResponse(response);
    const newSuggestions = extractSuggestions(response);
    setCategories(newCategories);
    setSuggestions(newSuggestions);
    setLoading(false);
  };

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    if (query.length > 2) {
      requestAutoComplete(query);
    }
  }, [sessionId, sendMessage, selectedCategory]);

  const requestAutoComplete = useCallback((query: string) => {
    const message: WebSocketMessage = {
      message_type: 'corpus_autocomplete_request',
      partial_input: query,
      category: selectedCategory || 'all',
      session_id: sessionId
    };
    sendMessage(message);
  }, [sendMessage, sessionId, selectedCategory]);

  const handleCategorySelect = useCallback((categoryName: string) => {
    const newCategory = categoryName === selectedCategory ? null : categoryName;
    setSelectedCategory(newCategory);
  }, [selectedCategory]);

  const handleOptionSelect = useCallback((category: DiscoveryCategory, option: ConfigOption) => {
    onDiscoverySelect(category.name, option);
  }, [onDiscoverySelect]);

  const renderCategory = useCallback((category: DiscoveryCategory) => {
    const isExpanded = selectedCategory === category.name;
    return (
      <CategorySection
        key={category.name}
        category={category}
        isExpanded={isExpanded}
        onCategorySelect={handleCategorySelect}
        onOptionSelect={handleOptionSelect}
      />
    );
  }, [selectedCategory, handleCategorySelect, handleOptionSelect]);

  return (
    <div className={cn(
      "rounded-xl p-6",
      "bg-gray-900/50 backdrop-blur-xl",
      "border border-gray-700/50",
      className
    )}>
      <PanelHeader />
      <SearchBar searchQuery={searchQuery} onSearch={handleSearch} />

      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="space-y-2">
          {categories.map(renderCategory)}
          <SuggestionsPanel suggestions={suggestions} />
        </div>
      )}
    </div>
  );
};

const PanelHeader: React.FC = () => (
  <div className="mb-6">
    <h2 className="text-xl font-semibold mb-2">Corpus Discovery</h2>
    <p className="text-gray-400">
      Explore and configure corpus generation options
    </p>
  </div>
);

export default CorpusDiscoveryPanel;