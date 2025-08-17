import { WebSocketMessage } from '@/types/chat';

describe('User Profile Basic Information Management', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should display and update user profile information', () => {
    // Navigate to profile settings
    cy.visit('/settings');

    // Verify profile information is displayed
    cy.get('input[name="full_name"]').should('have.value', 'Test User');
    cy.get('input[name="email"]').should('have.value', 'test@netrasystems.ai');
    cy.contains('Member since January 1, 2024').should('be.visible');

    // Update profile information
    const newName = 'Updated Test User';
    cy.get('input[name="full_name"]').clear().type(newName);

    // Mock profile update endpoint
    cy.intercept('PATCH', '/api/users/profile', {
      statusCode: 200,
      body: {
        id: 1,
        email: 'test@netrasystems.ai',
        full_name: newName,
        created_at: '2024-01-01T00:00:00Z',
        avatar_url: null
      }
    }).as('updateProfile');

    // Save changes
    cy.get('button').contains('Save Profile').click();
    cy.wait('@updateProfile');

    // Verify success message
    cy.contains('Profile updated successfully').should('be.visible');

    // Verify updated name is saved
    cy.reload();
    cy.get('input[name="full_name"]').should('have.value', newName);
  });

  it('should validate profile information fields', () => {
    cy.visit('/settings');

    // Test email validation
    cy.get('input[name="email"]').clear().type('invalid-email');
    cy.get('button').contains('Save Profile').click();
    cy.contains('Please enter a valid email address').should('be.visible');

    // Test name length validation
    cy.get('input[name="full_name"]').clear().type('a'); // Too short
    cy.get('button').contains('Save Profile').click();
    cy.contains('Name must be at least 2 characters').should('be.visible');

    // Test maximum name length
    const longName = 'a'.repeat(101);
    cy.get('input[name="full_name"]').clear().type(longName);
    cy.get('button').contains('Save Profile').click();
    cy.contains('Name must be less than 100 characters').should('be.visible');
  });

  it('should handle profile update errors gracefully', () => {
    cy.visit('/settings');

    // Mock server error
    cy.intercept('PATCH', '/api/users/profile', {
      statusCode: 500,
      body: {
        error: 'Internal server error'
      }
    }).as('updateProfileError');

    // Try to update profile
    cy.get('input[name="full_name"]').clear().type('Updated Name');
    cy.get('button').contains('Save Profile').click();
    cy.wait('@updateProfileError');

    // Verify error message
    cy.contains('Failed to update profile').should('be.visible');
    cy.contains('Please try again later').should('be.visible');
  });

  it('should display profile creation date correctly', () => {
    cy.visit('/settings');

    // Mock different creation dates
    const testDates = [
      { date: '2024-01-01T00:00:00Z', expected: 'January 1, 2024' },
      { date: '2023-12-15T14:30:00Z', expected: 'December 15, 2023' },
      { date: '2024-06-30T23:59:59Z', expected: 'June 30, 2024' }
    ];

    testDates.forEach(({ date, expected }) => {
      cy.intercept('GET', '/api/users/profile', {
        statusCode: 200,
        body: {
          id: 1,
          email: 'test@netrasystems.ai',
          full_name: 'Test User',
          created_at: date,
          avatar_url: null
        }
      }).as('getProfile');

      cy.reload();
      cy.wait('@getProfile');
      cy.contains(`Member since ${expected}`).should('be.visible');
    });
  });

  it('should handle avatar upload functionality', () => {
    cy.visit('/settings');

    // Test avatar upload button visibility
    cy.get('[data-testid="avatar-upload-button"]').should('be.visible');

    // Mock successful avatar upload
    cy.intercept('POST', '/api/users/avatar', {
      statusCode: 200,
      body: {
        avatar_url: 'https://example.com/avatar.jpg'
      }
    }).as('uploadAvatar');

    // Simulate file upload
    cy.get('input[type="file"]').selectFile({
      contents: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
      fileName: 'avatar.png',
      mimeType: 'image/png'
    }, { force: true });

    cy.wait('@uploadAvatar');

    // Verify success message
    cy.contains('Avatar updated successfully').should('be.visible');

    // Verify avatar image is displayed
    cy.get('img[alt="User avatar"]').should('have.attr', 'src').and('include', 'avatar.jpg');
  });

  it('should validate avatar file requirements', () => {
    cy.visit('/settings');

    // Test file size limit
    cy.intercept('POST', '/api/users/avatar', {
      statusCode: 400,
      body: {
        error: 'File size too large. Maximum size is 5MB.'
      }
    }).as('uploadAvatarError');

    // Simulate large file upload
    const largeFileContent = 'x'.repeat(6 * 1024 * 1024); // 6MB
    cy.get('input[type="file"]').selectFile({
      contents: largeFileContent,
      fileName: 'large-avatar.jpg',
      mimeType: 'image/jpeg'
    }, { force: true });

    cy.wait('@uploadAvatarError');

    // Verify error message
    cy.contains('File size too large').should('be.visible');
  });

  it('should handle profile form keyboard navigation', () => {
    cy.visit('/settings');

    // Test tab navigation
    cy.get('input[name="full_name"]').focus();
    cy.focused().should('have.attr', 'name', 'full_name');

    cy.focused().tab();
    cy.focused().should('have.attr', 'name', 'email');

    cy.focused().tab();
    cy.focused().should('contain.text', 'Save Profile');

    // Test form submission with Enter key
    cy.get('input[name="full_name"]').focus().clear().type('Keyboard Test User{enter}');

    // Should trigger save action
    cy.intercept('PATCH', '/api/users/profile').as('keyboardSave');
    cy.wait('@keyboardSave');
  });

  it('should auto-save profile changes after delay', () => {
    cy.visit('/settings');

    // Enable auto-save mode
    cy.get('[data-testid="auto-save-toggle"]').check();

    // Mock auto-save endpoint
    cy.intercept('PATCH', '/api/users/profile', {
      statusCode: 200,
      body: {
        id: 1,
        email: 'test@netrasystems.ai',
        full_name: 'Auto-saved Name',
        created_at: '2024-01-01T00:00:00Z',
        avatar_url: null
      }
    }).as('autoSaveProfile');

    // Type in the name field
    cy.get('input[name="full_name"]').clear().type('Auto-saved Name');

    // Wait for auto-save delay (assuming 2 seconds)
    cy.wait(2500);
    cy.wait('@autoSaveProfile');

    // Verify auto-save indicator
    cy.contains('Auto-saved').should('be.visible');
  });

  it('should show unsaved changes warning', () => {
    cy.visit('/settings');

    // Make changes without saving
    cy.get('input[name="full_name"]').clear().type('Unsaved Changes');

    // Try to navigate away
    cy.get('a[href="/dashboard"]').click();

    // Should show confirmation dialog
    cy.on('window:confirm', (text) => {
      expect(text).to.contains('You have unsaved changes');
      return false; // Cancel navigation
    });

    // Should remain on settings page
    cy.url().should('include', '/settings');

    // Verify changes are still there
    cy.get('input[name="full_name"]').should('have.value', 'Unsaved Changes');
  });
});
