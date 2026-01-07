# Gradio Chat App with Claude Haiku Integration

## Overview
Build a Gradio-based chat application that enables users to chat with Claude Haiku (claude-haiku-4-5) model. The app includes PostgreSQL storage for chat history, document retrieval from database, dynamic system prompt injection via Mustache templates with resume/job description context, and a specialized UI for resume/job description review.

## Technology Stack
- **Python Package Manager**: uv
- **UI Framework**: Gradio
- **LLM**: Anthropic Claude API (claude-haiku-4-5) with streaming
- **Database**: PostgreSQL with connection pooling
- **Template Engine**: pystache (Mustache for Python)
- **Environment Management**: python-dotenv
- **Development**: macOS local environment
- **Production**: HuggingFace Spaces + DigitalOcean Managed PostgreSQL

## Project Structure
```
project_root/
├── .env                          # Environment variables (not in git)
├── .env.example                  # Template for environment variables
├── pyproject.toml                # uv project configuration
├── migrations/
│   └── 001_create_tables.sql     # Creates chats and documents tables
├── prompts/
│   └── chat_system.mustache      # System prompt template
├── src/
│   ├── __init__.py
│   ├── main.py                   # Gradio app entry point
│   ├── database.py               # Database connection and operations
│   ├── chat_service.py           # Claude API interaction with streaming
│   └── prompt_loader.py          # Mustache template loader
└── README.md
```

## Environment Variables

### .env.example
```env
# Anthropic API
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# PostgreSQL Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=chat_app
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password_here

# Application
APP_PORT=7860
```

## Database Schema

### Migration: 001_create_tables.sql
```sql
-- Chats table for storing conversation history
CREATE TABLE IF NOT EXISTS chats (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_uuid UUID NOT NULL,
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('system', 'user', 'assistant')),
    contents TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_chats_session_uuid ON chats(session_uuid);
CREATE INDEX IF NOT EXISTS idx_chats_timestamp ON chats(timestamp);
```

**Note**: This migration will be executed once manually before application deployment.

### Documents Table (Managed Externally)

The `documents` table is created and managed by another application. This application expects the following schema:

```sql
-- Documents table (managed by another application - DO NOT CREATE)
-- Expected schema:
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    resume TEXT,
    jd TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_name ON documents(name);
```

## Core Components

### 1. Database Module (src/database.py)

#### Connection Management
- Use psycopg2 with connection pooling (SimpleConnectionPool or ThreadedConnectionPool)
- Pool size: minimum 1, maximum 3 connections (sufficient for 2 concurrent users)
- Connection parameters from environment variables

#### Functions
- `get_connection_pool()`: Initialize and return connection pool singleton
- `save_message(session_uuid, message_type, contents, timestamp)`: Save chat message to database
- `get_session_history(session_uuid)`: Retrieve chat history for current session (not used for historical sessions)
- `get_document_by_name(name)`: Retrieve resume and jd from documents table where name matches
- `test_connection()`: Verify database connectivity on startup
- `close_pool()`: Clean shutdown of connection pool

#### Error Handling
- Return None or raise specific exceptions for connection failures
- Log errors for debugging
- Enable graceful degradation in UI

### 2. Chat Service (src/chat_service.py)

#### Anthropic Client Setup
- Initialize client with API key from environment
- Use claude-haiku-4-5 model identifier: `claude-haiku-4-5-20251001`

#### Functions
- `stream_message(messages, system_prompt)`: Send messages to Claude API with streaming enabled
  - Returns generator/iterator for streaming response chunks
  - Handle streaming API responses properly
- `format_message_history(db_messages)`: Convert database format to Anthropic API message format
- `validate_api_key()`: Test API connectivity on startup

#### Streaming Implementation
- Use `anthropic.messages.create()` with `stream=True`
- Yield text chunks as they arrive
- Handle stream errors gracefully
- Return complete message for database storage after streaming completes

### 3. Prompt Loader (src/prompt_loader.py)

#### Template Management
- Load Mustache template from `prompts/chat_system.mustache`
- Template will have placeholders for `{{resume}}` and `{{jd}}`

#### Functions
- `load_template(template_path)`: Load and cache template file
- `render_prompt(template, resume, jd)`: Render template with resume and job description context
  - Context dict: `{"resume": resume, "jd": jd}`
- `validate_template_exists()`: Check template file exists on startup

### 4. Main Gradio App (src/main.py)

#### Startup Sequence
1. Load environment variables from .env
2. Verify all required environment variables present
3. Test database connection and initialize connection pool
4. Validate Anthropic API key
5. Verify system prompt template file exists
6. If any startup check fails: display error and exit gracefully

#### URL Parameter Handling
- Extract `q` parameter from URL query string on page load
- Use Gradio's `gr.Request` in interface function to access query parameters
- Store `q` value in Gradio State component

#### Document Retrieval Flow
1. On page load, extract `q` parameter
2. Query documents table: `SELECT resume, jd FROM documents WHERE name = q`
3. If document found: populate resume and jd textareas, enable chat
4. If document not found: show error, disable UI

#### UI Layout
```
Row 1: Error message area (gr.Markdown, visible only when errors occur)
Row 2: Chat interface (gr.Chatbot, 100% width)
Row 3: Message input (gr.Textbox) + Send button
Row 4: Two columns
  - Column 1: Resume textarea (50% width, gr.Textbox, interactive=False, lines=20)
  - Column 2: Job description textarea (50% width, gr.Textbox, interactive=False, lines=20)
```

#### State Management
- Generate new `session_uuid` (UUID4) on page load (once per session)
- Store in Gradio State component
- Store `q` parameter value in State
- Store resume and jd content in State
- No session history or continuation features

#### Chat Flow with Streaming
1. User sends message via input textbox
2. Validate all prerequisites (database, API, template, document)
3. Save user message to database with current timestamp
4. Retrieve session history from database (for context)
5. Load and render system prompt with resume and jd context
6. Call Claude API with streaming enabled
7. Stream response chunks to chat interface in real-time
8. After streaming completes, save full assistant response to database
9. Clear input textbox, ready for next message

#### Conditional UI Behavior

**If `q` parameter is missing:**
- Display error: "Error: 'q' parameter must be specified in the URL"
- Disable chat interface (interactive=False)
- Disable/hide resume and job description textareas
- Prevent message sending

**If `q` parameter present but document not found:**
- Display error: "Error: No document found with name '{q}'"
- Disable chat interface
- Disable/hide resume and job description textareas

**If database connection fails:**
- Display error: "Error: Unable to connect to database. Please check configuration."
- Disable entire UI

**If Claude API is unreachable:**
- Display error: "Error: Unable to connect to Claude API. Please check API key."
- Disable chat interface

**If system prompt template missing:**
- Display error: "Error: System prompt template not found at prompts/chat_system.mustache"
- Disable chat interface

**If all checks pass:**
- Enable chat interface
- Populate and display resume and job description textareas
- Hide error message area
- Ready to chat

#### Gradio Interface Configuration
```python
demo = gr.Interface(
    fn=chat_function,
    inputs=[...],
    outputs=[...],
    ...
)

# Or use gr.Blocks for more control
with gr.Blocks() as demo:
    # Define layout
    ...

demo.launch(server_port=APP_PORT)
```

## Dependencies (pyproject.toml)
```toml
[project]
name = "gradio-claude-chat"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "gradio>=4.0.0",
    "anthropic>=0.40.0",
    "psycopg2-binary>=2.9.0",
    "python-dotenv>=1.0.0",
    "pystache>=0.6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Error Handling Strategy

### Startup Errors (Fatal - Prevent App Launch)
- Missing environment variables
- Database connection failure
- Invalid Anthropic API key
- Missing system prompt template file

### Runtime Errors (Display in UI, Disable Chat)
- Document not found for given `q` parameter
- Database query failures during chat
- API errors during message streaming
- Template rendering errors

### Error Display
- Use gr.Markdown component for error messages
- Red/warning styling for visibility
- Clear, actionable error messages
- Disable interactive components when errors present

## Deployment Considerations

### Local Development (macOS)
- Run PostgreSQL locally or connect to remote instance
- Use .env file for local configuration
- Test with `uv run gradio src/main.py` or similar

### HuggingFace Spaces Production
- Set environment variables in Spaces secrets
- Ensure all dependencies in pyproject.toml
- Include README.md with setup instructions
- Configure `app.py` as entry point if required by HuggingFace
- Test streaming performance on Spaces infrastructure

### DigitalOcean Managed PostgreSQL
- Use connection string from DigitalOcean console
- Enable SSL/TLS for database connections
- Configure connection pool for managed instance limits
- Set appropriate timeout values
- Ensure firewall rules allow HuggingFace Spaces IPs

### Connection String Format
```env
DATABASE_HOST=your-cluster.db.ondigitalocean.com
DATABASE_PORT=25060
DATABASE_NAME=defaultdb
DATABASE_USER=doadmin
DATABASE_PASSWORD=your_secure_password
DATABASE_SSLMODE=require  # Add this for managed PostgreSQL
```

## Security Considerations
- Never commit .env file (add to .gitignore)
- Use HuggingFace Spaces secrets for production credentials
- Validate and sanitize `q` parameter to prevent SQL injection
- Use parameterized SQL queries exclusively
- Limit database user permissions to required tables only
- Consider rate limiting if application becomes public

## Testing Checklist
- [ ] App loads with valid `q` parameter
- [ ] App shows error with missing `q` parameter
- [ ] App shows error with invalid `q` parameter (document not found)
- [ ] Resume and job description populate correctly
- [ ] Chat messages stream in real-time
- [ ] Messages persist to database correctly
- [ ] System prompt renders with resume/jd context
- [ ] Database connection pool handles concurrent requests
- [ ] Error handling works for all failure modes
- [ ] App deploys successfully to HuggingFace Spaces
- [ ] Connection to DigitalOcean PostgreSQL works in production

## System Prompt Template Example

### prompts/chat_system.mustache
```
You are a helpful career advisor assistant reviewing a resume against a job description.

RESUME:
{{resume}}

JOB DESCRIPTION:
{{jd}}

Please provide thoughtful, specific feedback to help the candidate improve their resume for this position.
```

**Note**: User will create actual template content. This is just an example structure.

## No Session Management Features
- Users cannot view previous chat sessions
- Users cannot continue interrupted sessions (refresh creates new session)
- Users cannot clear/reset current session
- Each page load creates a new session_uuid
- Session history is stored but not exposed in UI

## Streaming Response Implementation Notes
- Use `with anthropic.messages.stream()` context manager
- Or iterate over response chunks from `stream=True`
- Update Gradio chat interface incrementally
- Accumulate full response for database storage
- Handle stream interruptions gracefully
- Display "Streaming..." indicator during response generation

## Expected Concurrency
- Maximum 2 concurrent users
- Connection pool sized accordingly (max 3 connections)
- No advanced queuing or load balancing required
- Simple connection management sufficient

## Future Considerations (Out of Scope)
- User authentication
- Session history viewing
- Multi-document support
- Resume/JD upload functionality
- Analytics and usage tracking
- Cost monitoring for API usage
