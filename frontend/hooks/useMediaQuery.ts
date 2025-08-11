import { useState, useEffect } from 'react';

export const useMediaQuery = (query: string): boolean => {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    
    // Set initial value
    setMatches(media.matches);

    // Create event listener
    const listener = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Add event listener
    if (media.addEventListener) {
      media.addEventListener('change', listener);
    } else {
      // Fallback for older browsers
      media.addListener(listener);
    }

    // Clean up
    return () => {
      if (media.removeEventListener) {
        media.removeEventListener('change', listener);
      } else {
        // Fallback for older browsers
        media.removeListener(listener);
      }
    };
  }, [query]);

  return matches;
};

// Predefined breakpoints matching Tailwind CSS
export const useBreakpoint = () => {
  const isMobile = useMediaQuery('(max-width: 639px)'); // < sm
  const isTablet = useMediaQuery('(min-width: 640px) and (max-width: 1023px)'); // sm to lg
  const isDesktop = useMediaQuery('(min-width: 1024px)'); // >= lg
  const isLargeDesktop = useMediaQuery('(min-width: 1280px)'); // >= xl
  
  return {
    isMobile,
    isTablet,
    isDesktop,
    isLargeDesktop,
    // Helper for responsive values
    responsive: <T,>(mobile: T, tablet?: T, desktop?: T): T => {
      if (isDesktop && desktop !== undefined) return desktop;
      if (isTablet && tablet !== undefined) return tablet;
      return mobile;
    }
  };
};