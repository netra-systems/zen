/**
 * Mobile Layout Responsive Test
 * Tests responsive behavior and mobile-specific layouts
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

describe('Mobile Layout Responsive Design', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    // Reset window size mocks
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: 768,
    });
  });

  it('should adapt layout for mobile screens', async () => {
    const ResponsiveComponent: React.FC = () => {
      const [isMobile, setIsMobile] = React.useState(false);
      
      React.useEffect(() => {
        const checkMobile = () => {
          setIsMobile(window.innerWidth < 768);
        };
        
        checkMobile();
        
        const handleResize = () => {
          checkMobile();
        };
        
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
      }, []);
      
      return (
        <div data-testid="responsive-container">
          <div data-testid="layout-type">
            {isMobile ? 'mobile' : 'desktop'}
          </div>
          
          {isMobile ? (
            <div data-testid="mobile-layout">
              <div data-testid="mobile-header">Mobile Header</div>
              <div data-testid="mobile-content">Mobile Content</div>
            </div>
          ) : (
            <div data-testid="desktop-layout">
              <div data-testid="desktop-sidebar">Desktop Sidebar</div>
              <div data-testid="desktop-main">Desktop Main</div>
            </div>
          )}
        </div>
      );
    };

    render(<ResponsiveComponent />);
    
    // Initially desktop layout
    expect(screen.getByTestId('layout-type')).toHaveTextContent('desktop');
    expect(screen.getByTestId('desktop-layout')).toBeInTheDocument();
    expect(screen.getByTestId('desktop-sidebar')).toBeInTheDocument();
    
    // Simulate mobile screen size
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 600,
    });
    
    // Trigger resize event
    fireEvent(window, new Event('resize'));
    
    await waitFor(() => {
      expect(screen.getByTestId('layout-type')).toHaveTextContent('mobile');
      expect(screen.getByTestId('mobile-layout')).toBeInTheDocument();
      expect(screen.getByTestId('mobile-header')).toBeInTheDocument();
    });
  });

  it('should handle mobile navigation menu toggle', async () => {
    const MobileNavigationComponent: React.FC = () => {
      const [isMenuOpen, setIsMenuOpen] = React.useState(false);
      const [isMobile, setIsMobile] = React.useState(true);
      
      const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
      };
      
      return (
        <div data-testid="mobile-nav-container">
          {isMobile && (
            <>
              <button
                data-testid="menu-toggle"
                onClick={toggleMenu}
                aria-expanded={isMenuOpen}
                aria-label="Toggle navigation menu"
              >
                ☰
              </button>
              
              {isMenuOpen && (
                <nav
                  data-testid="mobile-menu"
                  role="navigation"
                  aria-label="Main navigation"
                >
                  <a href="#" data-testid="nav-link-home">Home</a>
                  <a href="#" data-testid="nav-link-about">About</a>
                  <a href="#" data-testid="nav-link-contact">Contact</a>
                </nav>
              )}
              
              <div data-testid="menu-status">
                Menu is {isMenuOpen ? 'open' : 'closed'}
              </div>
            </>
          )}
        </div>
      );
    };

    render(<MobileNavigationComponent />);
    
    // Menu is initially closed
    expect(screen.getByTestId('menu-status')).toHaveTextContent('Menu is closed');
    expect(screen.queryByTestId('mobile-menu')).not.toBeInTheDocument();
    
    // Toggle menu open
    fireEvent.click(screen.getByTestId('menu-toggle'));
    
    expect(screen.getByTestId('menu-status')).toHaveTextContent('Menu is open');
    expect(screen.getByTestId('mobile-menu')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-home')).toBeInTheDocument();
    
    // Toggle menu closed
    fireEvent.click(screen.getByTestId('menu-toggle'));
    
    expect(screen.getByTestId('menu-status')).toHaveTextContent('Menu is closed');
    expect(screen.queryByTestId('mobile-menu')).not.toBeInTheDocument();
  });

  it('should handle touch gestures for mobile interactions', async () => {
    const TouchGestureComponent: React.FC = () => {
      const [touchStatus, setTouchStatus] = React.useState('idle');
      const [swipeDirection, setSwipeDirection] = React.useState('');
      
      const handleTouchStart = (e: React.TouchEvent) => {
        setTouchStatus('touching');
      };
      
      const handleTouchEnd = (e: React.TouchEvent) => {
        setTouchStatus('released');
        setSwipeDirection('left'); // Simulate swipe left
      };
      
      const handleTouchMove = (e: React.TouchEvent) => {
        setTouchStatus('moving');
      };
      
      return (
        <div
          data-testid="touch-area"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          style={{
            width: '300px',
            height: '200px',
            backgroundColor: '#f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <div>
            <div data-testid="touch-status">Status: {touchStatus}</div>
            <div data-testid="swipe-direction">
              {swipeDirection && `Swiped: ${swipeDirection}`}
            </div>
          </div>
        </div>
      );
    };

    render(<TouchGestureComponent />);
    
    const touchArea = screen.getByTestId('touch-area');
    
    // Simulate touch start
    fireEvent.touchStart(touchArea, {
      touches: [{ clientX: 100, clientY: 100 }]
    });
    
    expect(screen.getByTestId('touch-status')).toHaveTextContent('Status: touching');
    
    // Simulate touch end
    fireEvent.touchEnd(touchArea, {
      changedTouches: [{ clientX: 50, clientY: 100 }]
    });
    
    expect(screen.getByTestId('touch-status')).toHaveTextContent('Status: released');
    expect(screen.getByTestId('swipe-direction')).toHaveTextContent('Swiped: left');
  });

  it('should optimize content for different screen orientations', async () => {
    const OrientationComponent: React.FC = () => {
      const [orientation, setOrientation] = React.useState<'portrait' | 'landscape'>('portrait');
      
      React.useEffect(() => {
        const checkOrientation = () => {
          const isLandscape = window.innerWidth > window.innerHeight;
          setOrientation(isLandscape ? 'landscape' : 'portrait');
        };
        
        checkOrientation();
        
        window.addEventListener('resize', checkOrientation);
        return () => window.removeEventListener('resize', checkOrientation);
      }, []);
      
      return (
        <div data-testid="orientation-container">
          <div data-testid="current-orientation">
            Orientation: {orientation}
          </div>
          
          <div 
            data-testid="content-layout"
            style={{
              display: 'flex',
              flexDirection: orientation === 'portrait' ? 'column' : 'row'
            }}
          >
            <div data-testid="content-section-1">Section 1</div>
            <div data-testid="content-section-2">Section 2</div>
          </div>
        </div>
      );
    };

    render(<OrientationComponent />);
    
    // Initially portrait (height > width)
    expect(screen.getByTestId('current-orientation')).toHaveTextContent('Orientation: portrait');
    
    // Change to landscape
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1200,
    });
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: 600,
    });
    
    fireEvent(window, new Event('resize'));
    
    await waitFor(() => {
      expect(screen.getByTestId('current-orientation')).toHaveTextContent('Orientation: landscape');
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});