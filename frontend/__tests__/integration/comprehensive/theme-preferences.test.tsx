/**
 * Theme and Preferences Integration Tests
 * 
 * Tests theme synchronization, user preferences persistence,
 * and complex form validation with debouncing.
 */

import {
  React,
  render,
  waitFor,
  fireEvent,
  act,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  createThemeContext,
  createThemeProvider,
  mockUserPreferences,
  mockFormData,
  validateFormStep,
  TEST_TIMEOUTS,
  WS
} from './test-utils';

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

describe('Theme and Preferences Integration Tests', () => {
      setupAntiHang();
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
      cleanupAntiHang();
  });

  describe('Theme Synchronization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should sync theme preferences across components', async () => {
      const ThemeContext = createThemeContext();
      const ThemeProvider = createThemeProvider(ThemeContext);
      
      const TestComponent = () => {
        const { theme, setTheme } = React.useContext(ThemeContext);
        
        return (
          <div>
            <div data-testid="current-theme">{theme}</div>
            <button onClick={() => setTheme('dark')}>Dark Mode</button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );
      
      expect(getByTestId('current-theme')).toHaveTextContent('light');
      
      fireEvent.click(getByText('Dark Mode'));
      
      await waitFor(() => {
        expect(getByTestId('current-theme')).toHaveTextContent('dark');
        expect(localStorage.getItem('theme')).toBe('dark');
      });
    });

    it('should persist user preferences across sessions', async () => {
      const preferences = { ...mockUserPreferences };
      
      // Save preferences
      localStorage.setItem('userPreferences', JSON.stringify(preferences));
      
      // Simulate new session
      const loadPreferences = () => {
        const saved = localStorage.getItem('userPreferences');
        return saved ? JSON.parse(saved) : {};
      };
      
      const loaded = loadPreferences();
      
      expect(loaded).toEqual(preferences);
      expect(loaded.notifications).toBe(true);
      expect(loaded.autoSave).toBe(false);
    });

    it('should handle theme switching with transitions', async () => {
      const ThemeContext = createThemeContext();
      const ThemeProvider = createThemeProvider(ThemeContext);
      
      const TestComponent = () => {
        const { theme, setTheme } = React.useContext(ThemeContext);
        const [transitioning, setTransitioning] = React.useState(false);
        
        const handleThemeChange = async (newTheme: string) => {
          setTransitioning(true);
          await new Promise(resolve => setTimeout(resolve, 100));
          setTheme(newTheme);
          setTransitioning(false);
        };
        
        return (
          <div>
            <div data-testid="current-theme">{theme}</div>
            <div data-testid="transitioning">{transitioning ? 'true' : 'false'}</div>
            <button onClick={() => handleThemeChange('dark')}>Switch Theme</button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );
      
      fireEvent.click(getByText('Switch Theme'));
      
      // Check transitioning state
      await waitFor(() => {
        expect(getByTestId('transitioning')).toHaveTextContent('true');
      });
      
      // Wait for transition to complete
      await waitFor(() => {
        expect(getByTestId('current-theme')).toHaveTextContent('dark');
        expect(getByTestId('transitioning')).toHaveTextContent('false');
      }, { timeout: TEST_TIMEOUTS.SHORT });
    });
  });

  describe('Complex Form Validation', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should validate multi-step forms with dependencies', async () => {
      const FormComponent = () => {
        const [step, setStep] = React.useState(1);
        const [formData, setFormData] = React.useState(mockFormData);
        const [errors, setErrors] = React.useState<Record<string, string>>({});
        
        const validateStep = (currentStep: number) => {
          const { errors: newErrors, isValid } = validateFormStep(currentStep, formData);
          setErrors(newErrors);
          return isValid;
        };
        
        const handleNext = () => {
          if (validateStep(step)) {
            setStep(step + 1);
          }
        };
        
        return (
          <div>
            <div data-testid="step">{step}</div>
            {step === 1 && (
              <div>
                <input
                  data-testid="model-input"
                  value={formData.model}
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                />
                {errors.model && <div data-testid="model-error">{errors.model}</div>}
              </div>
            )}
            {step === 2 && (
              <div>
                <input
                  data-testid="temperature-input"
                  type="number"
                  value={formData.temperature}
                  onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                />
                {errors.temperature && <div data-testid="temperature-error">{errors.temperature}</div>}
              </div>
            )}
            <button onClick={handleNext}>Next</button>
          </div>
        );
      };
      
      const { getByTestId, getByText } = render(<FormComponent />);
      
      // Try to proceed without required field
      fireEvent.click(getByText('Next'));
      
      await waitFor(() => {
        expect(getByTestId('model-error')).toHaveTextContent('Model is required');
      });
      
      // Fill required field
      fireEvent.change(getByTestId('model-input'), { target: { value: 'gemini-2.5-flash' } });
      fireEvent.click(getByText('Next'));
      
      await waitFor(() => {
        expect(getByTestId('step')).toHaveTextContent('2');
      });
    });

    it('should handle async validation with debouncing', async () => {
      let validationCount = 0;
      
      const AsyncValidationComponent = () => {
        const [email, setEmail] = React.useState('');
        const [isValidating, setIsValidating] = React.useState(false);
        const [error, setError] = React.useState('');
        
        const validateEmail = React.useCallback(async (value: string) => {
          validationCount++;
          
          // Simulate API call
          await new Promise(resolve => setTimeout(resolve, 100));
          
          await act(async () => {
            setIsValidating(true);
            
            if (!value.includes('@')) {
              setError('Invalid email');
            } else {
              setError('');
            }
            
            setIsValidating(false);
          });
        }, []);
        
        // Debounce validation
        React.useEffect(() => {
          const timer = setTimeout(() => {
            if (email) validateEmail(email);
          }, 300);
          
          return () => clearTimeout(timer);
        }, [email, validateEmail]);
        
        return (
          <div>
            <input
              data-testid="email-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {isValidating && <div>Validating...</div>}
            {error && <div data-testid="error">{error}</div>}
          </div>
        );
      };
      
      const { getByTestId } = render(<AsyncValidationComponent />);
      
      // Type quickly
      const input = getByTestId('email-input');
      fireEvent.change(input, { target: { value: 't' } });
      fireEvent.change(input, { target: { value: 'te' } });
      fireEvent.change(input, { target: { value: 'test' } });
      
      // Wait for debounce
      await new Promise(resolve => setTimeout(resolve, 400));
      
      // Should only validate once due to debouncing
      expect(validationCount).toBe(1);
      
      await waitFor(() => {
        expect(getByTestId('error')).toHaveTextContent('Invalid email');
      });
    });

    it('should handle form validation with conditional fields', async () => {
      const ConditionalFormComponent = () => {
        const [userType, setUserType] = React.useState('');
        const [companyName, setCompanyName] = React.useState('');
        const [errors, setErrors] = React.useState<Record<string, string>>({});
        
        const validate = () => {
          const newErrors: Record<string, string> = {};
          
          if (!userType) {
            newErrors.userType = 'User type is required';
          }
          
          if (userType === 'business' && !companyName) {
            newErrors.companyName = 'Company name is required for business users';
          }
          
          setErrors(newErrors);
          return Object.keys(newErrors).length === 0;
        };
        
        return (
          <div>
            <select
              data-testid="user-type"
              value={userType}
              onChange={(e) => setUserType(e.target.value)}
            >
              <option value="">Select type</option>
              <option value="individual">Individual</option>
              <option value="business">Business</option>
            </select>
            {errors.userType && <div data-testid="user-type-error">{errors.userType}</div>}
            
            {userType === 'business' && (
              <div>
                <input
                  data-testid="company-name"
                  placeholder="Company Name"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
                {errors.companyName && <div data-testid="company-name-error">{errors.companyName}</div>}
              </div>
            )}
            
            <button onClick={validate}>Validate</button>
          </div>
        );
      };
      
      const { getByTestId, getByText, queryByTestId } = render(<ConditionalFormComponent />);
      
      // Test validation without selection
      fireEvent.click(getByText('Validate'));
      
      await waitFor(() => {
        expect(getByTestId('user-type-error')).toHaveTextContent('User type is required');
      });
      
      // Select business type
      fireEvent.change(getByTestId('user-type'), { target: { value: 'business' } });
      
      await waitFor(() => {
        expect(getByTestId('company-name')).toBeInTheDocument();
      });
      
      // Test validation with business type but no company name
      fireEvent.click(getByText('Validate'));
      
      await waitFor(() => {
        expect(getByTestId('company-name-error')).toHaveTextContent('Company name is required for business users');
      });
      
      // Fill company name
      fireEvent.change(getByTestId('company-name'), { target: { value: 'Acme Corp' } });
      
      // Switch to individual - company field should disappear
      fireEvent.change(getByTestId('user-type'), { target: { value: 'individual' } });
      
      await waitFor(() => {
        expect(queryByTestId('company-name')).not.toBeInTheDocument();
      });
    });
  });
});