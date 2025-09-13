# Netra Frontend - Next.js Application

Modern, real-time chat interface for the Netra AI Optimization Platform built with Next.js 14, TypeScript, and TailwindCSS.

## 📊 Architecture Documentation

For comprehensive visual documentation of the frontend architecture, see:
- **[Frontend Architecture Diagrams](./docs/FRONTEND_ARCHITECTURE_DIAGRAMS.md)** - Complete Mermaid diagrams including:
  - Key components architecture and relationships
  - Loading flow state machine  
  - WebSocket event processing pipeline
  - Authentication and token refresh flows
  - Store relationships and state management
  - Fix documentation for the 100% loading issue

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

The application will be available at `http://localhost:3000`

## 📁 Project Structure

```
frontend/
├── app/                        # Next.js 14 App Router
│   ├── chat/                  # Main chat interface
│   │   └── page.tsx          # Chat page component
│   ├── auth/                  # Authentication pages
│   │   ├── callback/         # OAuth callback handler
│   │   ├── error/            # Auth error page
│   │   └── logout/           # Logout handler
│   ├── corpus/               # Corpus management
│   ├── synthetic-data-generation/  # Data generation UI
│   ├── demo/                 # Demo features
│   ├── enterprise-demo/     # Enterprise demo
│   ├── layout.tsx            # Root layout with providers
│   └── globals.css           # Global styles
├── components/                # React components
│   ├── chat/                 # Chat-specific components
│   │   ├── ChatHeader.tsx   # Chat header with controls
│   │   ├── MessageItem.tsx  # Individual message display
│   │   ├── MessageInput.tsx # Message input with controls
│   │   ├── MessageList.tsx  # Message list container
│   │   ├── ThreadSidebar.tsx # Thread management sidebar
│   │   ├── ThinkingIndicator.tsx # Agent thinking status
│   │   └── ExamplePrompts.tsx # Example prompt suggestions
│   ├── ui/                   # Reusable UI components (shadcn/ui)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── select.tsx
│   │   └── (other components)
│   ├── demo/                 # Demo-specific components
│   ├── ChatInterface.tsx     # Main chat interface wrapper
│   ├── SubAgentStatus.tsx    # Agent status indicators
│   └── ErrorFallback.tsx     # Error boundary fallback
├── providers/                 # Context providers
│   ├── WebSocketProvider.tsx # WebSocket connection management
│   └── AgentProvider.tsx     # Agent state provider
├── hooks/                     # Custom React hooks
│   ├── useWebSocket.ts       # WebSocket connection hook
│   ├── useAgent.ts           # Agent interaction hook
│   ├── useChatWebSocket.ts   # Chat-specific WebSocket
│   └── useWebSocketResilience.ts # Connection resilience
├── store/                     # Zustand state management
│   ├── chat.ts               # Chat state store
│   ├── authStore.ts          # Authentication state
│   ├── threadStore.ts        # Thread management
│   └── app.ts                # Application state
├── services/                  # API and WebSocket services
│   ├── api.ts                # API client
│   ├── apiClient.ts          # Axios configuration
│   ├── webSocketService.ts   # WebSocket service
│   ├── messageService.ts     # Message handling
│   └── threadService.ts      # Thread management
├── types/                     # TypeScript type definitions
│   ├── backend_schema_auto_generated.ts # Auto-generated types
│   ├── chat.ts               # Chat-related types
│   ├── Message.ts            # Message types
│   ├── Thread.ts             # Thread types
│   ├── User.ts               # User types
│   └── Netra.ts              # Core Netra types
├── auth/                      # Authentication utilities
│   ├── context.tsx           # Auth context provider
│   ├── service.ts            # Auth service
│   └── types.ts              # Auth types
├── __tests__/                # Test files
│   ├── components/           # Component tests
│   ├── hooks/                # Hook tests
│   ├── store/                # Store tests
│   └── critical/             # Critical path tests
└── cypress/                   # E2E tests
    ├── e2e/                  # Test specs
    └── support/              # Test utilities
```

## 🎨 Key Features

### Real-time Chat Interface
- **WebSocket Communication**: Live updates with automatic reconnection
- **Message Streaming**: Real-time message and status updates
- **Thinking Indicators**: Visual feedback for agent processing
- **Thread Management**: Multiple conversation threads with history

### Agent Integration
- **Sub-agent Status**: Real-time status for each agent in the pipeline
- **Tool Execution**: Visual feedback for tool calls and results
- **Error Handling**: Graceful error recovery and user feedback
- **State Persistence**: Conversation continuity across sessions

### Authentication
- **Google OAuth**: Seamless OAuth 2.0 integration
- **JWT Sessions**: Secure token-based authentication
- **Protected Routes**: Automatic redirection for unauthenticated users
- **Session Management**: Persistent login with refresh tokens

### UI/UX Features
- **Responsive Design**: Mobile-first responsive layout
- **Dark Mode**: Support for light/dark themes
- **Accessibility**: WCAG 2.1 AA compliance
- **Keyboard Navigation**: Full keyboard support
- **Loading States**: Skeleton loaders and progress indicators

## 🛠 Development

### Environment Variables

Create a `.env.local` file:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# OAuth Configuration
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id

# Feature Flags
NEXT_PUBLIC_ENABLE_DEBUG=true
NEXT_PUBLIC_ENABLE_DEMO=true
```

### Available Scripts

```bash
# Development
npm run dev          # Start development server
npm run dev:turbo    # Start with Turbopack

# Building
npm run build        # Build for production
npm run start        # Start production server

# Testing
npm test             # Run Jest tests
npm test:watch       # Run tests in watch mode
npm test:coverage    # Generate coverage report

# E2E Testing
npm run cypress:open # Open Cypress interactive
npm run cy:run      # Run Cypress headless

# Code Quality
npm run lint         # Run ESLint
npm run lint:fix     # Fix linting issues
npm run typecheck    # Run TypeScript checks
npm run format       # Format with Prettier
```

### Testing

#### Unit Tests (Jest)
```bash
# Run all tests
npm test

# Run auth-specific tests (including critical bug reproduction)
npm run test:unit -- TEST_SUITE=auth

# Run specific test file
npm test ChatInterface

# Run with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

#### Auth Testing Coverage

The auth validation system includes comprehensive test coverage (93.73%) that reproduces and prevents critical authentication bugs:

- **Critical Bug Reproduction**: Tests that reproduce the exact "token without user" bug
- **Edge Case Validation**: Comprehensive testing of token validation, expiration, and malformed inputs
- **Atomic Auth Updates**: Race condition prevention through atomic state updates
- **Recovery Functions**: Enhanced auth recovery with multiple fallback strategies
- **WebSocket Integration**: Auth validation for real-time chat functionality

Key test files:
- `__tests__/lib/auth-validation-helpers.test.ts` - Core validation logic (93.73% coverage)
- `__tests__/auth/test_auth_complete_flow.test.tsx` - Complete auth flow integration
- `__tests__/auth/test_simple_logout_fix.test.tsx` - Logout state management

#### E2E Tests (Cypress)
```bash
# Interactive mode
npm run cypress:open

# Headless mode
npm run cy:run

# Specific test
npm run cy:run -- --spec "cypress/e2e/chat.cy.ts"
```

### State Management

The application uses Zustand for state management:

```typescript
// Example: Using the chat store
import { useChatStore } from '@/store/chat';

function Component() {
  const { messages, addMessage, clearMessages } = useChatStore();
  
  // Use store actions and state
}
```

### WebSocket Integration

WebSocket connection is managed through a provider:

```typescript
// Using WebSocket in components
import { useWebSocket } from '@/hooks/useWebSocket';

function Component() {
  const { connected, sendMessage, subscribe } = useWebSocket();
  
  useEffect(() => {
    const unsubscribe = subscribe('agent_update', (data) => {
      // Handle agent updates
    });
    
    return unsubscribe;
  }, []);
}
```

### Component Development

Components follow a consistent structure:

```typescript
// components/example/ExampleComponent.tsx
import { FC } from 'react';
import { cn } from '@/lib/utils';

interface ExampleComponentProps {
  className?: string;
  // Other props
}

export const ExampleComponent: FC<ExampleComponentProps> = ({
  className,
  ...props
}) => {
  return (
    <div className={cn('default-classes', className)}>
      {/* Component content */}
    </div>
  );
};
```

## 🎯 Key Components

### ChatInterface
Main chat interface that orchestrates all chat-related components.

### MessageItem
Renders individual messages with markdown support, code highlighting, and agent metadata.

### WebSocketProvider
Manages WebSocket connections with automatic reconnection, heartbeat, and error handling.

### SubAgentStatus
Displays real-time status of sub-agents during execution.

### ThreadSidebar
Manages conversation threads with create, switch, and delete functionality.

## 🔧 Configuration

### TailwindCSS
Configuration in `tailwind.config.ts`:
- Custom color scheme
- Typography plugin
- Animation utilities
- Responsive breakpoints

### TypeScript
Strict mode enabled with:
- No implicit any
- Strict null checks
- No unused locals/parameters
- ES2022 target

### Next.js
Configuration in `next.config.ts`:
- Image optimization
- API routes proxy
- Environment variables
- Performance optimizations

## 📚 Dependencies

### Core
- **Next.js 14**: React framework with App Router
- **React 18**: UI library
- **TypeScript 5**: Type safety
- **TailwindCSS 3**: Utility-first CSS

### State & Data
- **Zustand**: State management
- **Axios**: HTTP client
- **React Query**: Server state management

### UI Components
- **shadcn/ui**: Component library
- **Radix UI**: Headless UI primitives
- **React Hook Form**: Form management
- **Zod**: Schema validation

### Development
- **Jest**: Unit testing
- **Cypress**: E2E testing
- **ESLint**: Code linting
- **Prettier**: Code formatting

## 🚀 Deployment

### Build for Production
```bash
npm run build
npm start
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment-specific Builds
```bash
# Development
npm run build:dev

# Staging
npm run build:staging

# Production
npm run build:prod
```

## 🤝 Contributing

1. Follow the existing code style
2. Write tests for new features
3. Update documentation
4. Run all checks before submitting PR:
   ```bash
   npm run lint
   npm run typecheck
   npm test
   npm run cy:run
   ```

## 📄 License

Proprietary - Netra Systems

---

For more information, see the [main README](../README.md) or contact the development team.