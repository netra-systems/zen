import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight, Eye, Edit, Download } from 'lucide-react';
import { CorpusItem } from '../types/corpus';
import { getTypeIcon, getAccessIcon, getStatusBadgeVariant } from '../utils/corpus-utils';

interface CorpusItemProps {
  item: CorpusItem;
  depth?: number;
  isExpanded: boolean;
  isSelected: boolean;
  onToggleExpand: (id: string) => void;
  onToggleSelect: (id: string) => void;
}

export const CorpusItemRow = ({ 
  item, 
  depth = 0, 
  isExpanded, 
  isSelected, 
  onToggleExpand, 
  onToggleSelect 
}: CorpusItemProps) => {
  const hasChildren = item.children && item.children.length > 0;

  return (
    <div>
      <ItemContent 
        item={item}
        depth={depth}
        hasChildren={hasChildren ?? false}
        isExpanded={isExpanded}
        isSelected={isSelected}
        onToggleExpand={onToggleExpand}
        onToggleSelect={onToggleSelect}
      />
      {hasChildren && isExpanded && (
        <ChildrenContainer 
          item={item}
          depth={depth}
          onToggleExpand={onToggleExpand}
          onToggleSelect={onToggleSelect}
        />
      )}
    </div>
  );
};

const ItemContent = ({ 
  item, 
  depth = 0, 
  hasChildren, 
  isExpanded, 
  isSelected, 
  onToggleExpand, 
  onToggleSelect 
}: CorpusItemProps & { hasChildren: boolean }) => {
  return (
    <div
      className={`flex items-center gap-3 p-3 hover:bg-muted/50 rounded-lg cursor-pointer ${
        isSelected ? 'bg-muted' : ''
      }`}
      style={{ paddingLeft: `${depth * 24 + 12}px` }}
      onClick={() => onToggleSelect(item.id)}
    >
      <ExpandButton 
        hasChildren={hasChildren}
        isExpanded={isExpanded}
        onToggleExpand={() => onToggleExpand(item.id)}
      />
      {getTypeIcon(item.type)}
      <ItemDetails item={item} />
      <ItemActions />
    </div>
  );
};

const ExpandButton = ({ 
  hasChildren, 
  isExpanded, 
  onToggleExpand 
}: { 
  hasChildren: boolean; 
  isExpanded: boolean; 
  onToggleExpand: () => void; 
}) => {
  if (!hasChildren) {
    return <div className="w-5" />;
  }

  return (
    <button onClick={(e) => { e.stopPropagation(); onToggleExpand(); }} className="p-0.5">
      {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
    </button>
  );
};

const ItemDetails = ({ item }: { item: CorpusItem }) => {
  return (
    <div className="flex-1">
      <div className="flex items-center gap-2">
        <span className="font-medium">{item.name}</span>
        <Badge variant={getStatusBadgeVariant(item.status)}>
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
};

const ItemActions = () => {
  return (
    <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
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
};

const ChildrenContainer = ({ 
  item, 
  depth = 0, 
  onToggleExpand, 
  onToggleSelect 
}: Omit<CorpusItemProps, 'isExpanded' | 'isSelected'>) => {
  return (
    <div>
      {item.children!.map(child => (
        <CorpusItemRow
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
  );
};