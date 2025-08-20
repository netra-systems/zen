/**
 * Interactive Features Advanced Drag and Drop Integration Tests
 * ULTRA DEEP THINK: Module-based architecture - Advanced drag-drop tests extracted for 450-line compliance
 */

import {
  React, render, waitFor, fireEvent,
  setupInteractiveTest, teardownInteractiveTest,
  simulateDragStart, reorderItems, generateItems,
  expectItemOrder, simulateDropValidation
} from './interactive-features-utils';

describe('Advanced Drag and Drop Integration Tests', () => {
  let server: any;
  
  beforeEach(() => {
    server = setupInteractiveTest();
  });

  afterEach(() => {
    teardownInteractiveTest();
  });

  it('should reorder items with drag and drop', async () => {
    const ReorderableList = () => {
      const [items, setItems] = React.useState(generateItems(4));
      const [draggedItem, setDraggedItem] = React.useState<string | null>(null);
      const [dragOverItem, setDragOverItem] = React.useState<string | null>(null);
      
      const handleDragStart = (id: string) => {
        setDraggedItem(id);
      };
      
      const handleDragOver = (e: React.DragEvent, targetId: string) => {
        e.preventDefault();
        setDragOverItem(targetId);
      };
      
      const handleDragLeave = () => {
        setDragOverItem(null);
      };
      
      const resetDragState = () => {
        setDraggedItem(null);
        setDragOverItem(null);
      };
      
      const handleDrop = (targetId: string) => {
        if (!draggedItem || draggedItem === targetId) {
          resetDragState();
          return;
        }
        const draggedIndex = items.findIndex(item => item.id === draggedItem);
        const targetIndex = items.findIndex(item => item.id === targetId);
        setItems(reorderItems(items, draggedIndex, targetIndex));
        resetDragState();
      };
      
      return (
        <div data-testid="reorderable-list">
          {items.map((item, index) => (
            <div
              key={item.id}
              data-testid={`item-${index}`}
              draggable
              onDragStart={() => handleDragStart(item.id)}
              onDragOver={(e) => handleDragOver(e, item.id)}
              onDragLeave={handleDragLeave}
              onDrop={() => handleDrop(item.id)}
              style={{
                padding: '10px',
                margin: '5px',
                backgroundColor: dragOverItem === item.id ? '#e0e0e0' : '#f5f5f5',
                border: draggedItem === item.id ? '2px dashed #999' : '1px solid #ddd',
                cursor: 'move'
              }}
            >
              {item.text}
            </div>
          ))}
        </div>
      );
    };
    
    const { getByTestId } = render(<ReorderableList />);
    
    // Initial order
    expectItemOrder(getByTestId, ['Item 1', 'Item 2', 'Item 3']);
    
    // Simulate drag Item 1 to position of Item 3
    const item1 = getByTestId('item-0');
    const item3 = getByTestId('item-2');
    
    simulateDragStart(item1);
    fireEvent.dragOver(item3);
    fireEvent.drop(item3);
    
    await waitFor(() => {
      expectItemOrder(getByTestId, ['Item 2', 'Item 3', 'Item 1']);
    });
  });

  it('should handle drag and drop with validation', async () => {
    const ValidatedDragDrop = () => {
      const [validItems] = React.useState(['valid1', 'valid2']);
      const [invalidItems] = React.useState(['invalid1']);
      const [dropZones, setDropZones] = React.useState({
        valid: [] as string[],
        invalid: [] as string[]
      });
      const [error, setError] = React.useState('');
      
      const validateDrop = (zone: 'valid' | 'invalid', item: string): boolean => {
        try {
          simulateDropValidation(zone, item, invalidItems);
          return true;
        } catch (err: any) {
          setError(err.message);
          return false;
        }
      };
      
      const addItemToZone = (zone: 'valid' | 'invalid', item: string) => {
        setDropZones(prev => ({
          ...prev,
          [zone]: [...prev[zone], item]
        }));
      };
      
      const handleDrop = (zone: 'valid' | 'invalid', item: string) => {
        if (!validateDrop(zone, item)) return;
        setError('');
        addItemToZone(zone, item);
      };
      
      return (
        <div>
          <div data-testid="valid-zone">
            Valid Zone: {dropZones.valid.join(', ')}
          </div>
          <div data-testid="invalid-zone">
            Invalid Zone: {dropZones.invalid.join(', ')}
          </div>
          {error && <div data-testid="error">{error}</div>}
          <button
            onClick={() => handleDrop('valid', 'valid1')}
            data-testid="drop-valid-item"
          >
            Drop Valid Item
          </button>
          <button
            onClick={() => handleDrop('valid', 'invalid1')}
            data-testid="drop-invalid-item"
          >
            Drop Invalid Item
          </button>
        </div>
      );
    };
    
    const { getByTestId } = render(<ValidatedDragDrop />);
    
    // Drop valid item - should succeed
    fireEvent.click(getByTestId('drop-valid-item'));
    
    await waitFor(() => {
      expect(getByTestId('valid-zone')).toHaveTextContent('Valid Zone: valid1');
    });
    
    // Drop invalid item - should fail
    fireEvent.click(getByTestId('drop-invalid-item'));
    
    await waitFor(() => {
      expect(getByTestId('error')).toHaveTextContent('Invalid item cannot be placed in valid zone');
      expect(getByTestId('valid-zone')).not.toHaveTextContent('invalid1');
    });
  });
});