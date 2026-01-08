# aliciadata-chat

Public-facing frontend for the AliciaData chat app. A Gradio-based chat application that enables users to chat with Claude Haiku about resume qualifications against job descriptions.

## Overview

This application provides a conversational interface powered by Claude Haiku that helps hiring managers and recruiters learn about candidate qualifications. The app retrieves resume and job description documents from a PostgreSQL database, uses Mustache templates for dynamic system prompt generation, and provides real-time streaming responses.

## Technology Stack

- **Python Package Manager**: uv
- **UI Framework**: Gradio
- **LLM**: Anthropic Claude API (claude-haiku-4-5)
- **Database**: PostgreSQL with connection pooling
- **Template Engine**: pystache (Mustache for Python)
- **Environment Management**: python-dotenv

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- PostgreSQL database (local or remote)
- Anthropic API key

### 1. Clone the Repository

```bash
git clone <repository-url>
cd aliciadata-chat
```

### 2. Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with homebrew
brew install uv
```

### 3. Install Dependencies

```bash
uv sync
```

This will:
- Create a virtual environment at `.venv/`
- Install all dependencies specified in `pyproject.toml`
- Set up the project in editable mode

### 4. Set Up PostgreSQL Database

#### Option A: Local PostgreSQL

1. Install PostgreSQL (if not already installed):
   ```bash
   # macOS
   brew install postgresql@15
   brew services start postgresql@15
   ```

2. Create the database:
   ```bash
   createdb aliciadata_chat
   ```

3. Run the migration to create tables:
   ```bash
   psql -d aliciadata_chat -f migrations/001_create_tables.sql
   ```

#### Option B: Remote PostgreSQL (DigitalOcean, etc.)

1. Obtain connection credentials from your provider
2. Run the migration:
   ```bash
   psql -h your-host -p your-port -U your-user -d your-database -f migrations/001_create_tables.sql
   ```

### 5. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```bash
   # Anthropic API
   ANTHROPIC_API_KEY=sk-ant-xxx...

   # PostgreSQL Database
   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   DATABASE_NAME=aliciadata_chat
   DATABASE_USER=postgres
   DATABASE_PASSWORD=your_password

   # Application
   APP_PORT=7860

   # Applicant email
   APPLICANT_EMAIL=your.email@example.com
   ```

### 6. Populate Documents Table

The `documents` table is managed by another application, but for development you can manually insert test data:

```sql
INSERT INTO documents (name, resume, jd) VALUES (
    'test-doc',
    'Your resume content here...',
    'Your job description content here...'
);
```

### 7. Customize System Prompt Template

Edit `prompts/chat_system.mustache` to customize the AI assistant's behavior. The template supports these variables:
- `{{ resume }}` - Resume content
- `{{ jd }}` - Job description content
- `{{ email }}` - Applicant email address

## Running the Application

### Development Mode

```bash
uv run python src/main.py
```

The application will:
1. Run startup checks (database, API key, template)
2. Start the Gradio server on port 7860 (or `APP_PORT` from `.env`)
3. Be accessible at `http://localhost:7860?q=<document_name>`

### Accessing the Application

The application requires a `q` URL parameter to specify which document to load:

```
http://localhost:7860?q=test-doc
```

Where `test-doc` is the `name` field from the `documents` table.

## Project Structure

```
aliciadata-chat/
├── .env                          # Environment variables (not in git)
├── .env.example                  # Template for environment variables
├── pyproject.toml                # uv project configuration
├── migrations/
│   └── 001_create_tables.sql     # Database schema
├── prompts/
│   └── chat_system.mustache      # System prompt template
├── src/
│   ├── __init__.py
│   ├── main.py                   # Gradio app entry point
│   ├── database.py               # Database operations
│   ├── chat_service.py           # Claude API interaction
│   └── prompt_loader.py          # Mustache template loader
└── README.md
```

## Database Schema

### Chats Table (Created by Migration)

Stores conversation history:

```sql
CREATE TABLE chats (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_uuid UUID NOT NULL,
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('system', 'user', 'assistant')),
    contents TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Documents Table (Managed Externally)

Expected schema:

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    resume TEXT,
    jd TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Development Workflow

### Making Code Changes

1. The virtual environment is automatically activated when using `uv run`
2. Edit code in the `src/` directory
3. Restart the application to see changes

### Adding Dependencies

```bash
# Add a new dependency
uv add package-name

# Add a development dependency
uv add --dev package-name
```

### Database Migrations

Currently migrations are managed manually. To modify the schema:

1. Create a new SQL file in `migrations/`
2. Run it manually with `psql`

### Updating System Prompt

Edit `prompts/chat_system.mustache` and restart the application. The template is loaded once at startup and cached.

## Troubleshooting

### "Unable to connect to database"

- Verify PostgreSQL is running: `pg_isready`
- Check credentials in `.env`
- Ensure database exists: `psql -l | grep aliciadata_chat`

### "Unable to connect to Claude API"

- Verify API key is valid in `.env`
- Check API key has sufficient credits
- Test with: `curl https://api.anthropic.com/v1/messages -H "x-api-key: $ANTHROPIC_API_KEY"`

### "Template file not found"

- Verify `prompts/chat_system.mustache` exists
- Check you're running from project root directory

### "No document found with name 'xxx'"

- Verify document exists in database: `SELECT name FROM documents;`
- Check the `q` parameter matches exactly (case-sensitive)

### "Data incompatible with messages format"

- This was fixed in the latest version
- Make sure you have the updated code that uses dictionary format for messages

## Testing

### Manual Testing Checklist

- [ ] App loads with valid `q` parameter
- [ ] App shows error with missing `q` parameter
- [ ] App shows error with invalid `q` parameter
- [ ] Resume and job description display correctly
- [ ] Chat messages stream in real-time
- [ ] Messages persist to database
- [ ] System prompt includes resume/JD context
- [ ] Email variable interpolates correctly

### Database Testing

```bash
# Check messages are being saved
psql -d aliciadata_chat -c "SELECT * FROM chats ORDER BY timestamp DESC LIMIT 5;"

# Check session history
psql -d aliciadata_chat -c "SELECT session_uuid, message_type, LEFT(contents, 50) FROM chats ORDER BY timestamp;"
```

## Deployment

See `CLAUDE.md` for detailed deployment instructions for:
- HuggingFace Spaces
- DigitalOcean Managed PostgreSQL
- Production environment configuration

## Contributing

1. Create a feature branch
2. Make changes
3. Test locally
4. Submit pull request

## License

See LICENSE file for details.

## Support

For issues or questions, please open an issue on GitHub.
