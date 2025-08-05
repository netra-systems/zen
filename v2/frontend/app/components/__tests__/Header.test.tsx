import { render, screen } from '@testing-library/react';
import { Header } from '../Header';

describe('Header', () => {
  it('renders the header with the logo', () => {
    render(<Header />);
    expect(screen.getByRole('button', { name: /toggle navigation menu/i })).toBeInTheDocument();
  });

  it('renders the login button when no user is logged in', () => {
    render(<Header />);
    expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument();
  });
});