/**
 * Button Component Tests
 * Tests for button component variations and states
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '../../utils/anti-hanging-test-utilities';

// Mock button component
const MockButton: React.FC<{
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
}> = ({ children, variant = 'primary', size = 'medium', disabled = false, loading = false, onClick }) => {
  const getVariantClasses = () => {
    switch (variant) {
      case 'primary': return 'bg-blue-500 text-white hover:bg-blue-600';
      case 'secondary': return 'bg-gray-500 text-white hover:bg-gray-600';
      case 'danger': return 'bg-red-500 text-white hover:bg-red-600';
      default: return 'bg-blue-500 text-white hover:bg-blue-600';
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'small': return 'px-3 py-1 text-sm';
      case 'medium': return 'px-4 py-2 text-base';
      case 'large': return 'px-6 py-3 text-lg';
      default: return 'px-4 py-2 text-base';
    }
  };

  return (
    <button
      data-testid="button"
      className={`${getVariantClasses()} ${getSizeClasses()} rounded font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading ? 'Loading...' : children}
    </button>
  );
};

describe('Button Component Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  it('should render with default props', () => {
    render(<MockButton>Click me</MockButton>);
    
    const button = screen.getByTestId('button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Click me');
    expect(button).toHaveClass('bg-blue-500', 'px-4', 'py-2');
    expect(button).not.toBeDisabled();
  });

  it('should render different variants', () => {
    const { rerender } = render(<MockButton variant="primary">Primary</MockButton>);
    expect(screen.getByTestId('button')).toHaveClass('bg-blue-500');

    rerender(<MockButton variant="secondary">Secondary</MockButton>);
    expect(screen.getByTestId('button')).toHaveClass('bg-gray-500');

    rerender(<MockButton variant="danger">Danger</MockButton>);
    expect(screen.getByTestId('button')).toHaveClass('bg-red-500');
  });

  it('should render different sizes', () => {
    const { rerender } = render(<MockButton size="small">Small</MockButton>);
    expect(screen.getByTestId('button')).toHaveClass('px-3', 'py-1', 'text-sm');

    rerender(<MockButton size="medium">Medium</MockButton>);
    expect(screen.getByTestId('button')).toHaveClass('px-4', 'py-2', 'text-base');

    rerender(<MockButton size="large">Large</MockButton>);
    expect(screen.getByTestId('button')).toHaveClass('px-6', 'py-3', 'text-lg');
  });

  it('should handle disabled state', () => {
    render(<MockButton disabled>Disabled Button</MockButton>);
    
    const button = screen.getByTestId('button');
    expect(button).toBeDisabled();
    expect(button).toHaveClass('disabled:opacity-50', 'disabled:cursor-not-allowed');
  });

  it('should handle loading state', () => {
    render(<MockButton loading>Save</MockButton>);
    
    const button = screen.getByTestId('button');
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent('Loading...');
  });

  it('should handle click events', () => {
    const mockClick = jest.fn();
    render(<MockButton onClick={mockClick}>Click me</MockButton>);
    
    const button = screen.getByTestId('button');
    fireEvent.click(button);
    
    expect(mockClick).toHaveBeenCalledTimes(1);
  });

  it('should not trigger click when disabled', () => {
    const mockClick = jest.fn();
    render(<MockButton disabled onClick={mockClick}>Disabled</MockButton>);
    
    const button = screen.getByTestId('button');
    fireEvent.click(button);
    
    expect(mockClick).not.toHaveBeenCalled();
  });

  it('should not trigger click when loading', () => {
    const mockClick = jest.fn();
    render(<MockButton loading onClick={mockClick}>Loading</MockButton>);
    
    const button = screen.getByTestId('button');
    fireEvent.click(button);
    
    expect(mockClick).not.toHaveBeenCalled();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});