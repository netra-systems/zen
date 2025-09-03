import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Simple Button component for testing
const Button = ({ children, onClick, disabled = false }: { 
  children: React.ReactNode; 
  onClick?: () => void; 
  disabled?: boolean;
}) => (
  <button onClick={onClick} disabled={disabled}>
    {children}
  </button>
);

describe('Button Component', () => {
  it('renders button with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('handles click events', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('can be disabled', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick} disabled>Click me</Button>);
    
    const button = screen.getByText('Click me');
    expect(button).toBeDisabled();
    
    fireEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('renders children correctly', () => {
    render(
      <Button>
        <span data-testid="child-element">Child content</span>
      </Button>
    );
    expect(screen.getByTestId('child-element')).toBeInTheDocument();
  });
});