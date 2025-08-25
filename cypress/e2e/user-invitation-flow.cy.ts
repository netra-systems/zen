
describe('User Invitation and Role Assignment Flow (L4)', () => {

  const ADMIN_USER = Cypress.env('CYPRESS_ADMIN_USER');
  const ADMIN_PASSWORD = Cypress.env('CYPRESS_ADMIN_PASSWORD');
  const INVITED_USER_EMAIL = Cypress.env('CYPRESS_INVITED_USER_EMAIL');
  const INVITED_USER_PASSWORD = 'newTestPassword123';

  const LOGIN_URL = '/login';
  const INVITATION_API_ENDPOINT = '/api/invitations'; // Example endpoint to get invitation tokens

  it('should allow an admin to invite a user, assign a role, and enforce permissions', () => {
    // 1. Log in as Admin user
    cy.visit(LOGIN_URL);
    cy.get('input[name="username"]').type(ADMIN_USER);
    cy.get('input[name="password"]').type(ADMIN_PASSWORD);
    cy.get('button[type="submit"]').click();

    // 2. Invite a new user
    // NOTE: Replace with actual selectors for the invitation form
    cy.get('button#invite-user').click();
    cy.get('input[name="email"]').type(INVITED_USER_EMAIL);
    cy.get('button#send-invitation').click();

    // 3. Fetch the invitation token from the backend
    // NOTE: This is a placeholder. In a real scenario, you might need a dedicated
    // test endpoint or a tool like MailHog to intercept the email.
    cy.request({
      url: `${INVITATION_API_ENDPOINT}?email=${INVITED_USER_EMAIL}`,
      method: 'GET',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` }
    }).then((response) => {
      const invitationToken = response.body.token;

      // 4. Visit the registration page with the invitation token
      cy.visit(`/register?token=${invitationToken}`);

      // 5. Complete the registration for the new user
      cy.get('input[name="password"]').type(INVITED_USER_PASSWORD);
      cy.get('input[name="confirmPassword"]').type(INVITED_USER_PASSWORD);
      cy.get('button[type="submit"]').click();
    });

    // 6. Log in as Admin user again
    cy.visit(LOGIN_URL);
    cy.get('input[name="username"]').type(ADMIN_USER);
    cy.get('input[name="password"]').type(ADMIN_PASSWORD);
    cy.get('button[type="submit"]').click();

    // 7. Assign a "Read-Only" role to the new user
    // NOTE: Replace with actual selectors for role management
    cy.visit('/admin/users');
    cy.contains(INVITED_USER_EMAIL).parent().find('button.edit-roles').click();
    cy.get('select[name="role"]').select('Read-Only');
    cy.get('button#save-roles').click();

    // 8. Log in as the new user
    cy.visit(LOGIN_URL);
    cy.get('input[name="username"]').type(INVITED_USER_EMAIL);
    cy.get('input[name="password"]').type(INVITED_USER_PASSWORD);
    cy.get('button[type="submit"]').click();

    // 9. Attempt to perform a write action
    // NOTE: Replace with an actual write action that a read-only user should not be able to perform
    cy.request({
      url: '/api/some-resource',
      method: 'POST',
      body: { data: 'test' },
      headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` },
      failOnStatusCode: false
    }).then((response) => {
      // 10. Assert that the action is forbidden
      expect(response.status).to.eq(403);
    });
  });
});
