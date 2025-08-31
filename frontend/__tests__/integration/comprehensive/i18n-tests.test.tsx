import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { ternationalization Tests
 * 
 * Tests multi-language support, RTL languages, and locale formatting.
 * All functions ≤8 lines, file ≤300 lines for modular architecture compliance.
 */

import {
  React,
  render,
  waitFor,
  fireEvent,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  WS
} from './test-utils';

import {
  I18nSwitcherComponent,
  RTLLanguageComponent,
  LocaleFormattingComponent
} from './components/i18n-components';

// Apply Next.js navigation mock
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('Internationalization Tests', () => {
    jest.setTimeout(10000);
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Multi-language Support Integration', () => {
      jest.setTimeout(10000);
    it('should switch languages dynamically', async () => {
      const { getByTestId } = render(<I18nSwitcherComponent />);
      
      // Initial English state
      expect(getByTestId('welcome-message')).toHaveTextContent('Welcome');
      expect(getByTestId('goodbye-message')).toHaveTextContent('Goodbye');
      expect(getByTestId('current-lang')).toHaveTextContent('en');
      expect(document.documentElement.lang).toBe('en');
    });

    it('should switch to Spanish correctly', async () => {
      const { getByTestId } = render(<I18nSwitcherComponent />);
      
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'es' } });
      
      await waitFor(() => {
        expect(getByTestId('welcome-message')).toHaveTextContent('Bienvenido');
        expect(getByTestId('goodbye-message')).toHaveTextContent('Adiós');
        expect(getByTestId('current-lang')).toHaveTextContent('es');
        expect(document.documentElement.lang).toBe('es');
      });
    });

    it('should switch to French correctly', async () => {
      const { getByTestId } = render(<I18nSwitcherComponent />);
      
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'fr' } });
      
      await waitFor(() => {
        expect(getByTestId('welcome-message')).toHaveTextContent('Bienvenue');
        expect(getByTestId('goodbye-message')).toHaveTextContent('Au revoir');
        expect(localStorage.getItem('preferred_language')).toBe('fr');
      });
    });

    it('should handle Chinese Unicode support', async () => {
      const { getByTestId } = render(<I18nSwitcherComponent />);
      
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'zh' } });
      
      await waitFor(() => {
        expect(getByTestId('welcome-message')).toHaveTextContent('欢迎');
        expect(getByTestId('goodbye-message')).toHaveTextContent('再见');
      });
    });
  });

  describe('RTL Language Support', () => {
      jest.setTimeout(10000);
    it('should handle RTL languages correctly', async () => {
      const { getByTestId } = render(<RTLLanguageComponent />);
      
      // Initial LTR state
      expect(getByTestId('direction-indicator')).toHaveTextContent('ltr');
      expect(getByTestId('text-align')).toHaveTextContent('left');
      expect(document.documentElement.dir).toBe('ltr');
    });

    it('should switch to Arabic RTL correctly', async () => {
      const { getByTestId } = render(<RTLLanguageComponent />);
      
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'ar' } });
      
      await waitFor(() => {
        expect(getByTestId('direction-indicator')).toHaveTextContent('rtl');
        expect(getByTestId('text-align')).toHaveTextContent('right');
        expect(document.documentElement.dir).toBe('rtl');
      });
    });

    it('should switch to Hebrew RTL correctly', async () => {
      const { getByTestId } = render(<RTLLanguageComponent />);
      
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'he' } });
      
      await waitFor(() => {
        expect(getByTestId('direction-indicator')).toHaveTextContent('rtl');
        expect(document.documentElement.dir).toBe('rtl');
      });
    });

    it('should switch back to LTR correctly', async () => {
      const { getByTestId } = render(<RTLLanguageComponent />);
      
      // First go to RTL
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'ar' } });
      
      // Then back to LTR
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'es' } });
      
      await waitFor(() => {
        expect(getByTestId('direction-indicator')).toHaveTextContent('ltr');
        expect(getByTestId('text-align')).toHaveTextContent('left');
        expect(document.documentElement.dir).toBe('ltr');
      });
    });
  });

  describe('Locale Formatting', () => {
      jest.setTimeout(10000);
    it('should format dates and numbers according to locale', async () => {
      const { getByTestId } = render(<LocaleFormattingComponent />);
      
      // Test US formatting
      expect(getByTestId('formatted-date')).toHaveTextContent('1/15/2024');
      expect(getByTestId('formatted-number')).toHaveTextContent('1,234,567.89');
      expect(getByTestId('formatted-currency')).toHaveTextContent('$1,000.50');
    });

    it('should format Spanish locale correctly', async () => {
      const { getByTestId } = render(<LocaleFormattingComponent />);
      
      fireEvent.change(getByTestId('locale-selector'), { target: { value: 'es-ES' } });
      
      await waitFor(() => {
        expect(getByTestId('formatted-date')).toHaveTextContent('15/1/2024');
        expect(getByTestId('formatted-currency')).toHaveTextContent('1000,50');
      });
    });

    it('should handle Japanese locale formatting', async () => {
      const { getByTestId } = render(<LocaleFormattingComponent />);
      
      fireEvent.change(getByTestId('locale-selector'), { target: { value: 'ja-JP' } });
      
      await waitFor(() => {
        expect(getByTestId('formatted-date')).toHaveTextContent('2024/1/15');
      });
    });

    it('should handle Arabic locale formatting', async () => {
      const { getByTestId } = render(<LocaleFormattingComponent />);
      
      fireEvent.change(getByTestId('locale-selector'), { target: { value: 'ar-SA' } });
      
      await waitFor(() => {
        expect(getByTestId('formatted-date')).toHaveTextContent('15/1/2024');
      });
    });
  });
});