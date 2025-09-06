/**
 * Example component showing how to integrate Statsig analytics
 * with existing UI components
 */

import React from 'react';
import { useStatsigClient } from '@statsig/react-bindings';
import { useAnalytics } from '@/services/analyticsService';

// Example 1: Simple button with click tracking
export function AddToCartButton({ sku, price, itemName }: {
  sku: string;
  price: string;
  itemName: string;
}) {
  const { client } = useStatsigClient();

  const handleClick = () => {
    // Direct Statsig logging
    client.logEvent("add_to_cart", sku, {
      price,
      item_name: itemName,
    });
  };

  return <button onClick={handleClick}>Add to Cart</button>;
}

// Example 2: Using the unified analytics service
export function PurchaseButton({ productId, amount }: {
  productId: string;
  amount: number;
}) {
  const analytics = useAnalytics();

  const handlePurchase = () => {
    // Track conversion with unified analytics
    analytics.trackConversion('purchase', amount, {
      product_id: productId,
      currency: 'USD',
      timestamp: new Date().toISOString()
    });
  };

  return <button onClick={handlePurchase}>Purchase Now</button>;
}

// Example 3: Feature usage tracking
export function AdvancedFeatureToggle({ featureName }: { featureName: string }) {
  const analytics = useAnalytics();
  const [isEnabled, setIsEnabled] = React.useState(false);

  const handleToggle = () => {
    const newState = !isEnabled;
    setIsEnabled(newState);

    // Track feature usage
    analytics.trackFeatureUsage(featureName, newState ? 'enabled' : 'disabled', {
      previous_state: isEnabled,
      user_action: 'manual_toggle'
    });
  };

  return (
    <label>
      <input 
        type="checkbox" 
        checked={isEnabled}
        onChange={handleToggle}
      />
      Enable {featureName}
    </label>
  );
}

// Example 4: Error tracking
export function DataFetchButton({ endpoint }: { endpoint: string }) {
  const analytics = useAnalytics();

  const handleFetch = async () => {
    try {
      const response = await fetch(endpoint);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Track successful interaction
      analytics.trackInteraction('fetch_data', 'api', {
        endpoint,
        status: response.status,
        success: true
      });
      
    } catch (error) {
      // Track error
      analytics.trackError('data_fetch_failed', {
        endpoint,
        error_message: error instanceof Error ? error.message : 'Unknown error',
        error_type: error instanceof Error ? error.name : 'UnknownError'
      });
    }
  };

  return <button onClick={handleFetch}>Fetch Data</button>;
}

// Example 5: Complex interaction tracking
export function ChatInterfaceExample() {
  const analytics = useAnalytics();
  const [message, setMessage] = React.useState('');

  const handleSend = () => {
    if (!message.trim()) return;

    // Track multiple aspects of the interaction
    analytics.trackInteraction('send_message', 'chat_input', {
      message_content: message,
      message_length: message.length,
      has_emoji: /\p{Emoji}/u.test(message),
      word_count: message.trim().split(/\s+/).length,
      timestamp: new Date().toISOString()
    });

    // Track feature usage
    analytics.trackFeatureUsage('chat', 'message_sent', {
      interface_type: 'web',
      input_method: 'keyboard'
    });

    // Reset message
    setMessage('');
  };

  return (
    <div>
      <input 
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type a message..."
      />
      <button onClick={handleSend}>Send</button>
    </div>
  );
}

// Example 6: Page view tracking
export function PageViewTracker({ pageName }: { pageName: string }) {
  const analytics = useAnalytics();

  React.useEffect(() => {
    analytics.trackEvent({
      name: 'page_view',
      value: pageName,
      metadata: {
        referrer: document.referrer,
        url: window.location.href,
        timestamp: new Date().toISOString()
      }
    });
  }, [pageName]);

  return null;
}