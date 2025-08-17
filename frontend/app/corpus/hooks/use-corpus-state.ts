import { useState } from 'react';
import { TabType, FilterType } from '../types/corpus';

export const useCorpusState = () => {
  const [activeTab, setActiveTab] = useState<TabType>('browse');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [expandedItems, setExpandedItems] = useState<string[]>(['1', '2']);
  const [filterType, setFilterType] = useState<FilterType>('all');

  const toggleExpand = (id: string) => {
    setExpandedItems(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const toggleSelect = (id: string) => {
    setSelectedItems(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  return {
    activeTab,
    setActiveTab,
    searchTerm,
    setSearchTerm,
    selectedItems,
    setSelectedItems,
    expandedItems,
    setExpandedItems,
    filterType,
    setFilterType,
    toggleExpand,
    toggleSelect,
  };
};