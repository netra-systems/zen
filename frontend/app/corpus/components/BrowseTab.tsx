'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Search, Filter, Copy, Archive, Share2, Trash2
} from 'lucide-react';
import { CorpusItem } from './CorpusItem';
import type { CorpusItem as CorpusItemType } from './types';

interface BrowseTabProps {
  corpusData: CorpusItemType[];
}

const SearchAndFilters: React.FC<{
  searchTerm: string;
  filterType: string;
  onSearchChange: (value: string) => void;
  onFilterChange: (value: string) => void;
}> = ({ searchTerm, filterType, onSearchChange, onFilterChange }) => (
  <div className="flex gap-3">
    <div className="relative">
      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        placeholder="Search corpus..."
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
        className="pl-9 w-64"
      />
    </div>
    <Select value={filterType} onValueChange={onFilterChange}>
      <SelectTrigger className="w-32">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All Types</SelectItem>
        <SelectItem value="collection">Collections</SelectItem>
        <SelectItem value="dataset">Datasets</SelectItem>
        <SelectItem value="model">Models</SelectItem>
        <SelectItem value="embedding">Embeddings</SelectItem>
      </SelectContent>
    </Select>
    <Button variant="outline" size="icon">
      <Filter className="h-4 w-4" />
    </Button>
  </div>
);

const BulkActions: React.FC<{ selectedCount: number }> = ({ selectedCount }) => (
  <div className="mt-4 p-4 bg-muted rounded-lg flex justify-between items-center">
    <span className="text-sm">{selectedCount} items selected</span>
    <div className="flex gap-2">
      <Button size="sm" variant="outline">
        <Copy className="mr-2 h-4 w-4" />
        Duplicate
      </Button>
      <Button size="sm" variant="outline">
        <Archive className="mr-2 h-4 w-4" />
        Archive
      </Button>
      <Button size="sm" variant="outline">
        <Share2 className="mr-2 h-4 w-4" />
        Share
      </Button>
      <Button size="sm" variant="destructive">
        <Trash2 className="mr-2 h-4 w-4" />
        Delete
      </Button>
    </div>
  </div>
);

export const BrowseTab: React.FC<BrowseTabProps> = ({ corpusData }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [expandedItems, setExpandedItems] = useState<string[]>(['1', '2']);
  const [filterType, setFilterType] = useState('all');

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

  const filteredData = corpusData.filter(item => 
    (filterType === 'all' || item.type === filterType) &&
    (searchTerm === '' || item.name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Data Collections</CardTitle>
          <SearchAndFilters
            searchTerm={searchTerm}
            filterType={filterType}
            onSearchChange={setSearchTerm}
            onFilterChange={setFilterType}
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="border rounded-lg">
          {filteredData.map(item => (
            <CorpusItem
              key={item.id}
              item={item}
              isExpanded={expandedItems.includes(item.id)}
              isSelected={selectedItems.includes(item.id)}
              onToggleExpand={toggleExpand}
              onToggleSelect={toggleSelect}
            />
          ))}
        </div>
        {selectedItems.length > 0 && (
          <BulkActions selectedCount={selectedItems.length} />
        )}
      </CardContent>
    </Card>
  );
};