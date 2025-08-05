
import { render, screen } from '@testing-library/react';
import { Header } from '../Header';

describe('Header', () => {
  it('renders the header with the logo and title', () => {
    render(<Header />);
    expect(screen.getByText('Netra')).toBeInTheDocument();
  });
});
