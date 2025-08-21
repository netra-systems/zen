
describe('WebSocket Reconnection after Interruption (L4)', () => {

  const CHAT_URL = '/chat';

  beforeEach(() => {
    cy.visit(CHAT_URL);
  });

  it('should automatically reconnect and restore state after a WebSocket interruption', () => {
    // 1. Start an agent workflow
    cy.get('textarea[aria-label="Message input"]').type('Start a long-running agent workflow.');
    cy.get('button[aria-label="Send message"]').click();

    // 2. Verify the WebSocket connection is active
    cy.window().then((win) => {
      const store = win.useUnifiedChatStore?.getState();
      expect(store.websocketManager.isConnected()).to.be.true;

      // 3. Simulate a disconnection by mocking the WebSocket object
      // NOTE: This is a simplified approach. A more robust test would use tools
      // to simulate a real network interruption.
      store.websocketManager.getSocket().close();

      // 4. Assert that the application tries to reconnect
      // NOTE: This assumes the websocketManager has a public `reconnect` method.
      // We will spy on it to see if it gets called.
      const reconnectSpy = cy.spy(store.websocketManager, 'reconnect');
      store.websocketManager.getSocket().dispatchEvent(new Event('close'));
      expect(reconnectSpy).to.have.been.called;

      // 5. Once reconnected, assert that the application fetches the latest state
      // NOTE: This assumes the application has a mechanism to fetch the latest
      // state after reconnection. We will mock this mechanism for the test.
      const fetchStateSpy = cy.spy(store, 'fetchLatestWorkflowState');
      store.websocketManager.getSocket().dispatchEvent(new Event('open'));
      expect(fetchStateSpy).to.have.been.called;
    });
  });
});
