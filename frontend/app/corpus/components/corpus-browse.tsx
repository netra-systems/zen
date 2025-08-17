import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search, Filter, Copy, Archive, Share2, Trash2 } from 'lucide-react';
import { CorpusItem, FilterType } from '../types/corpus';
import { CorpusItemRow } from './corpus-item';
import { filterCorpusData } from '../utils/corpus-utils';

interface CorpusBrowseProps {
  corpusData: CorpusItem[];
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  filterType: FilterType;
  setFilterType: (type: FilterType) => void;
  selectedItems: string[];
  expandedItems: string[];
  onToggleExpand: (id: string) => void;
  onToggleSelect: (id: string) => void;
}

export const CorpusBrowse = ({
  corpusData,
  searchTerm,
  setSearchTerm,
  filterType,
  setFilterType,
  selectedItems,
  expandedItems,
  onToggleExpand,
  onToggleSelect,
}: CorpusBrowseProps) => {
  const filteredData = filterCorpusData(corpusData, filterType, searchTerm);

  return (
    <Card>
      <CardHeader>
        <BrowseHeader 
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          filterType={filterType}
          setFilterType={setFilterType}
        />
      </CardHeader>
      <CardContent>
        <BrowseContent 
          filteredData={filteredData}
          selectedItems={selectedItems}
          expandedItems={expandedItems}
          onToggleExpand={onToggleExpand}
          onToggleSelect={onToggleSelect}
        />
      </CardContent>
    </Card>
  );
};

const BrowseHeader = ({ 
  searchTerm, 
  setSearchTerm, 
  filterType, 
  setFilterType 
}: {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  filterType: FilterType;
  setFilterType: (type: FilterType) => void;
}) => {
  return (
    <div className="flex justify-between items-center">
      <CardTitle>Data Collections</CardTitle>
      <div className="flex gap-3">
        <SearchInput searchTerm={searchTerm} setSearchTerm={setSearchTerm} />
        <FilterSelect filterType={filterType} setFilterType={setFilterType} />
        <Button variant="outline" size="icon">
          <Filter className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};

const SearchInput = ({ 
  searchTerm, 
  setSearchTerm 
}: { 
  searchTerm: string; 
  setSearchTerm: (term: string) => void; 
}) => {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        placeholder="Search corpus..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="pl-9 w-64"
      />
    </div>
  );
};

const FilterSelect = ({ 
  filterType, 
  setFilterType 
}: { 
  filterType: FilterType; 
  setFilterType: (type: FilterType) => void; 
}) => {
  return (
    <Select value={filterType} onValueChange={setFilterType}>
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
  );
};

const BrowseContent = ({ 
  filteredData, 
  selectedItems, 
  expandedItems, 
  onToggleExpand, 
  onToggleSelect 
}: {
  filteredData: CorpusItem[];
  selectedItems: string[];
  expandedItems: string[];
  onToggleExpand: (id: string) => void;
  onToggleSelect: (id: string) => void;
}) => {
  return (
    <>
      <div className="border rounded-lg">
        {filteredData.map(item => (
          <CorpusItemRow
            key={item.id}
            item={item}
            isExpanded={expandedItems.includes(item.id)}
            isSelected={selectedItems.includes(item.id)}
            onToggleExpand={onToggleExpand}
            onToggleSelect={onToggleSelect}
          />
        ))}
      </div>
      {selectedItems.length > 0 && (
        <SelectionActions selectedCount={selectedItems.length} />
      )}
    </>
  );
};

const SelectionActions = ({ selectedCount }: { selectedCount: number }) => {
  return (
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
};