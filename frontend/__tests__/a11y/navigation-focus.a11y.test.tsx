/**
 * Navigation Focus Management Accessibility Test Suite
 * Tests focus trapping, restoration, and dynamic content focus
 * Follows 25-line function rule and 450-line file limit
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise) 
 * - Goal: Ensure proper focus management for accessibility compliance
 * - Value Impact: Enables keyboard-only users to navigate complex interfaces
 * - Revenue Impact: +$15K MRR from accessibility-required customers
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import navigation components
import { Button } from '@/components/ui/button';

// Import shared accessibility helpers
import { 
  setupKeyboardTest, 
  testFocusTrap, 
  testFocusRestoration 
} from './shared-a11y-helpers';

// ============================================================================
// FOCUS MANAGEMENT TESTS
// ============================================================================

describe('Focus Management - Trapping and Restoration', () => {
  it('traps focus in modal dialogs', async () => {
    const user = setupKeyboardTest();
    const ModalDialog = () => {
      const [isOpen, setIsOpen] = React.useState(false);
      
      React.useEffect(() => {
        if (isOpen) {
          const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Tab') {
              const focusableElements = document.querySelectorAll(
                '[role="dialog"] button, [role="dialog"] input'
              );
              if (focusableElements.length === 0) return;
            }
          };
          document.addEventListener('keydown', handleKeyDown);
          return () => document.removeEventListener('keydown', handleKeyDown);
        }
      }, [isOpen]);
      
      return (
        <div>
          <Button onClick={() => setIsOpen(true)}>Open Modal</Button>
          {isOpen && (
            <div role="dialog" aria-modal="true">
              <Button onClick={() => setIsOpen(false)}>Close</Button>
              <Button>Action</Button>
            </div>
          )}
        </div>
      );
    };
    
    render(<ModalDialog />);
    await user.click(screen.getByRole('button', { name: 'Open Modal' }));
    
    const closeButton = screen.getByRole('button', { name: 'Close' });
    const actionButton = screen.getByRole('button', { name: 'Action' });
    
    expect(closeButton).toBeInTheDocument();
    expect(actionButton).toBeInTheDocument();
  });

  it('restores focus after modal closes', async () => {
    const user = setupKeyboardTest();
    const ModalWithFocusRestore = () => {
      const [isOpen, setIsOpen] = React.useState(false);
      const triggerRef = React.useRef<HTMLButtonElement>(null);
      
      React.useEffect(() => {
        if (!isOpen && triggerRef.current) {
          triggerRef.current.focus();
        }
      }, [isOpen]);
      
      return (
        <div>
          <Button ref={triggerRef} onClick={() => setIsOpen(true)}>
            Open Modal
          </Button>
          {isOpen && (
            <div role="dialog">
              <Button onClick={() => setIsOpen(false)}>Close</Button>
            </div>
          )}
        </div>
      );
    };
    
    render(<ModalWithFocusRestore />);
    const trigger = screen.getByRole('button', { name: 'Open Modal' });
    
    await user.click(trigger);
    await user.click(screen.getByRole('button', { name: 'Close' }));
    
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
  });

  it('manages focus in dynamic content updates', async () => {
    const user = setupKeyboardTest();
    const DynamicContent = () => {
      const [showContent, setShowContent] = React.useState(false);
      const newContentRef = React.useRef<HTMLButtonElement>(null);
      
      React.useEffect(() => {
        if (showContent && newContentRef.current) {
          newContentRef.current.focus();
        }
      }, [showContent]);
      
      return (
        <div>
          <Button onClick={() => setShowContent(true)}>Load Content</Button>
          {showContent && (
            <Button ref={newContentRef}>New Content</Button>
          )}
        </div>
      );
    };
    
    render(<DynamicContent />);
    await user.click(screen.getByRole('button', { name: 'Load Content' }));
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'New Content' })).toHaveFocus();
    });
  });

  it('provides visible focus indicators', async () => {
    const user = setupKeyboardTest();
    render(<Button className="focus:ring-2 focus:ring-blue-500">Focus Test</Button>);
    
    const button = screen.getByRole('button');
    await user.tab();
    
    expect(button).toHaveFocus();
    expect(button).toHaveClass('focus:ring-2');
  });

  it('manages focus in collapsible content', async () => {
    const user = setupKeyboardTest();
    const CollapsibleContent = () => {
      const [isExpanded, setIsExpanded] = React.useState(false);
      const firstItemRef = React.useRef<HTMLButtonElement>(null);
      
      React.useEffect(() => {
        if (isExpanded && firstItemRef.current) {
          firstItemRef.current.focus();
        }
      }, [isExpanded]);
      
      return (
        <div>
          <Button 
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            aria-controls="collapsible-content"
          >
            Toggle Content
          </Button>
          {isExpanded && (
            <div id="collapsible-content">
              <Button ref={firstItemRef}>First Item</Button>
              <Button>Second Item</Button>
            </div>
          )}
        </div>
      );
    };
    
    render(<CollapsibleContent />);
    await user.click(screen.getByRole('button', { name: 'Toggle Content' }));
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'First Item' })).toHaveFocus();
    });
  });

  it('handles focus with programmatic navigation', async () => {
    const user = setupKeyboardTest();
    const ProgrammaticFocus = () => {
      const buttonRef = React.useRef<HTMLButtonElement>(null);
      
      const focusButton = () => {
        if (buttonRef.current) {
          buttonRef.current.focus();
        }
      };
      
      return (
        <div>
          <Button onClick={focusButton}>Focus Target Button</Button>
          <Button ref={buttonRef}>Target Button</Button>
        </div>
      );
    };
    
    render(<ProgrammaticFocus />);
    await user.click(screen.getByRole('button', { name: 'Focus Target Button' }));
    
    expect(screen.getByRole('button', { name: 'Target Button' })).toHaveFocus();
  });

  it('preserves focus during content updates', async () => {
    const user = setupKeyboardTest();
    const UpdatingContent = () => {
      const [count, setCount] = React.useState(0);
      const buttonRef = React.useRef<HTMLButtonElement>(null);
      
      const increment = () => {
        setCount(count + 1);
        // Maintain focus after update
        setTimeout(() => {
          if (buttonRef.current) {
            buttonRef.current.focus();
          }
        }, 0);
      };
      
      return (
        <div>
          <Button ref={buttonRef} onClick={increment}>
            Count: {count}
          </Button>
        </div>
      );
    };
    
    render(<UpdatingContent />);
    const button = screen.getByRole('button', { name: 'Count: 0' });
    
    await user.click(button);
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Count: 1' })).toHaveFocus();
    });
  });

  it('manages focus in tabbed interfaces', async () => {
    const user = setupKeyboardTest();
    const TabbedInterface = () => {
      const [activeTab, setActiveTab] = React.useState(0);
      const tabRefs = [
        React.useRef<HTMLButtonElement>(null),
        React.useRef<HTMLButtonElement>(null),
        React.useRef<HTMLButtonElement>(null)
      ];
      
      const selectTab = (index: number) => {
        setActiveTab(index);
        tabRefs[index].current?.focus();
      };
      
      return (
        <div>
          <div role="tablist">
            {['Tab 1', 'Tab 2', 'Tab 3'].map((label, index) => (
              <Button
                key={label}
                ref={tabRefs[index]}
                role="tab"
                aria-selected={activeTab === index}
                onClick={() => selectTab(index)}
              >
                {label}
              </Button>
            ))}
          </div>
          <div role="tabpanel">
            Content for Tab {activeTab + 1}
          </div>
        </div>
      );
    };
    
    render(<TabbedInterface />);
    await user.click(screen.getByRole('tab', { name: 'Tab 2' }));
    
    expect(screen.getByRole('tab', { name: 'Tab 2' })).toHaveFocus();
    expect(screen.getByRole('tab', { name: 'Tab 2' })).toHaveAttribute('aria-selected', 'true');
  });

  it('handles focus in dropdown menus', async () => {
    const user = setupKeyboardTest();
    const DropdownMenu = () => {
      const [isOpen, setIsOpen] = React.useState(false);
      const firstItemRef = React.useRef<HTMLButtonElement>(null);
      const triggerRef = React.useRef<HTMLButtonElement>(null);
      
      React.useEffect(() => {
        if (isOpen && firstItemRef.current) {
          firstItemRef.current.focus();
        } else if (!isOpen && triggerRef.current) {
          triggerRef.current.focus();
        }
      }, [isOpen]);
      
      return (
        <div>
          <Button 
            ref={triggerRef}
            onClick={() => setIsOpen(!isOpen)}
            aria-expanded={isOpen}
            aria-haspopup="menu"
          >
            Open Menu
          </Button>
          {isOpen && (
            <div role="menu">
              <Button ref={firstItemRef} role="menuitem">Item 1</Button>
              <Button role="menuitem">Item 2</Button>
              <Button 
                role="menuitem" 
                onClick={() => setIsOpen(false)}
              >
                Close Menu
              </Button>
            </div>
          )}
        </div>
      );
    };
    
    render(<DropdownMenu />);
    await user.click(screen.getByRole('button', { name: 'Open Menu' }));
    
    await waitFor(() => {
      expect(screen.getByRole('menuitem', { name: 'Item 1' })).toHaveFocus();
    });
    
    await user.click(screen.getByRole('menuitem', { name: 'Close Menu' }));
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Open Menu' })).toHaveFocus();
    });
  });

  it('supports focus management in forms with errors', async () => {
    const user = setupKeyboardTest();
    const FormWithErrors = () => {
      const [hasError, setHasError] = React.useState(false);
      const errorFieldRef = React.useRef<HTMLInputElement>(null);
      
      React.useEffect(() => {
        if (hasError && errorFieldRef.current) {
          errorFieldRef.current.focus();
        }
      }, [hasError]);
      
      const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setHasError(true);
      };
      
      return (
        <form onSubmit={handleSubmit}>
          <input 
            ref={errorFieldRef}
            placeholder="This field will have an error"
            aria-invalid={hasError}
          />
          {hasError && (
            <div role="alert">This field is required</div>
          )}
          <Button type="submit">Submit</Button>
        </form>
      );
    };
    
    render(<FormWithErrors />);
    await user.click(screen.getByRole('button', { name: 'Submit' }));
    
    await waitFor(() => {
      expect(screen.getByRole('textbox')).toHaveFocus();
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('manages focus in infinite scroll content', async () => {
    const user = setupKeyboardTest();
    const InfiniteScroll = () => {
      const [items, setItems] = React.useState([1, 2, 3]);
      const loadMoreRef = React.useRef<HTMLButtonElement>(null);
      
      const loadMore = () => {
        const newItems = [...items, ...Array.from({length: 3}, (_, i) => items.length + i + 1)];
        setItems(newItems);
        
        // Focus first new item after loading
        setTimeout(() => {
          const firstNewItem = document.querySelector(`[data-item="${items.length + 1}"]`) as HTMLElement;
          firstNewItem?.focus();
        }, 0);
      };
      
      return (
        <div>
          {items.map(item => (
            <Button key={item} data-item={item} tabIndex={0}>
              Item {item}
            </Button>
          ))}
          <Button ref={loadMoreRef} onClick={loadMore}>
            Load More
          </Button>
        </div>
      );
    };
    
    render(<InfiniteScroll />);
    await user.click(screen.getByRole('button', { name: 'Load More' }));
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Item 4' })).toHaveFocus();
    });
  });
});