import { TestDataFactory, TestSetup, MockEndpoints, TestAssertions, FormHelpers } from '../support/user-settings-helpers';

/**
 * User Profile Management E2E Tests
 * Split from user-profile-settings.cy.ts for 450-line compliance
 * 
 * BVJ: Growth & Enterprise - User retention through profile management
 * Value Impact: Profile functionality drives user engagement
 */

describe('User Profile Management', () => {
  beforeEach(() => {
    TestSetup.clearUserState();
    TestSetup.setupAuthenticatedUser();
  });

  it('should display and update user profile information', () => {
    // Mock initial profile data
    const initialProfile = TestDataFactory.createUserProfile();
    MockEndpoints.mockUserProfile(initialProfile);

    // Navigate to settings
    TestSetup.navigateToSettings();

    // Wait for profile data to load
    cy.wait('@getUserProfile');

    // Verify profile information is displayed (initially disabled)
    TestAssertions.verifyFieldValue('full_name', 'Test User');
    TestAssertions.verifyFieldValue('email', 'test@netrasystems.ai');
    TestAssertions.verifyElementText('Member since January 1, 2024');

    // Click edit to enable editing
    cy.get('button').contains('Edit Profile').click();

    // Update profile information
    const newName = 'Updated Test User';
    FormHelpers.clearAndType('full_name', newName);

    // Mock profile update endpoint
    const updatedProfile = MockEndpoints.mockProfileUpdate({ full_name: newName });

    // Save changes
    FormHelpers.submitForm('Save Profile');
    cy.wait('@updateProfile');

    // Verify success message
    TestAssertions.verifySuccessMessage('Profile updated successfully');

    // Verify updated name is saved (after reload)
    cy.reload();
    TestAssertions.verifyFieldValue('full_name', newName);
  });

  it('should handle profile update validation errors', () => {
    // Mock initial profile data
    MockEndpoints.mockUserProfile();
    TestSetup.navigateToSettings();

    // Wait for profile to load and enable editing
    cy.wait('@getUserProfile');
    cy.get('button').contains('Edit Profile').click();

    // Try to update with invalid email
    FormHelpers.clearAndType('email', 'invalid-email');

    // Mock validation error
    cy.intercept('PATCH', '/api/users/profile', {
      statusCode: 400,
      body: {
        error: 'Invalid email format',
        field: 'email'
      }
    }).as('invalidUpdate');

    FormHelpers.submitForm('Save Profile');
    cy.wait('@invalidUpdate');

    // Verify error message
    TestAssertions.verifyErrorMessage('Invalid email format');
  });

  it('should handle profile picture upload', () => {
    // Mock initial profile data
    MockEndpoints.mockUserProfile();
    TestSetup.navigateToSettings();
    cy.wait('@getUserProfile');

    // Mock successful upload
    cy.intercept('POST', '/api/users/profile/avatar', {
      statusCode: 200,
      body: {
        avatar_url: 'https://cdn.example.com/avatars/user-123.jpg'
      }
    }).as('uploadAvatar');

    // Simulate file upload - the UI handles validation client-side
    const fileName = 'profile.jpg';
    cy.get('input[type="file"]').selectFile({
      contents: 'fake-image-content',
      fileName,
      mimeType: 'image/jpeg'
    }, { force: true });

    // The UI should automatically trigger upload
    cy.wait('@uploadAvatar');

    // Verify success message
    TestAssertions.verifySuccessMessage('Profile picture updated');
    
    // Verify image is displayed
    TestAssertions.verifyElementVisible('img[alt="Profile picture"]');
    cy.get('img[alt="Profile picture"]').should('have.attr', 'src').and('include', 'user-123.jpg');
  });

  it('should validate profile picture size and format', () => {
    // Mock initial profile data
    MockEndpoints.mockUserProfile();
    TestSetup.navigateToSettings();
    cy.wait('@getUserProfile');

    // Try uploading oversized file (6MB)
    cy.get('input[type="file"]').selectFile({
      contents: new Array(6 * 1024 * 1024).fill('a').join(''), // 6MB file
      fileName: 'large.jpg',
      mimeType: 'image/jpeg'
    }, { force: true });

    TestAssertions.verifyErrorMessage('File size must be less than 5MB');

    // Try uploading invalid format
    cy.get('input[type="file"]').selectFile({
      contents: 'invalid content',
      fileName: 'document.pdf',
      mimeType: 'application/pdf'
    }, { force: true });

    TestAssertions.verifyErrorMessage('Only JPG, PNG, and GIF files are allowed');
  });
});