/**
 * Keyboard Navigation Accessibility Test
 * Tests keyboard navigation and accessibility features
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('Keyboard Navigation Accessibility', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  it('should support tab navigation through interactive elements', async () => {
    const TabNavigationComponent: React.FC = () => {
      const [focusedElement, setFocusedElement] = React.useState<string>('');
      
      const handleFocus = (elementName: string) => {
        setFocusedElement(elementName);
      };
      
      return (
        <div>
          <button
            data-testid="button-1"
            onFocus={() => handleFocus('button-1')}
          >
            Button 1
          </button>
          <input
            data-testid="input-1"
            onFocus={() => handleFocus('input-1')}
            placeholder="Input 1"
          />
          <a
            href="#"
            data-testid="link-1"
            onFocus={() => handleFocus('link-1')}
          >
            Link 1
          </a>
          <div data-testid="focused-element">
            Focused: {focusedElement}
          </div>
        </div>
      );
    };

    const user = userEvent.setup();
    render(<TabNavigationComponent />);
    
    // Tab through elements
    await user.tab();
    expect(screen.getByTestId('focused-element')).toHaveTextContent('Focused: button-1');
    
    await user.tab();
    expect(screen.getByTestId('focused-element')).toHaveTextContent('Focused: input-1');
    
    await user.tab();
    expect(screen.getByTestId('focused-element')).toHaveTextContent('Focused: link-1');
  });

  it('should support Enter key activation on buttons', async () => {
    const KeyboardButtonComponent: React.FC = () => {
      const [clickCount, setClickCount] = React.useState(0);
      
      const handleClick = () => {
        setClickCount(prev => prev + 1);
      };
      
      const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      };
      
      return (
        <div>
          <button
            data-testid="keyboard-button"
            onClick={handleClick}
            onKeyDown={handleKeyDown}
          >
            Click me
          </button>
          <div data-testid="click-count">
            Clicked: {clickCount} times
          </div>
        </div>
      );
    };

    const user = userEvent.setup();
    render(<KeyboardButtonComponent />);
    
    const button = screen.getByTestId('keyboard-button');
    button.focus();
    
    // Test Enter key
    await user.keyboard('{Enter}');
    expect(screen.getByTestId('click-count')).toHaveTextContent('Clicked: 1 times');
    
    // Test Space key
    await user.keyboard(' ');
    expect(screen.getByTestId('click-count')).toHaveTextContent('Clicked: 2 times');
  });

  it('should support arrow key navigation in lists', async () => {
    const ListNavigationComponent: React.FC = () => {
      const [selectedIndex, setSelectedIndex] = React.useState(0);
      const items = ['Item 1', 'Item 2', 'Item 3'];
      
      const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          setSelectedIndex(prev => Math.min(prev + 1, items.length - 1));
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          setSelectedIndex(prev => Math.max(prev - 1, 0));
        }
      };
      
      return (
        <div
          role="listbox"
          tabIndex={0}
          data-testid="navigable-list"
          onKeyDown={handleKeyDown}
          aria-activedescendant={`item-${selectedIndex}`}
        >
          {items.map((item, index) => (
            <div
              key={item}
              id={`item-${index}`}
              role="option"
              data-testid={`list-item-${index}`}
              aria-selected={index === selectedIndex}
              style={{
                backgroundColor: index === selectedIndex ? '#e3f2fd' : 'transparent',
                padding: '8px'
              }}
            >
              {item}
            </div>
          ))}
          <div data-testid="selected-item">
            Selected: {items[selectedIndex]}
          </div>
        </div>
      );
    };

    const user = userEvent.setup();
    render(<ListNavigationComponent />);
    
    const list = screen.getByTestId('navigable-list');
    list.focus();
    
    // Initially first item is selected
    expect(screen.getByTestId('selected-item')).toHaveTextContent('Selected: Item 1');
    expect(screen.getByTestId('list-item-0')).toHaveAttribute('aria-selected', 'true');
    
    // Navigate down
    await user.keyboard('{ArrowDown}');
    expect(screen.getByTestId('selected-item')).toHaveTextContent('Selected: Item 2');
    expect(screen.getByTestId('list-item-1')).toHaveAttribute('aria-selected', 'true');
    
    // Navigate up
    await user.keyboard('{ArrowUp}');
    expect(screen.getByTestId('selected-item')).toHaveTextContent('Selected: Item 1');
    expect(screen.getByTestId('list-item-0')).toHaveAttribute('aria-selected', 'true');
  });

  it('should support Escape key to close modals', async () => {
    const ModalComponent: React.FC = () => {
      const [isOpen, setIsOpen] = React.useState(false);
      
      const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Escape') {
          setIsOpen(false);
        }
      };
      
      React.useEffect(() => {
        const handleGlobalKeyDown = (e: KeyboardEvent) => {
          if (e.key === 'Escape' && isOpen) {
            setIsOpen(false);
          }
        };
        
        if (isOpen) {
          document.addEventListener('keydown', handleGlobalKeyDown);
          return () => document.removeEventListener('keydown', handleGlobalKeyDown);
        }
      }, [isOpen]);
      
      return (
        <div>
          <button
            data-testid="open-modal"
            onClick={() => setIsOpen(true)}
          >
            Open Modal
          </button>
          
          {isOpen && (
            <div
              role="dialog"
              aria-modal="true"
              data-testid="modal"
              onKeyDown={handleKeyDown}
              tabIndex={-1}
            >
              <div>Modal Content</div>
              <button
                data-testid="close-modal"
                onClick={() => setIsOpen(false)}
              >
                Close
              </button>
            </div>
          )}
          
          <div data-testid="modal-status">
            Modal is {isOpen ? 'open' : 'closed'}
          </div>
        </div>
      );
    };

    const user = userEvent.setup();
    render(<ModalComponent />);
    
    // Open modal
    await user.click(screen.getByTestId('open-modal'));
    expect(screen.getByTestId('modal-status')).toHaveTextContent('Modal is open');
    expect(screen.getByTestId('modal')).toBeInTheDocument();
    
    // Close with Escape
    await user.keyboard('{Escape}');
    expect(screen.getByTestId('modal-status')).toHaveTextContent('Modal is closed');
    expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});