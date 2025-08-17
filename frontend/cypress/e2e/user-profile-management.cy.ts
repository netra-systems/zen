import { WebSocketMessage } from '@/types/chat';

/**
 * User Profile Management E2E Tests
 * Split from user-profile-settings.cy.ts for 300-line compliance
 * 
 * BVJ: Growth & Enterprise - User retention through profile management
 * Value Impact: Profile functionality drives user engagement
 */

describe('User Profile Management', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should display and update user profile information', () => {
    // Navigate to profile settings
    // Note: User menu navigation not available in current UI
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

  it('should handle profile update validation errors', () => {
    cy.visit('/settings');

    // Try to update with invalid email
    cy.get('input[name="email"]').clear().type('invalid-email');

    // Mock validation error
    cy.intercept('PATCH', '/api/users/profile', {
      statusCode: 400,
      body: {
        error: 'Invalid email format',
        field: 'email'
      }
    }).as('invalidUpdate');

    cy.get('button').contains('Save Profile').click();
    cy.wait('@invalidUpdate');

    // Verify error message
    cy.contains('Invalid email format').should('be.visible');
  });

  it('should handle profile picture upload', () => {
    cy.visit('/settings');

    // Mock file upload
    const fileName = 'profile.jpg';
    cy.fixture(fileName, 'base64').then(fileContent => {
      cy.get('input[type="file"]').selectFile({
        contents: Cypress.Buffer.from(fileContent, 'base64'),
        fileName,
        mimeType: 'image/jpeg'
      }, { force: true });
    });

    // Mock upload endpoint
    cy.intercept('POST', '/api/users/profile/avatar', {
      statusCode: 200,
      body: {
        avatar_url: 'https://cdn.example.com/avatars/user-123.jpg'
      }
    }).as('uploadAvatar');

    cy.get('button').contains('Upload').click();
    cy.wait('@uploadAvatar');

    // Verify success
    cy.contains('Profile picture updated').should('be.visible');
    cy.get('img[alt="Profile picture"]').should('have.attr', 'src').and('include', 'user-123.jpg');
  });

  it('should validate profile picture size and format', () => {
    cy.visit('/settings');

    // Try uploading oversized file
    cy.get('input[type="file"]').selectFile({
      contents: new Array(6 * 1024 * 1024).fill('a').join(''), // 6MB file
      fileName: 'large.jpg',
      mimeType: 'image/jpeg'
    }, { force: true });

    cy.contains('File size must be less than 5MB').should('be.visible');

    // Try uploading invalid format
    cy.get('input[type="file"]').selectFile({
      contents: 'invalid content',
      fileName: 'document.pdf',
      mimeType: 'application/pdf'
    }, { force: true });

    cy.contains('Only JPG, PNG, and GIF files are allowed').should('be.visible');
  });
});