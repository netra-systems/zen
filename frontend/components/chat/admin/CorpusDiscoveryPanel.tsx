/**
 * Corpus Discovery Panel Component
 * 
 * Interactive UI for discovering corpus options and configurations.
 * Follows glassmorphic design with 300-line limit.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { ChevronRight, Search, Info, Sparkles } from 'lucide-react';
import { generateUniqueId } from '../../../lib/utils';
import { useWebSocket } from '../../../hooks/useWebSocket';
import { cn } from '../../../lib/utils';

interface DiscoveryCategory {
  name: string;
  description: string;
  options: ConfigOption[];
}

interface ConfigOption {
  id: string;
  label: string;
  value: string;
  description?: string;
  recommended?: boolean;
}

interface CorpusDiscoveryPanelProps {
  onDiscoverySelect: (category: string, option: ConfigOption) => void;
  sessionId: string;
  className?: string;
}

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
    sendMessage({
      message_type: 'corpus_discovery_request',
      intent: 'discover',
      query: 'list available corpus options',
      session_id: sessionId
    });
  }, [sendMessage, sessionId]);

  const handleWebSocketMessage = useCallback(() => {
    if (!lastMessage) return;
    
    if (lastMessage.message_type === 'corpus_discovery_response') {
      processDiscoveryResponse(lastMessage);
      setLoading(false);
    }
  }, [lastMessage]);

  const processDiscoveryResponse = (response: any) => {
    const newCategories: DiscoveryCategory[] = [
      createWorkloadCategory(response),
      createDomainCategory(response),
      createParameterCategory(response)
    ];
    setCategories(newCategories);
    setSuggestions(response.suggestions || []);
  };

  const createWorkloadCategory = (response: any): DiscoveryCategory => {
    return {
      name: 'Workload Types',
      description: 'Choose the type of workload for your corpus',
      options: (response.items || []).map((item: any) => ({
        id: generateUniqueId('workload'),
        label: item.name,
        value: item.id,
        description: item.description,
        recommended: item.recommended
      }))
    };
  };

  const createDomainCategory = (response: any): DiscoveryCategory => {
    const domains = ['ecommerce', 'fintech', 'healthcare', 'saas', 'iot'];
    return {
      name: 'Domain',
      description: 'Select your business domain',
      options: domains.map(domain => ({
        id: generateUniqueId('domain'),
        label: domain.charAt(0).toUpperCase() + domain.slice(1),
        value: domain,
        description: `Optimized for ${domain} use cases`
      }))
    };
  };

  const createParameterCategory = (response: any): DiscoveryCategory => {
    return {
      name: 'Generation Parameters',
      description: 'Configure generation settings',
      options: [
        {
          id: generateUniqueId('param'),
          label: 'Performance Optimized',
          value: 'performance',
          description: 'Fast generation with high throughput'
        },
        {
          id: generateUniqueId('param'),
          label: 'Quality Focused',
          value: 'quality',
          description: 'High accuracy and data integrity'
        },
        {
          id: generateUniqueId('param'),
          label: 'Balanced',
          value: 'balanced',
          description: 'Balance between speed and quality',
          recommended: true
        }
      ]
    };
  };

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    if (query.length > 2) {
      requestAutoComplete(query);
    }
  }, []);

  const requestAutoComplete = (query: string) => {
    sendMessage({
      message_type: 'corpus_autocomplete_request',
      partial_input: query,
      category: selectedCategory || 'all',
      session_id: sessionId
    });
  };

  const handleCategorySelect = (categoryName: string) => {
    setSelectedCategory(categoryName === selectedCategory ? null : categoryName);
  };

  const handleOptionSelect = (category: DiscoveryCategory, option: ConfigOption) => {
    onDiscoverySelect(category.name, option);
  };

  const renderCategory = (category: DiscoveryCategory) => {
    const isExpanded = selectedCategory === category.name;
    
    return (
      <div key={category.name} className="mb-4">
        <button
          onClick={() => handleCategorySelect(category.name)}
          className={cn(
            "w-full p-4 rounded-lg transition-all",
            "bg-white/5 backdrop-blur-md border border-white/10",
            "hover:bg-white/10 hover:border-white/20",
            isExpanded && "bg-white/10 border-white/20"
          )}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ChevronRight
                className={cn(
                  "w-5 h-5 transition-transform",
                  isExpanded && "rotate-90"
                )}
              />
              <div className="text-left">
                <h3 className="font-medium">{category.name}</h3>
                <p className="text-sm text-gray-400 mt-1">
                  {category.description}
                </p>
              </div>
            </div>
          </div>
        </button>
        
        {isExpanded && (
          <div className="mt-2 space-y-2 pl-8">
            {renderOptions(category)}
          </div>
        )}
      </div>
    );
  };

  const renderOptions = (category: DiscoveryCategory) => {
    return category.options.map(option => (
      <button
        key={option.id}
        onClick={() => handleOptionSelect(category, option)}
        className={cn(
          "w-full p-3 rounded-lg text-left transition-all",
          "bg-white/5 backdrop-blur-sm border border-white/10",
          "hover:bg-white/10 hover:border-white/20",
          option.recommended && "border-green-500/30"
        )}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-medium">{option.label}</span>
              {option.recommended && (
                <Sparkles className="w-4 h-4 text-green-400" />
              )}
            </div>
            {option.description && (
              <p className="text-sm text-gray-400 mt-1">
                {option.description}
              </p>
            )}
          </div>
        </div>
      </button>
    ));
  };

  const renderSuggestions = () => {
    if (suggestions.length === 0) return null;
    
    return (
      <div className="mt-4 p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
        <div className="flex items-start gap-2">
          <Info className="w-5 h-5 text-blue-400 mt-0.5" />
          <div>
            <h4 className="font-medium text-blue-300 mb-2">Suggestions</h4>
            <ul className="space-y-1">
              {suggestions.map((suggestion, idx) => (
                <li key={generateUniqueId('suggestion')} className="text-sm text-gray-300">
                  {suggestion}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className={cn(
      "rounded-xl p-6",
      "bg-gray-900/50 backdrop-blur-xl",
      "border border-gray-700/50",
      className
    )}>
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Corpus Discovery</h2>
        <p className="text-gray-400">
          Explore and configure corpus generation options
        </p>
      </div>

      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search for corpus options..."
            className={cn(
              "w-full pl-10 pr-4 py-3 rounded-lg",
              "bg-white/5 backdrop-blur-sm",
              "border border-white/10",
              "focus:border-white/20 focus:outline-none",
              "placeholder-gray-500"
            )}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-white/20 border-t-white/60" />
        </div>
      ) : (
        <div className="space-y-2">
          {categories.map(renderCategory)}
          {renderSuggestions()}
        </div>
      )}
    </div>
  );
};

export default CorpusDiscoveryPanel;