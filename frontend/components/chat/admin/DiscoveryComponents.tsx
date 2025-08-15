/**
 * Rendering components for Corpus Discovery Panel
 * All functions ≤8 lines, glassmorphic design without blue gradients
 */

import React from 'react';
import { ChevronRight, Search, Info, Sparkles } from 'lucide-react';
import { cn } from '../../../lib/utils';
import { generateUniqueId } from '../../../lib/utils';
import { DiscoveryCategory, ConfigOption } from './types';

interface CategoryProps {
  category: DiscoveryCategory;
  isExpanded: boolean;
  onCategorySelect: (name: string) => void;
  onOptionSelect: (category: DiscoveryCategory, option: ConfigOption) => void;
}

export const CategorySection: React.FC<CategoryProps> = ({
  category,
  isExpanded,
  onCategorySelect,
  onOptionSelect
}) => (
  <div key={category.name} className="mb-4">
    <CategoryButton
      category={category}
      isExpanded={isExpanded}
      onClick={() => onCategorySelect(category.name)}
    />
    {isExpanded && (
      <OptionsList category={category} onOptionSelect={onOptionSelect} />
    )}
  </div>
);

interface CategoryButtonProps {
  category: DiscoveryCategory;
  isExpanded: boolean;
  onClick: () => void;
}

const CategoryButton: React.FC<CategoryButtonProps> = ({
  category,
  isExpanded,
  onClick
}) => (
  <button
    onClick={onClick}
    className={cn(
      "w-full p-4 rounded-lg transition-all",
      "bg-white/5 backdrop-blur-md border border-white/10",
      "hover:bg-white/10 hover:border-white/20",
      isExpanded && "bg-white/10 border-white/20"
    )}
  >
    <CategoryContent category={category} isExpanded={isExpanded} />
  </button>
);

interface CategoryContentProps {
  category: DiscoveryCategory;
  isExpanded: boolean;
}

const CategoryContent: React.FC<CategoryContentProps> = ({
  category,
  isExpanded
}) => (
  <div className="flex items-center justify-between">
    <div className="flex items-center gap-3">
      <ChevronIcon isExpanded={isExpanded} />
      <CategoryInfo category={category} />
    </div>
  </div>
);

interface ChevronIconProps {
  isExpanded: boolean;
}

const ChevronIcon: React.FC<ChevronIconProps> = ({ isExpanded }) => (
  <ChevronRight
    className={cn(
      "w-5 h-5 transition-transform",
      isExpanded && "rotate-90"
    )}
  />
);

interface CategoryInfoProps {
  category: DiscoveryCategory;
}

const CategoryInfo: React.FC<CategoryInfoProps> = ({ category }) => (
  <div className="text-left">
    <h3 className="font-medium">{category.name}</h3>
    <p className="text-sm text-gray-400 mt-1">{category.description}</p>
  </div>
);

interface OptionsListProps {
  category: DiscoveryCategory;
  onOptionSelect: (category: DiscoveryCategory, option: ConfigOption) => void;
}

const OptionsList: React.FC<OptionsListProps> = ({
  category,
  onOptionSelect
}) => (
  <div className="mt-2 space-y-2 pl-8">
    {category.options.map(option => (
      <OptionButton
        key={option.id}
        option={option}
        onClick={() => onOptionSelect(category, option)}
      />
    ))}
  </div>
);

interface OptionButtonProps {
  option: ConfigOption;
  onClick: () => void;
}

const OptionButton: React.FC<OptionButtonProps> = ({ option, onClick }) => (
  <button
    onClick={onClick}
    className={cn(
      "w-full p-3 rounded-lg text-left transition-all",
      "bg-white/5 backdrop-blur-sm border border-white/10",
      "hover:bg-white/10 hover:border-white/20",
      option.recommended && "border-green-500/30"
    )}
  >
    <OptionContent option={option} />
  </button>
);

interface OptionContentProps {
  option: ConfigOption;
}

const OptionContent: React.FC<OptionContentProps> = ({ option }) => (
  <div className="flex items-start justify-between">
    <div className="flex-1">
      <OptionHeader option={option} />
      <OptionDescription option={option} />
    </div>
  </div>
);

const OptionHeader: React.FC<OptionContentProps> = ({ option }) => (
  <div className="flex items-center gap-2">
    <span className="font-medium">{option.label}</span>
    {option.recommended && <Sparkles className="w-4 h-4 text-green-400" />}
  </div>
);

const OptionDescription: React.FC<OptionContentProps> = ({ option }) =>
  option.description ? (
    <p className="text-sm text-gray-400 mt-1">{option.description}</p>
  ) : null;

interface SearchBarProps {
  searchQuery: string;
  onSearch: (query: string) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  searchQuery,
  onSearch
}) => (
  <div className="mb-6">
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
      <SearchInput searchQuery={searchQuery} onSearch={onSearch} />
    </div>
  </div>
);

interface SearchInputProps {
  searchQuery: string;
  onSearch: (query: string) => void;
}

const SearchInput: React.FC<SearchInputProps> = ({ searchQuery, onSearch }) => (
  <input
    type="text"
    value={searchQuery}
    onChange={(e) => onSearch(e.target.value)}
    placeholder="Search for corpus options..."
    className={cn(
      "w-full pl-10 pr-4 py-3 rounded-lg",
      "bg-white/5 backdrop-blur-sm border border-white/10",
      "focus:border-white/20 focus:outline-none placeholder-gray-500"
    )}
  />
);

interface SuggestionsProps {
  suggestions: string[];
}

export const SuggestionsPanel: React.FC<SuggestionsProps> = ({
  suggestions
}) => {
  if (suggestions.length === 0) return null;
  
  return (
    <div className="mt-4 p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
      <SuggestionsHeader />
      <SuggestionsList suggestions={suggestions} />
    </div>
  );
};

const SuggestionsHeader: React.FC = () => (
  <div className="flex items-start gap-2">
    <Info className="w-5 h-5 text-purple-400 mt-0.5" />
    <h4 className="font-medium text-purple-300 mb-2">Suggestions</h4>
  </div>
);

interface SuggestionsListProps {
  suggestions: string[];
}

const SuggestionsList: React.FC<SuggestionsListProps> = ({ suggestions }) => (
  <ul className="space-y-1 ml-7">
    {suggestions.map((suggestion) => (
      <li key={generateUniqueId('suggestion')} className="text-sm text-gray-300">
        {suggestion}
      </li>
    ))}
  </ul>
);

export const LoadingSpinner: React.FC = () => (
  <div className="flex items-center justify-center py-12">
    <div className="animate-spin rounded-full h-8 w-8 border-2 border-white/20 border-t-white/60" />
  </div>
);