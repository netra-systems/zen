'use client';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ChevronDown, ChevronRight, Eye, Edit, Download
} from 'lucide-react';
import { getTypeIcon, getAccessIcon, getStatusVariant } from './utils';
import type { CorpusItem as CorpusItemType } from './types';

interface CorpusItemProps {
  item: CorpusItemType;
  depth?: number;
  isExpanded: boolean;
  isSelected: boolean;
  onToggleExpand: (id: string) => void;
  onToggleSelect: (id: string) => void;
}

const ItemActions: React.FC = () => (
  <div className="flex gap-2">
    <Button size="sm" variant="ghost">
      <Eye className="h-4 w-4" />
    </Button>
    <Button size="sm" variant="ghost">
      <Edit className="h-4 w-4" />
    </Button>
    <Button size="sm" variant="ghost">
      <Download className="h-4 w-4" />
    </Button>
  </div>
);

const ItemContent: React.FC<{ item: CorpusItemType }> = ({ item }) => (
  <div className="flex-1">
    <div className="flex items-center gap-2">
      <span className="font-medium">{item.name}</span>
      <Badge variant={getStatusVariant(item.status)}>
        {item.status}
      </Badge>
      {getAccessIcon(item.accessLevel)}
      <Badge variant="outline" className="text-xs">
        {item.version}
      </Badge>
    </div>
    <div className="flex gap-4 text-sm text-muted-foreground mt-1">
      <span>{item.records} items</span>
      <span>{item.size}</span>
      <span>{item.lastModified}</span>
      <span>by {item.owner}</span>
    </div>
  </div>
);

const ExpandToggle: React.FC<{
  hasChildren: boolean;
  isExpanded: boolean;
  onToggle: () => void;
}> = ({ hasChildren, isExpanded, onToggle }) => {
  if (!hasChildren) {
    return <div className="w-5" />;
  }

  return (
    <button onClick={onToggle} className="p-0.5">
      {isExpanded ? (
        <ChevronDown className="h-4 w-4" />
      ) : (
        <ChevronRight className="h-4 w-4" />
      )}
    </button>
  );
};

export const CorpusItem: React.FC<CorpusItemProps> = ({
  item,
  depth = 0,
  isExpanded,
  isSelected,
  onToggleExpand,
  onToggleSelect
}) => {
  const hasChildren = item.children && item.children.length > 0;

  const handleExpandToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleExpand(item.id);
  };

  const handleItemClick = () => {
    onToggleSelect(item.id);
  };

  return (
    <div>
      <div
        className={`flex items-center gap-3 p-3 hover:bg-muted/50 rounded-lg cursor-pointer ${
          isSelected ? 'bg-muted' : ''
        }`}
        style={{ paddingLeft: `${depth * 24 + 12}px` }}
        onClick={handleItemClick}
      >
        <ExpandToggle
          hasChildren={hasChildren}
          isExpanded={isExpanded}
          onToggle={handleExpandToggle}
        />
        
        {getTypeIcon(item.type)}
        
        <ItemContent item={item} />
        
        <div onClick={(e) => e.stopPropagation()}>
          <ItemActions />
        </div>
      </div>
      
      {hasChildren && isExpanded && (
        <div>
          {item.children!.map(child => (
            <CorpusItem
              key={child.id}
              item={child}
              depth={depth + 1}
              isExpanded={false}
              isSelected={false}
              onToggleExpand={onToggleExpand}
              onToggleSelect={onToggleSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};