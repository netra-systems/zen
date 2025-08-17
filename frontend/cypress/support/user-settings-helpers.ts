/**
 * User Settings Test Helper Functions
 * Shared utilities for user settings test modules (≤300 lines each)
 * 
 * BVJ: All segments - Test efficiency = faster CI/CD = faster feature delivery
 * Value Impact: Reduced test maintenance cost + improved reliability
 */

// Common test data factories
export const TestDataFactory = {
  // User profile data
  createUserProfile: (overrides = {}) => ({
    id: 1,
    email: 'test@netrasystems.ai',
    full_name: 'Test User',
    created_at: '2024-01-01T00:00:00Z',
    avatar_url: null,
    ...overrides
  }),

  // API key data
  createApiKey: (overrides = {}) => ({
    id: 'key-test-123',
    name: 'Test API Key',
    provider: 'openai',
    last_used: null,
    created_at: new Date().toISOString(),
    masked_value: 'sk-...test123',
    ...overrides
  }),

  // Session data
  createSession: (overrides = {}) => ({
    id: 'session-test-123',
    device_name: 'Chrome on Windows',
    ip_address: '192.168.1.100',
    location: 'New York, US',
    last_active: new Date().toISOString(),
    current: false,
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    ...overrides
  }),

  // Notification settings
  createNotificationSettings: (overrides = {}) => ({
    email_notifications: {
      optimization_complete: true,
      weekly_reports: true,
      system_updates: false,
      marketing: false
    },
    in_app_notifications: {
      agent_updates: true,
      mentions: true,
      thread_replies: true
    },
    push_notifications: {
      enabled: false,
      critical_only: false
    },
    ...overrides
  }),

  // User preferences
  createUserPreferences: (overrides = {}) => ({
    theme: 'light',
    language: 'en',
    timezone: 'America/New_York',
    date_format: 'MM/DD/YYYY',
    default_model: 'claude-3-opus',
    auto_save_interval: 30,
    show_raw_data: false,
    enable_shortcuts: true,
    compact_view: false,
    ...overrides
  })
};

// Common setup functions for tests (≤8 lines each)
export const TestSetup = {
  // Setup authenticated user state
  setupAuthenticatedUser: () => {
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });
  },

  // Navigate to settings page
  navigateToSettings: () => {
    cy.visit('/settings');
  },

  // Navigate to specific settings section
  navigateToSection: (sectionName: string) => {
    TestSetup.navigateToSettings();
    cy.get('button').contains(sectionName).click();
  },

  // Clear all localStorage for clean test state
  clearUserState: () => {
    cy.window().then((win) => {
      win.localStorage.clear();
      win.sessionStorage.clear();
    });
  }
};

// Common mock endpoints for reusability
export const MockEndpoints = {
  // Mock user profile endpoints
  mockUserProfile: (profileData = {}) => {
    const profile = TestDataFactory.createUserProfile(profileData);
    cy.intercept('GET', '/api/users/profile', {
      statusCode: 200,
      body: profile
    }).as('getUserProfile');
    return profile;
  },

  // Mock profile update
  mockProfileUpdate: (updatedData = {}) => {
    const updated = TestDataFactory.createUserProfile(updatedData);
    cy.intercept('PATCH', '/api/users/profile', {
      statusCode: 200,
      body: updated
    }).as('updateProfile');
    return updated;
  },

  // Mock API keys list
  mockApiKeysList: (keys = []) => {
    const keysList = keys.length > 0 ? keys : [TestDataFactory.createApiKey()];
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: { keys: keysList }
    }).as('getApiKeys');
    return keysList;
  },

  // Mock sessions list
  mockSessionsList: (sessions = []) => {
    const sessionsList = sessions.length > 0 ? sessions : [
      TestDataFactory.createSession({ current: true })
    ];
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: { sessions: sessionsList }
    }).as('getSessions');
    return sessionsList;
  },

  // Mock notification settings
  mockNotificationSettings: (settings = {}) => {
    const notificationSettings = TestDataFactory.createNotificationSettings(settings);
    cy.intercept('GET', '/api/users/notifications/settings', {
      statusCode: 200,
      body: notificationSettings
    }).as('getNotificationSettings');
    return notificationSettings;
  },

  // Mock user preferences
  mockUserPreferences: (preferences = {}) => {
    const userPreferences = TestDataFactory.createUserPreferences(preferences);
    cy.intercept('GET', '/api/users/preferences', {
      statusCode: 200,
      body: userPreferences
    }).as('getUserPreferences');
    return userPreferences;
  }
};

// Common assertions for consistent validation (≤8 lines each)
export const TestAssertions = {
  // Verify success message appears
  verifySuccessMessage: (message: string) => {
    cy.contains(message).should('be.visible');
  },

  // Verify error message appears
  verifyErrorMessage: (message: string) => {
    cy.contains(message).should('be.visible');
  },

  // Verify form field has specific value
  verifyFieldValue: (fieldName: string, expectedValue: string) => {
    cy.get(`input[name="${fieldName}"]`).should('have.value', expectedValue);
  },

  // Verify element is visible
  verifyElementVisible: (selector: string) => {
    cy.get(selector).should('be.visible');
  },

  // Verify element contains text
  verifyElementText: (text: string) => {
    cy.contains(text).should('be.visible');
  },

  // Verify redirect to specific URL
  verifyRedirect: (urlPath: string) => {
    cy.url().should('include', urlPath);
  },

  // Verify button is disabled/enabled
  verifyButtonState: (buttonText: string, shouldBeDisabled: boolean) => {
    const assertion = shouldBeDisabled ? 'be.disabled' : 'not.be.disabled';
    cy.get('button').contains(buttonText).should(assertion);
  }
};

// Common form interactions (≤8 lines each)
export const FormHelpers = {
  // Fill password change form
  fillPasswordForm: (current: string, newPass: string, confirm: string) => {
    cy.get('input[name="current_password"]').type(current);
    cy.get('input[name="new_password"]').type(newPass);
    cy.get('input[name="confirm_password"]').type(confirm);
  },

  // Fill API key form
  fillApiKeyForm: (name: string, provider: string, key: string) => {
    cy.get('input[name="key_name"]').type(name);
    cy.get('select[name="provider"]').select(provider);
    cy.get('input[name="api_key"]').type(key);
  },

  // Submit form by button text
  submitForm: (buttonText: string) => {
    cy.get('button').contains(buttonText).click();
  },

  // Clear and type in field
  clearAndType: (fieldName: string, value: string) => {
    cy.get(`input[name="${fieldName}"]`).clear().type(value);
  },

  // Check/uncheck checkbox
  toggleCheckbox: (fieldName: string, shouldCheck: boolean) => {
    const action = shouldCheck ? 'check' : 'uncheck';
    cy.get(`input[name="${fieldName}"]`)[action]();
  },

  // Select dropdown option
  selectOption: (fieldName: string, value: string) => {
    cy.get(`select[name="${fieldName}"]`).select(value);
  }
};

// Common error scenarios for consistent testing
export const ErrorScenarios = {
  // Network error responses
  networkError: () => ({
    statusCode: 500,
    body: { error: 'Internal server error' }
  }),

  // Validation error responses
  validationError: (field: string, message: string) => ({
    statusCode: 400,
    body: { error: message, field }
  }),

  // Authentication error
  authError: () => ({
    statusCode: 401,
    body: { error: 'Authentication required' }
  }),

  // Rate limit error
  rateLimitError: (retryAfter: string) => ({
    statusCode: 429,
    body: { 
      error: 'Rate limit exceeded',
      retry_after: retryAfter
    }
  })
};

// Export all helpers as default for easy importing
export default {
  TestDataFactory,
  TestSetup,
  MockEndpoints,
  TestAssertions,
  FormHelpers,
  ErrorScenarios
};