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
