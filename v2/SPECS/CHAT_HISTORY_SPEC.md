# Chat History Specification

## Overview
The Chat History feature enables users to manage multiple conversation threads, view previous conversations, and switch between different chat sessions seamlessly.

## Architecture

### Backend Components

#### 1. Thread Management API (`/api/threads`)
- **GET /api/threads** - List all threads for authenticated user
  - Query params: `limit`, `offset`
  - Returns: Array of thread objects with metadata and message counts
  
- **POST /api/threads** - Create new thread
  - Body: `{ title?: string, metadata?: object }`
  - Returns: Created thread object
  
- **GET /api/threads/{thread_id}** - Get specific thread details
  - Returns: Thread object with full metadata
  
- **PUT /api/threads/{thread_id}** - Update thread (title, metadata)
  - Body: `{ title?: string, metadata?: object }`
  - Returns: Updated thread object
  
- **DELETE /api/threads/{thread_id}** - Archive thread (soft delete)
  - Returns: Success message
  
- **GET /api/threads/{thread_id}/messages** - Get messages for thread
  - Query params: `limit`, `offset`
  - Returns: Paginated message list

#### 2. Database Schema

**Thread Table (PostgreSQL)**
```sql
- id: string (primary key, format: thread_xxxx)
- object: string (always "thread")
- created_at: integer (unix timestamp)
- metadata_: jsonb (contains user_id, title, status, etc.)
```

**Message Table (PostgreSQL)**
```sql
- id: string (primary key, format: msg_xxxx)
- thread_id: string (foreign key to Thread)
- role: string (user/assistant/system)
- content: jsonb (array of content objects)
- created_at: integer (unix timestamp)
- metadata_: jsonb (additional data)
```

#### 3. Repository Pattern
- `ThreadRepository`: Handles thread CRUD operations
  - `find_by_user()`: Get all threads for a user
  - `get_or_create_for_user()`: Get or create default thread
  - `get_active_thread()`: Get most recent active thread
  - `archive_thread()`: Soft delete thread
  
- `MessageRepository`: Handles message operations
  - `find_by_thread()`: Get messages for thread with pagination
  - `count_by_thread()`: Get message count for thread
  - `create_message()`: Create new message in thread

### Frontend Components

#### 1. Thread Sidebar (`ThreadSidebar.tsx`)
- **Features:**
  - Display list of conversation threads
  - Create new thread button
  - Select/switch between threads
  - Edit thread titles inline
  - Delete/archive threads
  - Show thread metadata (date, message count)
  
- **State Management:**
  - Uses `threadStore` for thread state
  - Uses `chatStore` for message state
  - Syncs with backend via `ThreadService`

#### 2. Thread Store (`threadStore.ts`)
- **State:**
  - `threads`: Array of thread objects
  - `currentThreadId`: Currently selected thread
  - `currentThread`: Current thread object
  - `loading`: Loading state
  - `error`: Error state
  
- **Actions:**
  - `setThreads()`: Set thread list
  - `addThread()`: Add new thread
  - `updateThread()`: Update thread metadata
  - `deleteThread()`: Remove thread from list
  - `setCurrentThread()`: Switch active thread

#### 3. Thread Service (`threadService.ts`)
- **API Methods:**
  - `listThreads()`: Fetch all threads
  - `getThread()`: Get single thread
  - `createThread()`: Create new thread
  - `updateThread()`: Update thread metadata
  - `deleteThread()`: Archive thread
  - `getThreadMessages()`: Fetch thread messages

#### 4. Chat Store Updates
- **New Methods:**
  - `loadMessages()`: Load historical messages into chat
  - `setActiveThread()`: Set current thread context
  - `clearMessages()`: Clear chat when switching threads

### WebSocket Integration

#### Message Handling
- Messages include `thread_id` in payload
- Backend associates messages with correct thread
- Frontend updates active thread's message list

#### Real-time Updates
- Thread creation triggers sidebar update
- Message count updates in real-time
- Thread title updates on first message

## User Flow

### 1. New User Experience
1. User opens chat interface
2. No threads exist - empty state shown
3. User sends first message
4. System creates new thread automatically
5. Thread appears in sidebar with auto-generated title

### 2. Returning User Experience
1. User opens chat interface
2. Thread sidebar loads previous conversations
3. Most recent thread is selected by default
4. User can view message history
5. User can continue conversation or start new thread

### 3. Thread Management
1. **Create Thread**: Click "New Conversation" button
2. **Switch Thread**: Click thread in sidebar
3. **Edit Title**: Click edit icon, modify title inline
4. **Delete Thread**: Click delete icon, confirm deletion
5. **View History**: Select thread to load all messages

## Security Considerations

### Authentication
- All thread operations require authentication
- Threads are user-scoped (only owner can access)
- JWT token validation on all API endpoints

### Data Privacy
- Thread isolation per user
- No cross-user data access
- Soft delete preserves data integrity

## Performance Optimizations

### Pagination
- Thread list pagination (default: 20 items)
- Message pagination (default: 50 messages)
- Lazy loading for improved performance

### Caching
- Frontend caches thread list
- Messages cached in store
- Optimistic UI updates

## Future Enhancements

### Phase 2
- Thread search functionality
- Thread tagging/categorization
- Export conversation history
- Thread sharing (with permissions)

### Phase 3
- Thread templates
- Conversation branching
- Multi-user threads (collaboration)
- Thread analytics and insights

## Testing Requirements

### Unit Tests
- Repository methods
- API endpoints
- Store actions
- Service methods

### Integration Tests
- Thread CRUD operations
- Message association
- WebSocket message flow
- Authentication flow

### E2E Tests
- Create and switch threads
- Load message history
- Edit thread metadata
- Delete thread confirmation

## Deployment Considerations

### Database Migrations
- Add thread_id to existing messages
- Create thread records for orphan messages
- Index thread_id for performance

### Backward Compatibility
- Support legacy message format
- Migrate existing conversations
- Maintain API versioning