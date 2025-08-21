# Lark Bot Integration for GitHub Actions

## Two Types of Lark Integrations

### 1. Simple Webhook Bot (One-way notifications)
- **What it does**: Sends notifications FROM GitHub TO Lark
- **Setup**: Create a webhook bot in Lark group chat
- **No callback URL needed**
- **Best for**: Simple notifications without user interaction

### 2. Lark App/Bot with Callbacks (Two-way interaction)
- **What it does**: Sends notifications AND receives user interactions
- **Setup**: Create a Lark app in Lark Developer Console
- **Requires callback URL**: You need a server to handle callbacks
- **Best for**: Interactive messages with buttons that trigger GitHub Actions

## Option 1: Simple Webhook Bot (Recommended for GitHub Actions)

### Setup Steps:

1. **In Lark Desktop/Mobile App**:
   - Open the group chat where you want notifications
   - Click the "..." or settings icon
   - Select "Settings" → "Bots"
   - Click "Add Bot"
   - Choose "Custom Bot" (NOT "Subscribe to Bot")
   - Give it a name like "GitHub Actions"
   - Copy the webhook URL (looks like: `https://open.larksuite.com/open-apis/bot/v2/hook/xxxxx`)

2. **In GitHub**:
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add new secret: `LARK_WEBHOOK_URL` = your webhook URL

3. **Use the workflows I created earlier** - they'll work immediately!

## Option 2: Lark App with Callbacks (Advanced)

If you're seeing the "Callback configuration" screen, you're creating a full Lark app, not a simple webhook bot. Here's how to set this up:

### Prerequisites:
You need a public URL to receive callbacks. Options:
- Use GitHub Pages with a serverless function
- Deploy a simple webhook handler to Vercel/Netlify
- Use ngrok for local development
- Set up an AWS Lambda or Google Cloud Function

### Setup Steps:

1. **Create a Callback Handler**:

First, let's create a simple Node.js server to handle Lark callbacks:

```javascript
// lark-callback-server.js
const express = require('express');
const crypto = require('crypto');
const axios = require('axios');

const app = express();
app.use(express.json());

// Your Lark app credentials (from Lark Developer Console)
const APP_ID = process.env.LARK_APP_ID;
const APP_SECRET = process.env.LARK_APP_SECRET;
const VERIFICATION_TOKEN = process.env.LARK_VERIFICATION_TOKEN;
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_REPO = process.env.GITHUB_REPO; // owner/repo format

// Verify Lark signature
function verifySignature(timestamp, nonce, signature, body) {
  const content = timestamp + nonce + VERIFICATION_TOKEN + JSON.stringify(body);
  const hash = crypto.createHash('sha256').update(content).digest('hex');
  return hash === signature;
}

// Handle URL verification (Lark will call this to verify your endpoint)
app.post('/lark/callback', async (req, res) => {
  const { type, challenge, token } = req.body;
  
  // URL verification
  if (type === 'url_verification') {
    if (token !== VERIFICATION_TOKEN) {
      return res.status(403).json({ error: 'Invalid token' });
    }
    return res.json({ challenge });
  }
  
  // Event callback
  if (type === 'event_callback') {
    const { event } = req.body;
    
    // Handle different event types
    switch (event.type) {
      case 'message':
        await handleMessage(event);
        break;
      case 'card.action.trigger':
        await handleCardAction(event);
        break;
    }
    
    // Always respond immediately
    res.json({ success: true });
  }
});

// Handle card button clicks
async function handleCardAction(event) {
  const { action, open_id, user_id } = event;
  
  // Check what action was triggered
  if (action.value.action === 'trigger_workflow') {
    // Trigger a GitHub Actions workflow
    try {
      await axios.post(
        `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/${action.value.workflow_id}/dispatches`,
        {
          ref: 'main',
          inputs: {
            triggered_by: 'lark',
            user_id: user_id
          }
        },
        {
          headers: {
            'Authorization': `token ${GITHUB_TOKEN}`,
            'Accept': 'application/vnd.github.v3+json'
          }
        }
      );
      
      // Send success message back to Lark
      await sendLarkMessage(open_id, '✅ Workflow triggered successfully!');
    } catch (error) {
      await sendLarkMessage(open_id, '❌ Failed to trigger workflow: ' + error.message);
    }
  }
}

// Send message back to Lark
async function sendLarkMessage(open_id, text) {
  // Get access token
  const tokenResponse = await axios.post(
    'https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal',
    {
      app_id: APP_ID,
      app_secret: APP_SECRET
    }
  );
  
  const accessToken = tokenResponse.data.tenant_access_token;
  
  // Send message
  await axios.post(
    'https://open.larksuite.com/open-apis/im/v1/messages',
    {
      receive_id: open_id,
      msg_type: 'text',
      content: JSON.stringify({ text })
    },
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      },
      params: {
        receive_id_type: 'open_id'
      }
    }
  );
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Lark callback server running on port ${PORT}`);
});
```

2. **Deploy the Callback Server**:

For quick deployment to Vercel:

```json
// vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "lark-callback-server.js",
      "use": "@vercel/node"
    }
  ],
  "routes": [
    {
      "src": "/lark/callback",
      "dest": "/lark-callback-server.js"
    }
  ]
}
```

```json
// package.json
{
  "name": "lark-github-callback",
  "version": "1.0.0",
  "main": "lark-callback-server.js",
  "dependencies": {
    "express": "^4.18.0",
    "axios": "^1.4.0"
  }
}
```

3. **Configure Lark App**:

In Lark Developer Console (https://open.larksuite.com/app):

a. **Create New App**:
   - Click "Create App"
   - Choose "Custom App"
   - Fill in basic information

b. **Configure Callback URL**:
   - Go to "Event Subscriptions"
   - Enable events
   - Set Request URL: `https://your-domain.vercel.app/lark/callback`
   - Add events you want to subscribe to:
     - `im.message.receive_v1` - Receive messages
     - `card.action.trigger` - Handle button clicks

c. **Get Credentials**:
   - Go to "Credentials & Basic Info"
   - Copy App ID, App Secret, Verification Token
   - Add these as environment variables in your deployment

4. **Update GitHub Actions Workflow**:

```yaml
# .github/workflows/lark-interactive.yml
name: 'Lark Interactive Workflow'

on:
  workflow_dispatch:
    inputs:
      triggered_by:
        description: 'Who triggered this workflow'
        required: false
        default: 'manual'
      user_id:
        description: 'Lark user ID'
        required: false

jobs:
  interactive-job:
    runs-on: warp-custom-default
    
    steps:
      - name: 'Process Lark trigger'
        run: |
          echo "Workflow triggered by: ${{ github.event.inputs.triggered_by }}"
          echo "Lark user: ${{ github.event.inputs.user_id }}"
          
      - name: 'Send interactive card to Lark'
        env:
          LARK_APP_ID: ${{ secrets.LARK_APP_ID }}
          LARK_APP_SECRET: ${{ secrets.LARK_APP_SECRET }}
        run: |
          # Get access token
          TOKEN_RESPONSE=$(curl -X POST \
            "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal" \
            -H "Content-Type: application/json" \
            -d "{\"app_id\":\"${LARK_APP_ID}\",\"app_secret\":\"${LARK_APP_SECRET}\"}")
          
          ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.tenant_access_token')
          
          # Send interactive card
          curl -X POST \
            "https://open.larksuite.com/open-apis/im/v1/messages" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{
              "receive_id": "'${{ github.event.inputs.user_id }}'",
              "msg_type": "interactive",
              "card": {
                "header": {
                  "title": {"tag": "plain_text", "content": "Workflow Complete"}
                },
                "elements": [
                  {
                    "tag": "action",
                    "actions": [
                      {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "Deploy to Production"},
                        "type": "primary",
                        "value": {
                          "action": "trigger_workflow",
                          "workflow_id": "deploy.yml"
                        }
                      }
                    ]
                  }
                ]
              }
            }'
```

## Which Option Should You Choose?

### Use Simple Webhook Bot if:
- You just want to send notifications to Lark ✅
- You don't need button interactions
- You want quick setup without external servers
- **This is what most GitHub Actions users need!**

### Use Full Lark App if:
- You want buttons that trigger GitHub workflows
- You need two-way communication
- You want to build a chatbot
- You have infrastructure for callback URLs

## Quick Start for Simple Notifications

If you just want GitHub Actions to send notifications to Lark:

1. **Don't use the Developer Console** - use Lark app directly
2. In your Lark group chat: Settings → Bots → Add Bot → Custom Bot
3. Copy the webhook URL
4. Add to GitHub Secrets
5. Use the workflows I provided earlier!

The "Callback configuration" you're seeing is only needed for interactive apps, not for simple notifications.