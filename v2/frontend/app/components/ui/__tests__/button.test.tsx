
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Button } from '@/components/ui/button';

describe('Button', () => {
  it('renders a button', () => {
    render(<Button>Click me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
  });

  it('applies the correct variant class', () => {
    render(<Button variant="destructive">Click me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toHaveClass('bg-destructive');
  });

  it('applies the correct size class', () => {
    render(<Button size="lg">Click me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toHaveClass('h-11');
  });

  it('renders as a child component', () => {
    render(<Button asChild><a href="#">Click me</a></Button>);
    const link = screen.getByRole('link', { name: /click me/i });
    expect(link).toBeInTheDocument();
  });
});
