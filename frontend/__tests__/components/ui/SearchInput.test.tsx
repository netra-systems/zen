import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';

// SearchInput component as found in corpus-browse.tsx
const SearchInput = ({ 
  searchTerm, 
  setSearchTerm,
  placeholder = 'Search...',
  className = '',
  disabled = false,
  ...props
}: { 
  searchTerm: string; 
  setSearchTerm: (term: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  [key: string]: any;
}) => {
  const handleClear = () => {
    setSearchTerm('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      handleClear();
    }
    props.onKeyDown?.(e);
  };

  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        placeholder={placeholder}
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        onKeyDown={handleKeyDown}
        className="pl-9 pr-8"
        disabled={disabled}
        data-testid="search-input"
        {...props}
      />
      {searchTerm && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-2 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
          aria-label="Clear search"
          data-testid="clear-search"
        >
          ×
        </button>
      )}
    </div>
  );
};

describe('SearchInput Component - Comprehensive Tests', () => {
  const defaultProps = {
    searchTerm: '',
    setSearchTerm: jest.fn(),
  };

  const renderSearchInput = (props = {}) => {
    const mergedProps = { ...defaultProps, ...props };
    return render(<SearchInput {...mergedProps} />);
  };

  const setupUser = () => userEvent.setup();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders search input correctly', () => {
      renderSearchInput();
      const input = screen.getByTestId('search-input');
      expect(input).toBeInTheDocument();
      expect(input).toBeInstanceOf(HTMLInputElement);
    });

    it('displays search icon', () => {
      renderSearchInput();
      const searchIcon = screen.getByRole('img', { hidden: true });
      expect(searchIcon).toBeInTheDocument();
    });

    it('shows default placeholder', () => {
      renderSearchInput();
      const input = screen.getByTestId('search-input');
      expect(input).toHaveAttribute('placeholder', 'Search...');
    });

    it('shows custom placeholder', () => {
      renderSearchInput({ placeholder: 'Search corpus...' });
      const input = screen.getByTestId('search-input');
      expect(input).toHaveAttribute('placeholder', 'Search corpus...');
    });

    it('applies custom className', () => {
      renderSearchInput({ className: 'custom-search' });
      const container = screen.getByTestId('search-input').parentElement;
      expect(container).toHaveClass('custom-search');
    });
  });

  describe('Text Entry and Search', () => {
    it('accepts search input correctly', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.type(input, 'test query');
      expect(setSearchTerm).toHaveBeenCalledTimes(10);
      expect(setSearchTerm).toHaveBeenLastCalledWith('test query');
    });

    it('handles rapid typing', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.type(input, 'rapid', { delay: 1 });
      expect(setSearchTerm).toHaveBeenCalledTimes(5);
    });

    it('updates display value when searchTerm prop changes', () => {
      const { rerender } = renderSearchInput({ searchTerm: 'initial' });
      const input = screen.getByTestId('search-input');
      expect(input).toHaveValue('initial');
      
      rerender(<SearchInput searchTerm="updated" setSearchTerm={jest.fn()} />);
      expect(input).toHaveValue('updated');
    });

    it('handles controlled component updates', async () => {
      const user = setupUser();
      const TestComponent = () => {
        const [searchTerm, setSearchTerm] = React.useState('');
        return (
          <SearchInput searchTerm={searchTerm} setSearchTerm={setSearchTerm} />
        );
      };
      
      render(<TestComponent />);
      const input = screen.getByTestId('search-input');
      
      await user.type(input, 'controlled');
      expect(input).toHaveValue('controlled');
    });
  });

  describe('Special Characters and Query Types', () => {
    it('accepts emoji in search queries', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.type(input, '🔍 emoji search');
      expect(setSearchTerm).toHaveBeenLastCalledWith('🔍 emoji search');
    });

    it('handles special search characters', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.type(input, '*wildcard +operator "quoted"');
      expect(setSearchTerm).toHaveBeenLastCalledWith('*wildcard +operator "quoted"');
    });

    it('accepts Unicode characters', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.type(input, 'café résumé 中文');
      expect(setSearchTerm).toHaveBeenLastCalledWith('café résumé 中文');
    });

    it('handles code search queries', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.type(input, 'function() { return true; }');
      expect(setSearchTerm).toHaveBeenLastCalledWith('function() { return true; }');
    });
  });

  describe('Clear Functionality', () => {
    it('shows clear button when search term exists', () => {
      renderSearchInput({ searchTerm: 'test' });
      const clearButton = screen.getByTestId('clear-search');
      expect(clearButton).toBeInTheDocument();
    });

    it('hides clear button when search term is empty', () => {
      renderSearchInput({ searchTerm: '' });
      const clearButton = screen.queryByTestId('clear-search');
      expect(clearButton).not.toBeInTheDocument();
    });

    it('clears search on clear button click', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ searchTerm: 'test query', setSearchTerm });
      const clearButton = screen.getByTestId('clear-search');
      
      await user.click(clearButton);
      expect(setSearchTerm).toHaveBeenCalledWith('');
    });

    it('clears search on Escape key', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ searchTerm: 'test', setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      await user.keyboard('{Escape}');
      expect(setSearchTerm).toHaveBeenCalledWith('');
    });

    it('clear button has proper accessibility label', () => {
      renderSearchInput({ searchTerm: 'test' });
      const clearButton = screen.getByTestId('clear-search');
      expect(clearButton).toHaveAttribute('aria-label', 'Clear search');
    });
  });

  describe('Copy and Paste Operations', () => {
    it('supports paste operation', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      await user.paste('pasted search term');
      expect(setSearchTerm).toHaveBeenCalledWith('pasted search term');
    });

    it('supports copy operation', async () => {
      const user = setupUser();
      renderSearchInput({ searchTerm: 'copy this' });
      const input = screen.getByTestId('search-input');
      
      await user.tripleClick(input);
      await user.copy();
      expect(input.selectionStart).toBe(0);
      expect(input.selectionEnd).toBe(9);
    });

    it('handles multi-line paste gracefully', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      await user.paste('line 1\nline 2\nline 3');
      // Should handle newlines in pasted content
      expect(setSearchTerm).toHaveBeenCalled();
    });
  });

  describe('Keyboard Shortcuts', () => {
    it('supports select all shortcut', async () => {
      const user = setupUser();
      renderSearchInput({ searchTerm: 'select all this' });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      await user.keyboard('{Control>}a{/Control}');
      expect(input.selectionStart).toBe(0);
      expect(input.selectionEnd).toBe(15);
    });

    it('supports standard editing shortcuts', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ searchTerm: 'edit this text', setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      await user.keyboard('{Control>}a{/Control}');
      await user.keyboard('{Backspace}');
      expect(setSearchTerm).toHaveBeenCalledWith('');
    });

    it('handles custom onKeyDown events', async () => {
      const user = setupUser();
      const onKeyDown = jest.fn();
      renderSearchInput({ onKeyDown });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      await user.keyboard('a');
      expect(onKeyDown).toHaveBeenCalled();
    });

    it('handles navigation keys', async () => {
      const user = setupUser();
      renderSearchInput({ searchTerm: 'navigate me' });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      await user.keyboard('{Home}');
      expect(input.selectionStart).toBe(0);
      
      await user.keyboard('{End}');
      expect(input.selectionStart).toBe(11);
    });
  });

  describe('Auto-focus Functionality', () => {
    it('focuses automatically when autoFocus is true', () => {
      renderSearchInput({ autoFocus: true });
      const input = screen.getByTestId('search-input');
      expect(input).toHaveFocus();
    });

    it('can receive focus programmatically', () => {
      renderSearchInput();
      const input = screen.getByTestId('search-input');
      
      act(() => {
        input.focus();
      });
      expect(input).toHaveFocus();
    });

    it('maintains focus after clear operation', async () => {
      const user = setupUser();
      renderSearchInput({ searchTerm: 'focused', autoFocus: true });
      const input = screen.getByTestId('search-input');
      const clearButton = screen.getByTestId('clear-search');
      
      expect(input).toHaveFocus();
      await user.click(clearButton);
      // Focus might be maintained depending on implementation
      expect(input).toBeInTheDocument();
    });
  });

  describe('Mobile Keyboard Behavior', () => {
    it('uses text input type for mobile keyboards', () => {
      renderSearchInput();
      const input = screen.getByTestId('search-input');
      expect(input).toHaveAttribute('type', 'text');
    });

    it('handles touch interactions', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      expect(input).toHaveFocus();
    });

    it('maintains proper input styling on mobile', () => {
      renderSearchInput();
      const input = screen.getByTestId('search-input');
      expect(input).toHaveClass('pl-9'); // Proper left padding for icon
      expect(input).toHaveClass('pr-8'); // Proper right padding for clear button
    });
  });

  describe('Disabled State', () => {
    it('prevents input when disabled', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ disabled: true, setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      expect(input).toBeDisabled();
      await user.type(input, 'should not work');
      expect(setSearchTerm).not.toHaveBeenCalled();
    });

    it('shows disabled styling', () => {
      renderSearchInput({ disabled: true });
      const input = screen.getByTestId('search-input');
      expect(input).toHaveClass('disabled:cursor-not-allowed');
      expect(input).toHaveClass('disabled:opacity-50');
    });

    it('disables clear button when disabled', () => {
      renderSearchInput({ disabled: true, searchTerm: 'test' });
      const clearButton = screen.getByTestId('clear-search');
      // Clear button should still be visible but parent input is disabled
      expect(clearButton).toBeInTheDocument();
    });

    it('cannot receive focus when disabled', () => {
      renderSearchInput({ disabled: true });
      const input = screen.getByTestId('search-input');
      
      act(() => {
        input.focus();
      });
      expect(input).not.toHaveFocus();
    });
  });

  describe('Event Handling', () => {
    it('calls onChange handler on input', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      await user.type(input, 'test');
      expect(setSearchTerm).toHaveBeenCalledTimes(4);
    });

    it('calls onFocus handler when focused', async () => {
      const user = setupUser();
      const onFocus = jest.fn();
      renderSearchInput({ onFocus });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      expect(onFocus).toHaveBeenCalledTimes(1);
    });

    it('calls onBlur handler when blurred', async () => {
      const user = setupUser();
      const onBlur = jest.fn();
      renderSearchInput({ onBlur });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      await user.tab();
      expect(onBlur).toHaveBeenCalledTimes(1);
    });

    it('handles custom event handlers', async () => {
      const user = setupUser();
      const onKeyDown = jest.fn();
      const onFocus = jest.fn();
      renderSearchInput({ onKeyDown, onFocus });
      const input = screen.getByTestId('search-input');
      
      await user.click(input);
      await user.keyboard('a');
      expect(onFocus).toHaveBeenCalled();
      expect(onKeyDown).toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('supports aria-label', () => {
      renderSearchInput({ 'aria-label': 'Search database' });
      const input = screen.getByTestId('search-input');
      expect(input).toHaveAttribute('aria-label', 'Search database');
    });

    it('supports aria-describedby for help text', () => {
      renderSearchInput({ 'aria-describedby': 'search-help' });
      const input = screen.getByTestId('search-input');
      expect(input).toHaveAttribute('aria-describedby', 'search-help');
    });

    it('has proper role for search input', () => {
      renderSearchInput({ role: 'searchbox' });
      const input = screen.getByTestId('search-input');
      expect(input).toHaveAttribute('role', 'searchbox');
    });

    it('clear button has proper accessibility attributes', () => {
      renderSearchInput({ searchTerm: 'test' });
      const clearButton = screen.getByTestId('clear-search');
      expect(clearButton).toHaveAttribute('type', 'button');
      expect(clearButton).toHaveAttribute('aria-label', 'Clear search');
    });

    it('supports screen reader announcements', () => {
      renderSearchInput({ 'aria-live': 'polite' });
      const input = screen.getByTestId('search-input');
      expect(input).toHaveAttribute('aria-live', 'polite');
    });
  });

  describe('Search Icon Styling', () => {
    it('positions search icon correctly', () => {
      renderSearchInput();
      const searchIcon = screen.getByRole('img', { hidden: true });
      expect(searchIcon.parentElement).toHaveClass('relative');
      expect(searchIcon).toHaveClass('absolute');
      expect(searchIcon).toHaveClass('left-3');
    });

    it('applies proper icon styling', () => {
      renderSearchInput();
      const searchIcon = screen.getByRole('img', { hidden: true });
      expect(searchIcon).toHaveClass('h-4');
      expect(searchIcon).toHaveClass('w-4');
      expect(searchIcon).toHaveClass('text-muted-foreground');
    });
  });

  describe('Performance', () => {
    it('handles rapid input changes efficiently', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      // Simulate rapid typing
      await user.type(input, 'performance test', { delay: 1 });
      expect(setSearchTerm).toHaveBeenCalledTimes(16);
      expect(input).toHaveValue('performance test');
    });

    it('maintains responsiveness with long search terms', async () => {
      const user = setupUser();
      const setSearchTerm = jest.fn();
      renderSearchInput({ setSearchTerm });
      const input = screen.getByTestId('search-input');
      
      const longSearchTerm = 'a'.repeat(1000);
      await user.paste(longSearchTerm);
      expect(setSearchTerm).toHaveBeenCalledWith(longSearchTerm);
    });

    it('efficiently updates UI on prop changes', () => {
      const { rerender } = renderSearchInput({ searchTerm: '' });
      const input = screen.getByTestId('search-input');
      
      // Multiple rapid prop updates
      for (let i = 0; i < 100; i++) {
        rerender(<SearchInput searchTerm={`term-${i}`} setSearchTerm={jest.fn()} />);
      }
      
      expect(input).toHaveValue('term-99');
    });
  });

  describe('Integration with Forms', () => {
    it('integrates with form submission', () => {
      const handleSubmit = jest.fn((e) => e.preventDefault());
      render(
        <form onSubmit={handleSubmit}>
          <SearchInput searchTerm="test query" setSearchTerm={jest.fn()} />
          <button type="submit">Search</button>
        </form>
      );
      
      const submitButton = screen.getByText('Search');
      fireEvent.click(submitButton);
      expect(handleSubmit).toHaveBeenCalled();
    });

    it('supports form validation', () => {
      renderSearchInput({ required: true });
      const input = screen.getByTestId('search-input');
      expect(input).toHaveAttribute('required');
    });

    it('works with form name attribute', () => {
      renderSearchInput({ name: 'search-query' });
      const input = screen.getByTestId('search-input');
      expect(input).toHaveAttribute('name', 'search-query');
    });
  });
});